from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from src.models.dmaengine import (
    ExtractedFactsV13,
    ScorePurposeV13,
    ScreeningTraceV13,
)
from src.utils import dmaruleregistry, dmascoring
from src.repositories.dmarepository import step4BuildTrace


def step0BuildFactTrace(
    *,
    extractedFact: ExtractedFactsV13 | Mapping[str, Any],
    sourceChannel: str,
) -> dict:
    # STEP 0. Fact-only DTO를 v1.3 Trace Payload로 감싼다.
    # Input: ExtractedFactsV13 1건과 sourceChannel.
    # Output: 점수/Screening 없는 ScoringPayloadV13 dict.
    fact = extractedFact if isinstance(extractedFact, ExtractedFactsV13) else ExtractedFactsV13(**dict(extractedFact))
    return step4BuildTrace(
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        sourceChannel=sourceChannel,
        subIssueCode=fact.subIssueCode,
        extractedFacts=fact,
    )


def step1RunCanonical(
    *,
    subIssueCode: Optional[str] = None,
    impactInput: Optional[Mapping[str, Any]] = None,
    financialInput: Optional[Mapping[str, Any]] = None,
    sourceChannel: Optional[str] = None,
    extractedFacts: Optional[ExtractedFactsV13 | Mapping[str, Any]] = None,
) -> dict:
    policy = dmaruleregistry.getPolicy("canonical_scoring_policy")
    axes = dmascoring.step1CalcAxes(policy, impact=impactInput, financial=financialInput)
    axisScores = [score for score in axes.values() if score is not None]
    return step4BuildTrace(
        scorePurpose=ScorePurposeV13.CANONICAL_IRO,
        sourceChannel=sourceChannel,
        subIssueCode=subIssueCode,
        extractedFacts=extractedFacts,
        axisScores=axisScores,
        ruleVersion=dmaruleregistry.getRuleVersion(),
        configHash=dmaruleregistry.getConfigHash(),
    )


def step2RunScreening(channel: str, payload: Mapping[str, Any]) -> dict:
    screeningPolicy = dmaruleregistry.getPolicy("screening_policy")
    normalizedChannel = str(channel)

    def buildPayload(
        trace: ScreeningTraceV13,
        subIssueCode: Optional[str] = None,
        sourceChannel: Optional[str] = None,
    ) -> dict:
        return step4BuildTrace(
            scorePurpose=trace.scorePurpose,
            sourceChannel=sourceChannel or normalizedChannel,
            subIssueCode=subIssueCode,
            screeningTrace=[trace],
            ruleVersion=dmaruleregistry.getRuleVersion(),
            configHash=dmaruleregistry.getConfigHash(),
        )

    if normalizedChannel == "benchmark":
        trace = dmascoring.step2CalcBenchmark(str(payload["observation"]), screeningPolicy)
        trace = trace.model_copy(update={
            "capability": dmaruleregistry.getCapability("benchmarkScreening"),
            "rawInputs": {
                **trace.rawInputs,
                "leaderObserved": bool(payload.get("leaderObserved")),
                "peerObserved": bool(payload.get("peerObserved")),
                "ownObserved": bool(payload.get("ownObserved")),
            },
        })
        return buildPayload(trace, subIssueCode=payload.get("subIssueCode"))

    if normalizedChannel == "regulation":
        trace = dmascoring.step2CalcRegulation(str(payload["regime"]), str(payload["applicability"]), screeningPolicy)
        rawInputs = {
            **trace.rawInputs,
            "sourceStep": "media_external",
            "sourceType": "regulation",
            "companyId": payload.get("companyId"),
            "reportingYear": payload.get("reportingYear"),
            "inputMethod": payload.get("inputMethod"),
            "sourceDocumentRef": payload.get("sourceDocumentRef"),
            "reviewStatus": payload.get("reviewStatus"),
            "reviewerComment": payload.get("reviewerComment"),
            "mappingReason": payload.get("mappingReason"),
        }
        trace = trace.model_copy(update={
            "capability": dmaruleregistry.getCapability("regulationBaseScreening"),
            "rawInputs": rawInputs,
        })
        return buildPayload(trace, subIssueCode=payload.get("subIssueCode"), sourceChannel="media_external")

    if normalizedChannel == "kcgs":
        kcgsPolicy = screeningPolicy["kcgs"]
        latestGrade = str(payload.get("latestGrade") or payload["grade"])
        state = dmascoring.step2CalcKcgs(latestGrade, str(payload["trend"]), screeningPolicy)
        subIssueBoost = dmascoring.step2CalcKcgsBoost(state["pillarSignal"], screeningPolicy)
        # KCGS pillar movement is a symmetric E/S/G domain-level media_external signal.
        # It participates in external MAX but is not added again at Top20.
        trace = ScreeningTraceV13(
            channel="kcgs_pillar_domain_signal",
            scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
            impactSignal=state["pillarSignal"],
            financialSignal=state["pillarSignal"],
            status=state["status"],
            capability=dmaruleregistry.getCapability("kcgsPillarSignal"),
            rawInputs={
                "sourceStep": "media_external",
                "sourceType": "agency",
                "providerKey": "kcgs",
                "companyId": payload.get("companyId"),
                "ratingYears": list(payload.get("ratingYears") or []),
                "overallGradeHistory": list(payload.get("overallGradeHistory") or []),
                "pillar": payload.get("pillar"),
                "pillarGradeHistory": list(payload.get("pillarGradeHistory") or []),
                "previousGrade": payload.get("previousGrade"),
                "latestGrade": latestGrade,
                "trend": payload.get("trend"),
                "stepDifference": payload.get("stepDifference"),
                "inputSourceType": payload.get("inputSourceType"),
                "sourceDocumentRefs": list(payload.get("sourceDocumentRefs") or []),
                "reviewStatusHistory": list(payload.get("reviewStatusHistory") or []),
                "gradeRisk": state["gradeRisk"],
                "trendModifier": state["trendModifier"],
                "pillarSignal": state["pillarSignal"],
                "subIssueBoost": subIssueBoost,
                "propagationMode": kcgsPolicy["propagationMode"],
                "overallGradeTraceOnlyYn": kcgsPolicy["overallGradeTraceOnlyYn"],
                "externalMaxEligibleYn": kcgsPolicy["externalMaxEligibleYn"],
                "top20BoostOnlyYn": kcgsPolicy["top20BoostOnlyYn"],
                "axisMode": kcgsPolicy["axisMode"],
                "directCanonicalFinalAllowedYn": kcgsPolicy["directCanonicalFinalAllowedYn"],
            },
        )
        return buildPayload(
            trace,
            subIssueCode=payload.get("subIssueCode"),
            sourceChannel="media_external",
        )

    if normalizedChannel == "externalMax":
        signals = [
            item if isinstance(item, ScreeningTraceV13) else ScreeningTraceV13(**item)
            for item in payload["signals"]
        ]
        trace = dmascoring.step2CalcExternalMax(signals, screeningPolicy)
        return buildPayload(
            trace,
            subIssueCode=payload.get("subIssueCode"),
            sourceChannel="media_external",
        )

    if normalizedChannel == "surveyOverlay":
        surveyPolicy = dmaruleregistry.getPolicy("survey_policy")
        overlay = dmascoring.step2CalcSurveyOverlay(payload["normalizedRows"], surveyPolicy)
        observed = overlay["impactObservedCount"] > 0 or overlay["financialObservedCount"] > 0
        trace = ScreeningTraceV13(
            channel="survey_overlay",
            scorePurpose=ScorePurposeV13.STAKEHOLDER_OVERLAY,
            impactSignal=overlay["impactOverlay"],
            financialSignal=overlay["financialOverlay"],
            status=dmascoring.STATUS_OBSERVED if observed else dmascoring.STATUS_UNOBSERVED,
            capability=dmaruleregistry.getCapability("surveyAggregation"),
            rawInputs=overlay,
        )
        return buildPayload(trace)

    raise ValueError(f"Unknown screening channel: {channel!r}")


def step3RunSelection(items: Sequence[Mapping[str, Any]]) -> dict:
    policy = dmaruleregistry.getPolicy("selection_policy")
    return dmascoring.step3RunSelection(items, policy)


__all__ = [
    "step0BuildFactTrace",
    "step1RunCanonical",
    "step2RunScreening",
    "step3RunSelection",
]
