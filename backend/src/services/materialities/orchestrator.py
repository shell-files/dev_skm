"""
Domain: DMA Materiality (v1.3 MVP)
Layer: service/orchestrator
Responsibility:
- Compose registry policies, pure scoring helpers, and v1.3 payload trace builders.
- Keep Phase B foundation isolated from legacy runtime service wiring.
Do not:
- do not mutate DB state
- do not call API routers
- do not connect Redis / Kafka / Docker runtime paths
- do not migrate existing service flows in Phase B
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from src.models.dmaengine import ExtractedFactsV13, ScorePurposeV13, ScreeningTraceV13
from src.utils import dmaruleregistry, dmascoring
from src.utils.dmarepository import step4BuildTrace


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

    def buildPayload(trace: ScreeningTraceV13) -> dict:
        return step4BuildTrace(
            scorePurpose=trace.scorePurpose,
            sourceChannel=normalizedChannel,
            screeningTrace=[trace],
            ruleVersion=dmaruleregistry.getRuleVersion(),
            configHash=dmaruleregistry.getConfigHash(),
        )

    if normalizedChannel == "benchmark":
        trace = dmascoring.step2CalcBenchmark(str(payload["observation"]), screeningPolicy)
        trace = trace.model_copy(update={"capability": dmaruleregistry.getCapability("benchmarkScreening")})
        return buildPayload(trace)

    if normalizedChannel == "regulation":
        trace = dmascoring.step2CalcRegulation(str(payload["regime"]), str(payload["applicability"]), screeningPolicy)
        trace = trace.model_copy(update={"capability": dmaruleregistry.getCapability("regulationBaseScreening")})
        return buildPayload(trace)

    if normalizedChannel == "kcgs":
        state = dmascoring.step2CalcKcgs(str(payload["grade"]), str(payload["trend"]), screeningPolicy)
        subIssueBoost = dmascoring.step2CalcKcgsBoost(state["pillarSignal"], screeningPolicy)
        # KCGS pillar movement is not an axis score. Preserve it only as a Top20 boost hint.
        trace = ScreeningTraceV13(
            channel="kcgs_pillar_boost",
            scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
            impactSignal=None,
            financialSignal=None,
            status=state["status"],
            capability=dmaruleregistry.getCapability("kcgsPillarSignal"),
            rawInputs={
                **state,
                "subIssueBoost": subIssueBoost,
                "directCanonicalFinalAllowedYn": screeningPolicy["kcgs"]["directCanonicalFinalAllowedYn"],
            },
        )
        return buildPayload(trace)

    if normalizedChannel == "externalMax":
        signals = [
            item if isinstance(item, ScreeningTraceV13) else ScreeningTraceV13(**item)
            for item in payload["signals"]
        ]
        trace = dmascoring.step2CalcExternalMax(signals, screeningPolicy)
        return buildPayload(trace)

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


__all__ = ["step0BuildFactTrace", "step1RunCanonical", "step2RunScreening", "step3RunSelection"]
