"""
Domain: DMA Materiality
Layer: service/workflow
Responsibility:
- Build company context profile from G0 facts
- Calculate deterministic context modifiers
- Apply context modifiers to final DMA score only
- Preserve stage score immutability
Public functions:
- applyModifiers
- applyCompanyContextModifiers
- getProfile
- getCompanyContextProfile
- buildProfile
- buildCompanyContextProfile
- calcModifier
- calculateContextModifier
- applyRankGuards
- applyRankMovementGuards
- checkObservedStage
- hasObservedStage
Do not:
- do not mutate unrelated DB state
- do not change scoring formula unless explicitly requested
- do not change benchmark/media/survey stage scores
- do not change API routes
- do not call FastAPI router directly
- do not bypass context modifier guard flow
- do not modify auth/token/common code
"""

from __future__ import annotations

import json
from typing import Optional

from src.models.materialitycontext import (
    CompanyContextFactDto,
    CompanyContextModifierResponseDto,
    CompanyContextProfileResponseDto,
    CompanyContextProfileDto,
    ContextRuleHitDto,
    SubIssueContextModifierDto,
)
from src.services.materialities.contextgraph import buildCompanyContextProfileWithOptionalGraph
from src.utils.companycontextrepository import (
    getLatestProfile,
    getRun,
    listG0Facts,
    listScoreRows,
    replaceProfile,
    updateModifiers,
)
from src.utils.dmaaggregator import calcFinal
from src.utils.dmarepository import recalcFinal
from src.utils.dmarepository import updateRanks
from src.utils.dmascoring import clamp
from src.utils.subissuemaster import subissueMaster


MVP_MODIFIER_MIN = -0.3
MVP_MODIFIER_MAX = 0.3
SYSTEM_MODIFIER_MIN = -0.5
SYSTEM_MODIFIER_MAX = 0.5
MIN_PROFILE_CONFIDENCE_FOR_MODIFIER = 0.5
MAX_RANK_MOVEMENT = 2
TOP5_ENTRY_RAW_RANK_LIMIT = 8
MODIFIER_RULE_VERSION = "company-context-modifier-v1"


def applyModifiers(runId: int) -> CompanyContextModifierResponseDto:
    runContext = getRun(runId)
    if not runContext:
        return CompanyContextModifierResponseDto(
            runId=runId,
            implementationStatus="NO_RUN",
            messages=["No ESG_MATERIALITY_RUN row found for runId."],
        )

    companyId = int(runContext["company_id"])
    reportingYear = int(runContext["reporting_year"])
    facts = _toFactDtos(listG0Facts(companyId, reportingYear))
    profile, graphTrace = buildCompanyContextProfileWithOptionalGraph(
        runId=runId,
        runContext=runContext,
        facts=facts,
        deterministicBuilder=buildProfile,
    )
    profileConfidence = _profileConfidence(profile)
    summaryRows = listScoreRows(runId)

    modifiers = [
        calcModifier(profile, row, profileConfidence)
        for row in summaryRows
        if row.get("sub_issue_code") in subissueMaster
    ]
    modifiers = applyRankGuards(modifiers)
    modifierPayload = _buildModifierPayload(modifiers)
    contextPayload = {
        "profile": profile.model_dump(),
        "profileSource": profile.profileSource,
        "ruleVersion": MODIFIER_RULE_VERSION,
        "profileConfidence": profileConfidence,
        "graphTrace": graphTrace,
    }
    contextProfileId = replaceProfile(
        runId=runId,
        companyId=companyId,
        reportingYear=reportingYear,
        industryProfile=profile.industryProfile,
        businessModel=profile.businessModel,
        contextPayload=contextPayload,
        modifierPayload=modifierPayload,
        confidenceScore=profileConfidence,
    )

    updatedCount = updateModifiers(
        runId,
        [
            {
                "subIssueCode": item.subIssueCode,
                "impactModifier": item.impactModifier,
                "financialModifier": item.financialModifier,
            }
            for item in modifiers
        ],
    )

    recalculatedCount = 0
    for item in modifiers:
        recalcFinal(runId, item.subIssueCode, updateRankingsYn=False)
        recalculatedCount += 1
    updateRanks(runId)

    messages = [
        "Context modifiers were applied only to final aggregation.",
        "Benchmark/media/survey stage scores were not changed.",
    ]
    if profileConfidence < MIN_PROFILE_CONFIDENCE_FOR_MODIFIER:
        messages.append("LOW_CONTEXT_CONFIDENCE: all context modifiers were forced to 0.0000.")
    if any(item.guardAppliedYn for item in modifiers):
        messages.append("One or more context modifier guards were applied.")

    return CompanyContextModifierResponseDto(
        runId=runId,
        contextProfileId=contextProfileId,
        companyId=companyId,
        reportingYear=reportingYear,
        implementationStatus="APPLIED",
        profile=profile,
        modifiers=modifiers,
        updatedModifierCount=updatedCount,
        recalculatedFinalCount=recalculatedCount,
        modifierRange={"min": MVP_MODIFIER_MIN, "max": MVP_MODIFIER_MAX},
        systemModifierRange={"min": SYSTEM_MODIFIER_MIN, "max": SYSTEM_MODIFIER_MAX},
        stageScoreChangedYn=False,
        messages=messages,
        rawPayload={
            "ruleVersion": MODIFIER_RULE_VERSION,
            "modifierJson": modifierPayload,
        },
    )


def getProfile(runId: int) -> CompanyContextProfileResponseDto:
    row = getLatestProfile(runId)
    if not row:
        return CompanyContextProfileResponseDto(
            runId=runId,
            implementationStatus="NO_CONTEXT_PROFILE",
            messages=["No ESG_DMA_CONTEXT_PROFILE row found for runId."],
        )

    contextPayload = _parseJsonDict(row.get("context_json"))
    modifierPayload = _parseJsonDict(row.get("modifier_json"))
    profilePayload = contextPayload.get("profile") or None
    profile = None
    if profilePayload:
        try:
            profile = CompanyContextProfileDto(**profilePayload)
        except Exception:
            profile = None

    modifiers = []
    for item in modifierPayload.get("modifiers", []) or []:
        try:
            modifiers.append(SubIssueContextModifierDto(**item))
        except Exception:
            continue

    profileSource = contextPayload.get("profileSource")
    profileConfidence = _floatOrNone(contextPayload.get("profileConfidence"))

    return CompanyContextProfileResponseDto(
        runId=runId,
        contextProfileId=int(row["id"]) if row.get("id") is not None else None,
        companyId=int(row["company_id"]) if row.get("company_id") is not None else None,
        reportingYear=int(row["reporting_year"]) if row.get("reporting_year") is not None else None,
        profile=profile,
        profileSource=profileSource,
        profileConfidence=profileConfidence,
        modifierRange=modifierPayload.get("modifierRange") or {"min": MVP_MODIFIER_MIN, "max": MVP_MODIFIER_MAX},
        systemModifierRange=modifierPayload.get("systemModifierRange") or {"min": SYSTEM_MODIFIER_MIN, "max": SYSTEM_MODIFIER_MAX},
        graphTrace=contextPayload.get("graphTrace") or [],
        modifiers=modifiers,
        messages=["OK"],
        implementationStatus="READY",
    )


def buildProfile(
    runId: int,
    runContext: dict,
    facts: list[CompanyContextFactDto],
) -> CompanyContextProfileDto:
    combinedText = _combinedText(runContext, facts)
    evidenceMetricIds = _unique([fact.metricId for fact in facts if fact.metricId])
    evidenceAtomicMetricIds = _unique([fact.atomicMetricId for fact in facts if fact.atomicMetricId])
    businessModel = _firstTextByMetric(facts, "G0-01")

    industryExposure = "automotive_parts_high" if _hasAny(
        combinedText,
        ["automotive", "mobility", "vehicle", "car", "parts", "자동차", "모빌리티", "부품", "전장"],
    ) else "unknown"

    valueChainExposure = _levelByKeywords(
        combinedText,
        high=["supply chain", "value chain", "supplier", "협력사", "공급망", "가치사슬", "원재료"],
        medium=["구매", "조달", "upstream", "downstream"],
    )
    globalCustomerExposure = _levelByKeywords(
        combinedText,
        high=["global", "overseas", "export", "eu", "europe", "usa", "글로벌", "해외", "수출", "유럽", "미국"],
        medium=["customer", "client", "고객", "완성차"],
    )
    euRegulationExposure = _levelByKeywords(
        combinedText,
        high=["csrd", "esrs", "cbam", "eu taxonomy", "유럽", "eu"],
        medium=["regulation", "compliance", "규제", "공시"],
    )
    transitionExposure = _levelByKeywords(
        combinedText,
        high=["transition", "carbon", "emission", "ev", "electric vehicle", "전환", "탄소", "배출", "전기차"],
        medium=["climate", "renewable", "energy", "기후", "재생에너지", "에너지"],
    )
    supplyChainDependency = _levelByKeywords(
        combinedText,
        high=["supplier", "supply chain", "협력사", "공급망", "원재료"],
        medium=["procurement", "purchase", "구매", "조달"],
    )
    productSafetyExposure = _levelByKeywords(
        combinedText,
        high=["product safety", "recall", "defect", "제품안전", "리콜", "결함"],
        medium=["quality", "certification", "품질", "인증", "안전"],
    )
    businessScaleExposure = _businessScaleExposure(facts)

    profileSummary = (
        "MVP context profile derived from G0/company facts. "
        "The profile describes exposure flags only; modifiers are calculated by rule engine."
    )

    return CompanyContextProfileDto(
        runId=runId,
        companyId=int(runContext["company_id"]),
        reportingYear=int(runContext["reporting_year"]),
        industryProfile=runContext.get("industry_profile"),
        businessModel=businessModel,
        industryExposure=industryExposure,
        valueChainExposure=valueChainExposure,
        globalCustomerExposure=globalCustomerExposure,
        euRegulationExposure=euRegulationExposure,
        transitionExposure=transitionExposure,
        supplyChainDependency=supplyChainDependency,
        productSafetyExposure=productSafetyExposure,
        businessScaleExposure=businessScaleExposure,
        evidenceMetricIds=evidenceMetricIds,
        evidenceAtomicMetricIds=evidenceAtomicMetricIds,
        profileSummary=profileSummary,
        profileSource="DETERMINISTIC_FALLBACK",
        confidence=_profileConfidenceFromValues([
            industryExposure,
            valueChainExposure,
            globalCustomerExposure,
            euRegulationExposure,
            transitionExposure,
            supplyChainDependency,
            productSafetyExposure,
            businessScaleExposure,
        ]),
        evidenceText=[fact.valueText[:300] for fact in facts if fact.valueText][:5],
        facts=facts,
    )


def calcModifier(
    profile: CompanyContextProfileDto,
    row: dict,
    profileConfidence: Optional[float] = None,
) -> SubIssueContextModifierDto:
    subIssueCode = row.get("sub_issue_code")
    rules: list[ContextRuleHitDto] = []
    confidence = _profileConfidence(profile) if profileConfidence is None else profileConfidence

    if subIssueCode == "E_CLIMATE__CLIMATE_TARGETS_TRANSITION" and profile.transitionExposure == "high":
        rules.append(_rule("CTX_AUTO_TRANSITION_FIN_001", subIssueCode, 0.0, 0.3, "High transition exposure increases financial relevance of transition planning."))

    if subIssueCode == "E_ENERGY__ENERGY_USE_MIX" and profile.transitionExposure == "high":
        rules.append(_rule("CTX_AUTO_ENERGY_MIX_001", subIssueCode, 0.1, 0.2, "High transition exposure increases relevance of energy mix and energy transition."))

    if subIssueCode == "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP" and profile.supplyChainDependency == "high":
        rules.append(_rule("CTX_AUTO_SUPPLY_CHAIN_001", subIssueCode, 0.2, 0.2, "High supply chain dependency increases supplier audit and CAP relevance."))

    if subIssueCode == "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE" and profile.industryExposure == "automotive_parts_high":
        rules.append(_rule("CTX_AUTO_LOW_CARBON_PRODUCT_001", subIssueCode, 0.0, 0.3, "Automotive parts exposure increases financial relevance of low-carbon product portfolio."))

    if subIssueCode == "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY" and profile.productSafetyExposure in ["medium", "high"]:
        impact = 0.2 if profile.productSafetyExposure == "high" else 0.1
        financial = 0.2 if profile.productSafetyExposure == "high" else 0.1
        rules.append(_rule("CTX_AUTO_PRODUCT_SAFETY_001", subIssueCode, impact, financial, "Product safety exposure increases product safety materiality."))

    if subIssueCode == "G_GOVERNANCE__BUSINESS_MODEL_VALUE_CHAIN" and profile.valueChainExposure == "high":
        rules.append(_rule("CTX_AUTO_VALUE_CHAIN_GOV_001", subIssueCode, 0.1, 0.1, "High value chain exposure increases business model and value chain governance relevance."))

    impactModifier = clamp(sum(item.impactModifier for item in rules), MVP_MODIFIER_MIN, MVP_MODIFIER_MAX)
    financialModifier = clamp(sum(item.financialModifier for item in rules), MVP_MODIFIER_MIN, MVP_MODIFIER_MAX)
    guardReason = None

    if not checkObservedStage(row):
        impactModifier = 0.0
        financialModifier = 0.0
        guardReason = "NO_STAGE_OBSERVATION"
    elif confidence < MIN_PROFILE_CONFIDENCE_FOR_MODIFIER:
        impactModifier = 0.0
        financialModifier = 0.0
        guardReason = "LOW_CONTEXT_CONFIDENCE"

    return _withScorePreview(
        profile,
        row,
        impactModifier,
        financialModifier,
        rules if guardReason is None else [],
        profileConfidence=confidence,
        guardAppliedYn=guardReason is not None,
        guardReason=guardReason,
    )


def checkObservedStage(row: dict) -> bool:
    return any([
        row.get("benchmark_impact_score") is not None,
        row.get("benchmark_financial_score") is not None,
        row.get("media_external_impact_score") is not None,
        row.get("media_external_financial_score") is not None,
        row.get("survey_impact_score") is not None,
        row.get("survey_financial_score") is not None,
    ])


def applyRankGuards(
    modifiers: list[SubIssueContextModifierDto],
) -> list[SubIssueContextModifierDto]:
    _assignRawRanks(modifiers)
    _assignAdjustedRanks(modifiers)

    changed = True
    while changed:
        changed = False
        for item in modifiers:
            if item.guardAppliedYn and item.guardReason in ["NO_STAGE_OBSERVATION", "LOW_CONTEXT_CONFIDENCE"]:
                continue
            violation = _rankGuardViolation(item)
            if violation and _hasNonZeroModifier(item):
                _zeroModifier(item, violation)
                changed = True
        if changed:
            _assignAdjustedRanks(modifiers)

    # Final global pass: if any remaining rank movement still exceeds the MVP
    # limit, remove all still-active modifiers. This keeps selection stable.
    if any(
        item.rankDelta is not None and abs(item.rankDelta) > MAX_RANK_MOVEMENT
        for item in modifiers
    ):
        for item in modifiers:
            if _hasNonZeroModifier(item):
                _zeroModifier(item, "RANK_MOVEMENT_LIMIT_GLOBAL")
        _assignAdjustedRanks(modifiers)

    return modifiers


# Compatibility wrappers for previous public names

def applyCompanyContextModifiers(runId: int) -> CompanyContextModifierResponseDto:
    return applyModifiers(runId)


def getCompanyContextProfile(runId: int) -> CompanyContextProfileResponseDto:
    return getProfile(runId)


def buildCompanyContextProfile(
    runId: int,
    runContext: dict,
    facts: list[CompanyContextFactDto],
) -> CompanyContextProfileDto:
    return buildProfile(runId, runContext, facts)


def calculateContextModifier(
    profile: CompanyContextProfileDto,
    row: dict,
    profileConfidence: Optional[float] = None,
) -> SubIssueContextModifierDto:
    return calcModifier(profile, row, profileConfidence)


def applyRankMovementGuards(
    modifiers: list[SubIssueContextModifierDto],
) -> list[SubIssueContextModifierDto]:
    return applyRankGuards(modifiers)


def hasObservedStage(row: dict) -> bool:
    return checkObservedStage(row)


def _withScorePreview(
    profile: CompanyContextProfileDto,
    row: dict,
    impactModifier: float,
    financialModifier: float,
    rules: list[ContextRuleHitDto],
    profileConfidence: Optional[float] = None,
    guardAppliedYn: bool = False,
    guardReason: Optional[str] = None,
) -> SubIssueContextModifierDto:
    subIssueCode = row.get("sub_issue_code")
    impactModifier = clamp(impactModifier, MVP_MODIFIER_MIN, MVP_MODIFIER_MAX)
    financialModifier = clamp(financialModifier, MVP_MODIFIER_MIN, MVP_MODIFIER_MAX)
    raw = calcFinal(
        subIssueCode=subIssueCode,
        surveyImpact=_floatOrNone(row.get("survey_impact_score")),
        surveyFinancial=_floatOrNone(row.get("survey_financial_score")),
        benchmarkImpact=_floatOrNone(row.get("benchmark_impact_score")),
        benchmarkFinancial=_floatOrNone(row.get("benchmark_financial_score")),
        mediaImpact=_floatOrNone(row.get("media_external_impact_score")),
        mediaFinancial=_floatOrNone(row.get("media_external_financial_score")),
        contextImpactModifier=0.0,
        contextFinancialModifier=0.0,
    )
    final = calcFinal(
        subIssueCode=subIssueCode,
        surveyImpact=_floatOrNone(row.get("survey_impact_score")),
        surveyFinancial=_floatOrNone(row.get("survey_financial_score")),
        benchmarkImpact=_floatOrNone(row.get("benchmark_impact_score")),
        benchmarkFinancial=_floatOrNone(row.get("benchmark_financial_score")),
        mediaImpact=_floatOrNone(row.get("media_external_impact_score")),
        mediaFinancial=_floatOrNone(row.get("media_external_financial_score")),
        contextImpactModifier=impactModifier,
        contextFinancialModifier=financialModifier,
    )

    return SubIssueContextModifierDto(
        subIssueCode=subIssueCode,
        profileSource=profile.profileSource,
        profileConfidence=_roundOrNone(profileConfidence),
        impactModifier=round(float(impactModifier), 4),
        financialModifier=round(float(financialModifier), 4),
        contextModifier=_combinedModifier(impactModifier, financialModifier),
        rawFinalImpactScore=_roundOrNone(raw.finalImpactScore),
        finalImpactScoreAfterModifier=_roundOrNone(final.finalImpactScore),
        rawFinalFinancialScore=_roundOrNone(raw.finalFinancialScore),
        finalFinancialScoreAfterModifier=_roundOrNone(final.finalFinancialScore),
        rawFinalScore=_roundOrNone(raw.finalScore),
        finalScoreAfterModifier=_roundOrNone(final.finalScore),
        adjustedFinalScore=_roundOrNone(final.finalScore),
        guardAppliedYn=guardAppliedYn,
        guardReason=guardReason,
        appliedRules=rules,
    )


def _buildModifierPayload(modifiers: list[SubIssueContextModifierDto]) -> dict:
    return {
        "ruleVersion": MODIFIER_RULE_VERSION,
        "modifierType": "ADDITIVE",
        "modifierRange": {"min": MVP_MODIFIER_MIN, "max": MVP_MODIFIER_MAX},
        "systemModifierRange": {"min": SYSTEM_MODIFIER_MIN, "max": SYSTEM_MODIFIER_MAX},
        "rankGuard": {
            "maxRankMovement": MAX_RANK_MOVEMENT,
            "top5EntryRawRankLimit": TOP5_ENTRY_RAW_RANK_LIMIT,
            "minProfileConfidenceForModifier": MIN_PROFILE_CONFIDENCE_FOR_MODIFIER,
        },
        "scoreFormula": {
            "impact": "clamp(raw_final_impact_score + context_impact_modifier, 0, 5)",
            "financial": "clamp(raw_final_financial_score + context_financial_modifier, 0, 5)",
        },
        "modifiers": [item.model_dump() for item in modifiers],
        "appliedRuleCount": sum(len(item.appliedRules) for item in modifiers),
    }


def _assignRawRanks(items: list[SubIssueContextModifierDto]) -> None:
    ranked = sorted(
        [item for item in items if item.rawFinalScore is not None],
        key=lambda item: (-float(item.rawFinalScore), item.subIssueCode),
    )
    for rank, item in enumerate(ranked, start=1):
        item.rawRank = rank


def _assignAdjustedRanks(items: list[SubIssueContextModifierDto]) -> None:
    ranked = sorted(
        [item for item in items if item.adjustedFinalScore is not None],
        key=lambda item: (-float(item.adjustedFinalScore), item.subIssueCode),
    )
    adjustedByCode = {item.subIssueCode: rank for rank, item in enumerate(ranked, start=1)}
    for item in items:
        item.adjustedRank = adjustedByCode.get(item.subIssueCode)
        if item.rawRank is None or item.adjustedRank is None:
            item.rankDelta = None
            item.rankChangedYn = False
            continue
        item.rankDelta = item.rawRank - item.adjustedRank
        item.rankChangedYn = item.rankDelta != 0


def _rankGuardViolation(item: SubIssueContextModifierDto) -> Optional[str]:
    if item.rawRank is None or item.adjustedRank is None:
        return None
    if item.adjustedRank <= 5 and item.rawRank > TOP5_ENTRY_RAW_RANK_LIMIT:
        return "TOP5_RAW_RANK_LIMIT"
    if item.rankDelta is not None and abs(item.rankDelta) > MAX_RANK_MOVEMENT:
        return "RANK_MOVEMENT_LIMIT"
    return None


def _zeroModifier(item: SubIssueContextModifierDto, reason: str) -> None:
    item.impactModifier = 0.0
    item.financialModifier = 0.0
    item.contextModifier = 0.0
    item.finalImpactScoreAfterModifier = item.rawFinalImpactScore
    item.finalFinancialScoreAfterModifier = item.rawFinalFinancialScore
    item.finalScoreAfterModifier = item.rawFinalScore
    item.adjustedFinalScore = item.rawFinalScore
    item.appliedRules = []
    item.guardAppliedYn = True
    item.guardReason = reason


def _hasNonZeroModifier(item: SubIssueContextModifierDto) -> bool:
    return abs(item.impactModifier) > 0.00001 or abs(item.financialModifier) > 0.00001


def _combinedModifier(impactModifier: float, financialModifier: float) -> float:
    return round((float(impactModifier) + float(financialModifier)) / 2.0, 4)


def _toFactDtos(rows: list[dict]) -> list[CompanyContextFactDto]:
    facts = []
    for row in rows:
        facts.append(
            CompanyContextFactDto(
                sourceTable=row.get("source_table", ""),
                metricId=row.get("metric_id"),
                atomicMetricId=row.get("atomic_metric_id"),
                metricName=row.get("metric_name"),
                atomicName=row.get("atomic_name"),
                valueNumeric=_floatOrNone(row.get("value_numeric")),
                valueText=row.get("value_text"),
                unit=row.get("unit"),
            )
        )
    return facts


def _rule(ruleId: str, subIssueCode: str, impact: float, financial: float, reason: str) -> ContextRuleHitDto:
    return ContextRuleHitDto(
        ruleId=ruleId,
        subIssueCode=subIssueCode,
        impactModifier=impact,
        financialModifier=financial,
        reason=reason,
    )


def _combinedText(runContext: dict, facts: list[CompanyContextFactDto]) -> str:
    parts = [
        str(runContext.get("industry_profile") or ""),
        str(runContext.get("company_code") or ""),
        str(runContext.get("company_scope_type") or ""),
    ]
    for fact in facts:
        parts.extend([
            fact.metricId or "",
            fact.atomicMetricId or "",
            fact.metricName or "",
            fact.atomicName or "",
            fact.valueText or "",
            str(fact.valueNumeric if fact.valueNumeric is not None else ""),
            fact.unit or "",
        ])
    return " ".join(parts).lower()


def _hasAny(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _levelByKeywords(text: str, high: list[str], medium: list[str]) -> str:
    if _hasAny(text, high):
        return "high"
    if _hasAny(text, medium):
        return "medium"
    return "unknown"


def _businessScaleExposure(facts: list[CompanyContextFactDto]) -> str:
    revenueValues = [
        fact.valueNumeric for fact in facts
        if fact.valueNumeric is not None
        and fact.metricId == "G0-02"
        and (fact.unit or "").upper() in ["KRW", "WON", ""]
    ]
    if not revenueValues:
        return "unknown"
    maxRevenue = max(revenueValues)
    if maxRevenue >= 10_000_000_000_000:
        return "high"
    if maxRevenue >= 1_000_000_000_000:
        return "medium"
    return "low"


def _firstTextByMetric(facts: list[CompanyContextFactDto], metricId: str) -> Optional[str]:
    for fact in facts:
        if fact.metricId == metricId and fact.valueText:
            return fact.valueText[:200]
    return None


def _unique(values: list[Optional[str]]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _profileConfidence(profile: CompanyContextProfileDto) -> float:
    if profile.confidence is not None:
        return round(clamp(float(profile.confidence), 0, 1), 4)
    return _profileConfidenceFromValues([
        profile.industryExposure,
        profile.valueChainExposure,
        profile.globalCustomerExposure,
        profile.euRegulationExposure,
        profile.transitionExposure,
        profile.supplyChainDependency,
        profile.productSafetyExposure,
        profile.businessScaleExposure,
    ])


def _profileConfidenceFromValues(values: list[str]) -> float:
    observed = len([value for value in values if value != "unknown"])
    return round(min(1.0, 0.25 + observed * 0.09), 4)


def _floatOrNone(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _roundOrNone(value) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 4)


def _parseJsonDict(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


__all__ = [
    "applyModifiers",
    "applyCompanyContextModifiers",
    "getProfile",
    "getCompanyContextProfile",
    "buildProfile",
    "buildCompanyContextProfile",
    "calcModifier",
    "calculateContextModifier",
    "applyRankGuards",
    "applyRankMovementGuards",
    "checkObservedStage",
    "hasObservedStage",
]
