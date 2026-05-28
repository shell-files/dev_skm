from __future__ import annotations

from typing import Optional

from src.models.materialitycontext import (
    CompanyContextFactDto,
    CompanyContextModifierResponseDto,
    CompanyContextProfileDto,
    ContextRuleHitDto,
    SubIssueContextModifierDto,
)
from src.utils.companycontextrepository import (
    getCompanyG0Facts,
    getDmaScoreSummaryRowsForContext,
    getMaterialityRunContext,
    replaceCompanyContextProfile,
    updateContextModifiers,
)
from src.utils.dmaaggregator import calculateFinalMateriality
from src.utils.dmarepository import recalculateFinalScore
from src.utils.dmascoring import clamp
from src.utils.subissuemaster import subissueMaster


MODIFIER_MIN = -0.5
MODIFIER_MAX = 0.5
MODIFIER_RULE_VERSION = "company-context-modifier-v1"


def applyCompanyContextModifiers(runId: int) -> CompanyContextModifierResponseDto:
    runContext = getMaterialityRunContext(runId)
    if not runContext:
        return CompanyContextModifierResponseDto(
            runId=runId,
            implementationStatus="NO_RUN",
            messages=["No ESG_MATERIALITY_RUN row found for runId."],
        )

    companyId = int(runContext["company_id"])
    reportingYear = int(runContext["reporting_year"])
    facts = _toFactDtos(getCompanyG0Facts(companyId, reportingYear))
    profile = buildCompanyContextProfile(runId, runContext, facts)
    summaryRows = getDmaScoreSummaryRowsForContext(runId)

    modifiers = [
        calculateContextModifier(profile, row)
        for row in summaryRows
        if row.get("sub_issue_code") in subissueMaster
    ]
    modifierPayload = _buildModifierPayload(modifiers)
    contextPayload = {
        "profile": profile.model_dump(),
        "profileSource": profile.profileSource,
        "ruleVersion": MODIFIER_RULE_VERSION,
    }
    contextProfileId = replaceCompanyContextProfile(
        runId=runId,
        companyId=companyId,
        reportingYear=reportingYear,
        industryProfile=profile.industryProfile,
        businessModel=profile.businessModel,
        contextPayload=contextPayload,
        modifierPayload=modifierPayload,
        confidenceScore=_profileConfidence(profile),
    )

    updatedCount = updateContextModifiers(
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
        recalculateFinalScore(runId, item.subIssueCode)
        recalculatedCount += 1

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
        stageScoreChangedYn=False,
        messages=[
            "Context modifiers were applied only to final aggregation.",
            "Benchmark/media/survey stage scores were not changed.",
        ],
        rawPayload={
            "ruleVersion": MODIFIER_RULE_VERSION,
            "modifierJson": modifierPayload,
        },
    )


def buildCompanyContextProfile(
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
        facts=facts,
    )


def calculateContextModifier(profile: CompanyContextProfileDto, row: dict) -> SubIssueContextModifierDto:
    subIssueCode = row.get("sub_issue_code")
    rules: list[ContextRuleHitDto] = []

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

    impactModifier = clamp(sum(item.impactModifier for item in rules), MODIFIER_MIN, MODIFIER_MAX)
    financialModifier = clamp(sum(item.financialModifier for item in rules), MODIFIER_MIN, MODIFIER_MAX)
    return _withScorePreview(row, impactModifier, financialModifier, rules)


def _withScorePreview(
    row: dict,
    impactModifier: float,
    financialModifier: float,
    rules: list[ContextRuleHitDto],
) -> SubIssueContextModifierDto:
    subIssueCode = row.get("sub_issue_code")
    raw = calculateFinalMateriality(
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
    final = calculateFinalMateriality(
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
        impactModifier=round(float(impactModifier), 4),
        financialModifier=round(float(financialModifier), 4),
        rawFinalImpactScore=_roundOrNone(raw.finalImpactScore),
        finalImpactScoreAfterModifier=_roundOrNone(final.finalImpactScore),
        rawFinalFinancialScore=_roundOrNone(raw.finalFinancialScore),
        finalFinancialScoreAfterModifier=_roundOrNone(final.finalFinancialScore),
        rawFinalScore=_roundOrNone(raw.finalScore),
        finalScoreAfterModifier=_roundOrNone(final.finalScore),
        appliedRules=rules,
    )


def _buildModifierPayload(modifiers: list[SubIssueContextModifierDto]) -> dict:
    return {
        "ruleVersion": MODIFIER_RULE_VERSION,
        "modifierType": "ADDITIVE",
        "modifierRange": {"min": MODIFIER_MIN, "max": MODIFIER_MAX},
        "scoreFormula": {
            "impact": "clamp(raw_final_impact_score + context_impact_modifier, 0, 5)",
            "financial": "clamp(raw_final_financial_score + context_financial_modifier, 0, 5)",
        },
        "modifiers": [item.model_dump() for item in modifiers],
        "appliedRuleCount": sum(len(item.appliedRules) for item in modifiers),
    }


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
    observed = len([value for value in [
        profile.industryExposure,
        profile.valueChainExposure,
        profile.globalCustomerExposure,
        profile.euRegulationExposure,
        profile.transitionExposure,
        profile.supplyChainDependency,
        profile.productSafetyExposure,
        profile.businessScaleExposure,
    ] if value != "unknown"])
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
