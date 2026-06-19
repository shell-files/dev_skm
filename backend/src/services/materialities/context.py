"""
context.py
레이어: Service (materialities)
역할: 기업 컨텍스트 프로필·수정자 저장 서비스.
"""
from __future__ import annotations

import json
from typing import Optional

from src.models.materialitycontext import (
    CompanyContextFactDto,
    CompanyContextModifierResponseDto,
    CompanyContextProfileResponseDto,
    CompanyContextProfileDto,
    SubIssueContextModifierDto,
)
from src.services.materialities.contextbuilder import (
    MIN_PROFILE_CONFIDENCE_FOR_MODIFIER,
    MODIFIER_RULE_VERSION,
    MVP_MODIFIER_MAX,
    MVP_MODIFIER_MIN,
    SYSTEM_MODIFIER_MAX,
    SYSTEM_MODIFIER_MIN,
    MAX_RANK_MOVEMENT,
    TOP5_ENTRY_RAW_RANK_LIMIT,
    applyRankGuards,
    buildProfile,
    calcModifier,
    checkObservedStage,
    _floatOrNone,
    _profileConfidence,
)
from src.services.materialities.contextgraph import buildCompanyContextProfileWithOptionalGraph
from src.repositories.companycontextrepository import (
    getLatestProfile,
    getRun,
    listG0Facts,
    listScoreRows,
    replaceProfile,
    updateModifiers,
)
from src.repositories.dmarepository import recalcFinal, updateRanks
from src.utils.subissuemaster import subissueMaster


def applyModifiers(runId: int) -> CompanyContextModifierResponseDto:
    """G0 Fact 기반 컨텍스트 프로필을 빌드하고 서브이슈별 modifier를 계산해 DB에 적용한다."""
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
    """저장된 최신 컨텍스트 프로필과 modifier 목록을 조회해 반환한다."""
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


# 이전 공개 이름과의 호환성 래퍼

def applyCompanyContextModifiers(runId: int, userModel) -> CompanyContextModifierResponseDto:
    """applyModifiers의 이전 공개 이름 호환 래퍼."""
    return applyModifiers(runId)


def getCompanyContextProfile(runId: int, userModel) -> CompanyContextProfileResponseDto:
    """getProfile의 이전 공개 이름 호환 래퍼."""
    return getProfile(runId)


def buildCompanyContextProfile(
    runId: int,
    runContext: dict,
    facts: list[CompanyContextFactDto],
) -> CompanyContextProfileDto:
    """buildProfile의 이전 공개 이름 호환 래퍼."""
    return buildProfile(runId, runContext, facts)


def calculateContextModifier(
    profile: CompanyContextProfileDto,
    row: dict,
    profileConfidence: Optional[float] = None,
) -> SubIssueContextModifierDto:
    """calcModifier의 이전 공개 이름 호환 래퍼."""
    return calcModifier(profile, row, profileConfidence)


def applyRankMovementGuards(
    modifiers: list[SubIssueContextModifierDto],
) -> list[SubIssueContextModifierDto]:
    """applyRankGuards의 이전 공개 이름 호환 래퍼."""
    return applyRankGuards(modifiers)


def hasObservedStage(row: dict) -> bool:
    """checkObservedStage의 이전 공개 이름 호환 래퍼."""
    return checkObservedStage(row)


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
