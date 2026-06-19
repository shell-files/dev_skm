"""
screeningbuilder.py
레이어: Service (materialities)
역할: Pre-Survey Screening 신호 구성 — 미디어·벤치마크 기반 후보 이슈 1차 선별.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.models.dmaengine import (
    ExtractedFactsV13,
    KcgsGradeInputV13,
    MediaNewsDedupTraceV13,
    MediaNewsEventResolutionTraceV13,
    RegulationApplicabilityInputV13,
    RegulationSubIssueMappingSeedV13,
    ScorePurposeV13,
    ScreeningTraceV13,
)
from src.repositories.dmarepository import (
    step4BuildTrace,
    MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
)
from src.services.materialities.orchestrator import step2RunScreening
from src.utils import dmaruleregistry, dmascoring
from src.utils.subissuemaster import subissueMaster

REGULATION_INPUT_METHODS = ("CONSULTANT_INPUT", "MANUAL", "POLICY_SEED")
REGULATION_REVIEW_STATUSES = ("APPROVED", "DRAFT", "REVIEWED")
KCGS_INPUT_SOURCE_TYPES = ("MANUAL", "IMPORT")
KCGS_REVIEW_STATUSES = ("APPROVED", "DRAFT", "REVIEWED")
KCGS_PILLAR_GRADE_FIELDS = (
    ("E", "environmentGrade"),
    ("S", "socialGrade"),
    ("G", "governanceGrade"),
)

_EXTERNAL_MAX_EXPECTED_SOURCE_TYPE: dict[str, str] = {
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP: "news",
    MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP: "regulation",
    MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP: "agency",
}


def step2ResolveBenchmarkObservation(row: Mapping[str, Any]) -> str:
    if not (row.get("sub_issue_code") or row.get("subIssueCode")):
        raise ValueError("sub_issue_code is required for benchmark observation resolution")

    leaderObserved = int(row.get("leader_observed") or 0) > 0
    peerObserved = int(row.get("peer_observed") or 0) > 0
    ownObserved = int(row.get("own_observed") or 0) > 0

    if leaderObserved and peerObserved and not ownObserved:
        return "BLIND_SPOT"
    if leaderObserved and peerObserved:
        return "COMMON_ISSUE"
    return "NONE"


def step2BuildBenchmarkScreeningPayloads(
    factPayloads: Sequence[Mapping[str, Any]],
    universeSubIssueCodes: Sequence[str],
) -> list[dict]:
    universeSet = set(universeSubIssueCodes)
    observedByCode: dict[str, dict[str, bool]] = {}
    for fp in factPayloads:
        if not isinstance(fp, dict):
            raise ValueError("benchmark fact payload must be a dict")
        ef = fp.get("extractedFacts")
        if not isinstance(ef, dict):
            raise ValueError("extractedFacts is required and must be a dict")
        code = ef.get("subIssueCode")
        if not code:
            raise ValueError("extractedFacts.subIssueCode is required")
        stype = ef.get("sourceType")
        if stype not in ("leader_sr", "peer_sr", "own_sr"):
            raise ValueError(f"invalid benchmark sourceType: {stype!r}")
        if code not in universeSet:
            raise ValueError(f"subIssueCode is outside benchmark universe: {code!r}")
        if code not in observedByCode:
            observedByCode[code] = {}
        observedByCode[code][stype] = True

    screeningPayloads = []
    for code in universeSubIssueCodes:
        obs = observedByCode.get(code, {})
        leaderObserved = bool(obs.get("leader_sr"))
        peerObserved = bool(obs.get("peer_sr"))
        ownObserved = bool(obs.get("own_sr"))
        backfilledYn = code not in observedByCode

        row = {
            "sub_issue_code": code,
            "leader_observed": 1 if leaderObserved else 0,
            "peer_observed": 1 if peerObserved else 0,
            "own_observed": 1 if ownObserved else 0,
        }
        observation = step2ResolveBenchmarkObservation(row)

        payload = step2RunScreening("benchmark", {
            "subIssueCode": code,
            "observation": observation,
            "leaderObserved": leaderObserved,
            "peerObserved": peerObserved,
            "ownObserved": ownObserved,
        })

        stList = payload.get("screeningTrace")
        if isinstance(stList, list) and stList and isinstance(stList[0], dict):
            ri = dict(stList[0].get("rawInputs") or {})
            ri["backfilledYn"] = backfilledYn
            stList[0]["rawInputs"] = ri

        screeningPayloads.append(payload)

    return screeningPayloads


def step2BuildRegulationScreeningPayloads(
    applicabilityInputs: Sequence[RegulationApplicabilityInputV13 | Mapping[str, Any]],
    mappingRows: Sequence[RegulationSubIssueMappingSeedV13 | Mapping[str, Any]],
) -> list[dict]:
    screeningPolicy = dmaruleregistry.getPolicy("screening_policy")
    regulationPolicy = screeningPolicy.get("regulation")
    if not isinstance(regulationPolicy, Mapping):
        raise ValueError("screening_policy.regulation is required")

    inputs = [
        item if isinstance(item, RegulationApplicabilityInputV13)
        else RegulationApplicabilityInputV13(**dict(item))
        for item in applicabilityInputs
    ]
    mappings = [
        item if isinstance(item, RegulationSubIssueMappingSeedV13)
        else RegulationSubIssueMappingSeedV13(**dict(item))
        for item in mappingRows
    ]

    approvedInputs = {}
    for item in inputs:
        if item.regime not in regulationPolicy:
            raise ValueError(f"Unknown regulation regime: {item.regime!r}")
        regimePolicy = regulationPolicy[item.regime]
        if not isinstance(regimePolicy, Mapping) or item.applicability not in regimePolicy:
            raise ValueError(f"Unknown regulation applicability: {item.applicability!r}")
        if item.inputMethod not in REGULATION_INPUT_METHODS:
            raise ValueError(f"Unknown regulation inputMethod: {item.inputMethod!r}")
        if item.reviewStatus not in REGULATION_REVIEW_STATUSES:
            raise ValueError(f"Unknown regulation reviewStatus: {item.reviewStatus!r}")
        if item.reviewStatus != "APPROVED":
            continue
        key = (item.companyId, item.reportingYear, item.regime)
        if key in approvedInputs:
            raise ValueError(
                "Duplicate APPROVED regulation applicability input: "
                f"companyId={item.companyId}, reportingYear={item.reportingYear}, regime={item.regime}"
            )
        approvedInputs[key] = item

    approvedMappingsByRegime: dict[str, list[RegulationSubIssueMappingSeedV13]] = {}
    mappingKeys = set()
    for item in mappings:
        if item.regime not in regulationPolicy:
            raise ValueError(f"Unknown regulation mapping regime: {item.regime!r}")
        if item.reviewStatus not in REGULATION_REVIEW_STATUSES:
            raise ValueError(f"Unknown regulation mapping reviewStatus: {item.reviewStatus!r}")
        if not item.subIssueCode:
            raise ValueError("regulation mapping subIssueCode is required")
        if item.subIssueCode not in subissueMaster:
            raise ValueError(f"Unknown regulation mapping subIssueCode: {item.subIssueCode!r}")
        key = (item.regime, item.subIssueCode)
        if key in mappingKeys:
            raise ValueError(
                "Duplicate regulation sub-issue mapping seed: "
                f"regime={item.regime}, subIssueCode={item.subIssueCode}"
            )
        mappingKeys.add(key)
        if item.reviewStatus == "APPROVED" and item.activeYn:
            approvedMappingsByRegime.setdefault(item.regime, []).append(item)

    rows = []
    for key in sorted(approvedInputs.keys()):
        item = approvedInputs[key]
        for mapping in sorted(
            approvedMappingsByRegime.get(item.regime, []),
            key=lambda row: row.subIssueCode,
        ):
            rows.append((item.companyId, item.reportingYear, item.regime, mapping.subIssueCode, item, mapping))

    return [
        step2RunScreening("regulation", {
            "companyId": item.companyId,
            "reportingYear": item.reportingYear,
            "regime": item.regime,
            "applicability": item.applicability,
            "inputMethod": item.inputMethod,
            "sourceDocumentRef": item.sourceDocumentRef,
            "reviewStatus": item.reviewStatus,
            "reviewerComment": item.reviewerComment,
            "subIssueCode": mapping.subIssueCode,
            "mappingReason": mapping.mappingReason,
        })
        for _, _, _, _, item, mapping in rows
    ]


def step2BuildKcgsPillarBoostPayloads(
    gradeRows: Sequence[KcgsGradeInputV13 | Mapping[str, Any]],
) -> list[dict]:
    screeningPolicy = dmaruleregistry.getPolicy("screening_policy")
    kcgsPolicy = screeningPolicy["kcgs"]
    gradeOrder = set(kcgsPolicy["gradeOrderBestToWorst"])

    inputs = [
        item if isinstance(item, KcgsGradeInputV13)
        else KcgsGradeInputV13(**dict(item))
        for item in gradeRows
    ]

    approvedInputs: list[KcgsGradeInputV13] = []
    for item in inputs:
        if item.reviewStatus not in KCGS_REVIEW_STATUSES:
            raise ValueError(f"Unknown KCGS reviewStatus: {item.reviewStatus!r}")
        if item.inputSourceType not in KCGS_INPUT_SOURCE_TYPES:
            raise ValueError(f"Unknown KCGS inputSourceType: {item.inputSourceType!r}")
        for fieldName in ("overallGrade", "environmentGrade", "socialGrade", "governanceGrade"):
            grade = getattr(item, fieldName)
            if grade not in gradeOrder:
                raise ValueError(f"Unknown KCGS {fieldName}: {grade!r}")
        if item.reviewStatus == "APPROVED":
            approvedInputs.append(item)

    if not approvedInputs:
        return []
    if len(approvedInputs) != 3:
        raise ValueError(
            f"KCGS pillar boost requires exactly 3 APPROVED rows, got {len(approvedInputs)}"
        )

    companyIds = {item.companyId for item in approvedInputs}
    if len(companyIds) != 1:
        raise ValueError(f"KCGS pillar boost rows must belong to one company, got {sorted(companyIds)}")

    years = [item.ratingYear for item in approvedInputs]
    if len(set(years)) != len(years):
        raise ValueError(f"Duplicate APPROVED KCGS ratingYear detected: {sorted(years)}")
    orderedInputs = sorted(approvedInputs, key=lambda item: item.ratingYear)
    orderedYears = [item.ratingYear for item in orderedInputs]
    if orderedYears != list(range(orderedYears[0], orderedYears[0] + 3)):
        raise ValueError(f"KCGS APPROVED rating years must be consecutive, got {orderedYears}")

    previousInput = orderedInputs[-2]
    latestInput = orderedInputs[-1]
    companyId = latestInput.companyId
    overallGradeHistory = [
        {"ratingYear": item.ratingYear, "grade": item.overallGrade}
        for item in orderedInputs
    ]
    sourceDocumentRefs = [
        {"ratingYear": item.ratingYear, "sourceDocumentRef": item.sourceDocumentRef}
        for item in orderedInputs
    ]
    reviewStatusHistory = [
        {"ratingYear": item.ratingYear, "reviewStatus": item.reviewStatus}
        for item in orderedInputs
    ]
    inputSourceType = latestInput.inputSourceType

    payloads: list[dict] = []
    for pillar, fieldName in KCGS_PILLAR_GRADE_FIELDS:
        previousGrade = getattr(previousInput, fieldName)
        latestGrade = getattr(latestInput, fieldName)
        trend = dmascoring.step2ResolveKcgsTrend(previousGrade, latestGrade, screeningPolicy)
        pillarGradeHistory = [
            {"ratingYear": item.ratingYear, "grade": getattr(item, fieldName)}
            for item in orderedInputs
        ]
        for subIssueCode, metadata in sorted(subissueMaster.items()):
            if metadata.get("domain") != pillar:
                continue
            payloads.append(step2RunScreening("kcgs", {
                "companyId": companyId,
                "ratingYears": orderedYears,
                "overallGradeHistory": overallGradeHistory,
                "pillar": pillar,
                "pillarGradeHistory": pillarGradeHistory,
                "previousGrade": trend["previousGrade"],
                "latestGrade": trend["latestGrade"],
                "grade": trend["latestGrade"],
                "trend": trend["trend"],
                "stepDifference": trend["stepDifference"],
                "inputSourceType": inputSourceType,
                "sourceDocumentRefs": sourceDocumentRefs,
                "reviewStatusHistory": reviewStatusHistory,
                "subIssueCode": subIssueCode,
            }))

    return payloads


def step2BuildMediaExternalMaxPayloads(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict]:
    from collections import defaultdict

    groups: dict[str, list[ScreeningTraceV13]] = defaultdict(list)

    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"External MAX row must be a Mapping, got {type(row)!r}")
        subIssueCode = row.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("subIssueCode is required for External MAX payload")
        if subIssueCode not in subissueMaster:
            raise ValueError(f"Unknown subIssueCode for External MAX: {subIssueCode!r}")

        sourceStep = row.get("sourceStep")
        if sourceStep == MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP:
            channel = "news_canonical"
        elif sourceStep == MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP:
            rawLabel = str(row.get("rawIssueLabel") or "").lower()
            channel = f"regulation_{rawLabel}"
        elif sourceStep == MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP:
            channel = "kcgs_pillar_domain_signal"
        else:
            raise ValueError(
                f"External MAX ineligible sourceStep: {sourceStep!r}. "
                f"Eligible: news_canonical, regulation, and kcgs domain signal only."
            )

        expectedSourceType = _EXTERNAL_MAX_EXPECTED_SOURCE_TYPE[sourceStep]
        if row.get("sourceType") != expectedSourceType:
            raise ValueError(
                f"External MAX sourceType mismatch for sourceStep={sourceStep!r}: "
                f"expected {expectedSourceType!r}, got {row.get('sourceType')!r}"
            )

        rawImpact = row.get("impactSignal")
        rawFinancial = row.get("financialSignal")
        impactSignal = None if rawImpact is None else float(rawImpact)
        financialSignal = None if rawFinancial is None else float(rawFinancial)
        status = (
            dmascoring.STATUS_OBSERVED
            if (impactSignal is not None or financialSignal is not None)
            else dmascoring.STATUS_UNOBSERVED
        )

        if sourceStep == MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP:
            rawInputs: dict[str, Any] = {
                "sourceStep": sourceStep,
                "sourceType": "agency",
                "providerKey": "kcgs",
                "sourceRowId": row.get("id"),
                "rawIssueLabel": row.get("rawIssueLabel"),
            }
        else:
            rawInputs = {"sourceStep": sourceStep}

        trace = ScreeningTraceV13(
            channel=channel,
            scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
            impactSignal=impactSignal,
            financialSignal=financialSignal,
            status=status,
            rawInputs=rawInputs,
        )
        groups[subIssueCode].append(trace)

    payloads = []
    for subIssueCode in sorted(groups.keys()):
        traces = groups[subIssueCode]
        payload = step2RunScreening("externalMax", {
            "subIssueCode": subIssueCode,
            "signals": traces,
        })
        payloads.append(payload)

    return payloads


def _mediaNewsCandidateFingerprint(candidate) -> tuple:
    if candidate is None:
        return ()
    return (
        getattr(candidate, "polarity", None),
        getattr(candidate, "scale", None),
        getattr(candidate, "scope", None),
        getattr(candidate, "likelihood", None),
        getattr(candidate, "irremediability", None),
        getattr(candidate, "timeHorizon", None),
        getattr(candidate, "explicitNoUrgencyYn", None),
        getattr(candidate, "magnitude", None),
    )


def _selectMediaNewsCanonicalRows(
    facts: List[ExtractedFactsV13],
    resolutions: List[MediaNewsEventResolutionTraceV13],
) -> List[Tuple[ExtractedFactsV13, MediaNewsEventResolutionTraceV13]]:
    pairs = list(zip(facts, resolutions))
    output: List[Tuple[ExtractedFactsV13, MediaNewsEventResolutionTraceV13]] = []
    merged_groups: Dict[str, List[int]] = {}

    for idx, (_, r) in enumerate(pairs):
        if r.dedup.dedupStatus == "MERGED" and r.dedup.confirmedEventGroupKey is not None:
            merged_groups.setdefault(r.dedup.confirmedEventGroupKey, []).append(idx)
        else:
            output.append(pairs[idx])

    for _key, indices in merged_groups.items():
        group_pairs = [pairs[i] for i in indices]
        impact_fps = {_mediaNewsCandidateFingerprint(r.impact) for _, r in group_pairs}
        fin_fps = {_mediaNewsCandidateFingerprint(r.financial) for _, r in group_pairs}

        if len(impact_fps) <= 1 and len(fin_fps) <= 1:
            def _sort_key(item: tuple, orig_idx: int) -> tuple:
                fact, r = item
                conf = fact.classificationConfidence if fact.classificationConfidence is not None else 0.0
                pub = ""
                url = ""
                if fact.evidenceSpans:
                    span = fact.evidenceSpans[0]
                    pub = getattr(span, "publishedAt", None) or ""
                    url = getattr(span, "sourceUrl", None) or ""
                stableFactKey = json.dumps(
                    fact.model_dump(mode="json", by_alias=False),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                return (-conf, pub, url, stableFactKey, orig_idx)

            ranked = sorted(
                [(group_pairs[j], indices[j]) for j in range(len(indices))],
                key=lambda x: _sort_key(x[0], x[1]),
            )
            output.append(ranked[0][0])
        else:
            for fact, r in group_pairs:
                demoted = r.model_copy(
                    update={
                        "resolverStatus": "CONFLICTED",
                        "dedup": MediaNewsDedupTraceV13(
                            eventGroupCandidateId=r.dedup.eventGroupCandidateId,
                            confirmedEventGroupKey=None,
                            dedupStatus="CONFLICTED",
                            ruleTrace=list(r.dedup.ruleTrace) + [{
                                "reason": "merged_candidate_fingerprint_mismatch",
                            }],
                        ),
                    }
                )
                output.append((fact, demoted))

    return output


def step1BuildMediaNewsCanonicalPayloads(
    extractedFacts: Sequence[ExtractedFactsV13],
    *,
    evaluationDate: Optional[str] = None,
) -> list[dict]:
    from src.services.medias.eventresolver import (
        resolveMediaNewsCanonicalFactors,
        resolveMediaNewsEventGroup,
        resolveMediaNewsEventObservation,
    )

    resolverPolicy = dmaruleregistry.getPolicy("media_event_resolver_policy")
    canonicalPolicy = dmaruleregistry.getPolicy("canonical_scoring_policy")
    ruleVersion = dmaruleregistry.getRuleVersion()
    configHash = dmaruleregistry.getConfigHash()

    facts = list(extractedFacts)
    if not facts:
        return []

    resolutions = [
        resolveMediaNewsEventObservation(fact, resolverPolicy, evaluationDate=evaluationDate)
        for fact in facts
    ]
    resolutions = resolveMediaNewsEventGroup(resolutions, resolverPolicy)

    canonical_pairs = _selectMediaNewsCanonicalRows(facts, resolutions)

    payloads = []
    for fact, resolution in canonical_pairs:
        can_compute = (
            resolution.dedup.dedupStatus in ("UNIQUE", "MERGED")
            and resolution.resolverStatus in ("RESOLVED", "PARTIAL")
        )
        if can_compute:
            axes = resolveMediaNewsCanonicalFactors(resolution, canonicalPolicy)
            axisScores = [score for score in axes.values() if score is not None]
        else:
            axisScores = []

        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode=fact.subIssueCode,
            extractedFacts=fact,
            axisScores=axisScores,
            eventResolutionTrace=resolution,
            ruleVersion=ruleVersion,
            configHash=configHash,
        )
        payloads.append(payload)

    return payloads


__all__ = [
    "step1BuildMediaNewsCanonicalPayloads",
    "step2BuildBenchmarkScreeningPayloads",
    "step2BuildKcgsPillarBoostPayloads",
    "step2BuildMediaExternalMaxPayloads",
    "step2BuildRegulationScreeningPayloads",
    "step2ResolveBenchmarkObservation",
]
