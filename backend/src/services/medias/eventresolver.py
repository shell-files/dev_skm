"""
eventresolver.py
레이어: Service (medias)
역할: 미디어 뉴스 이벤트 관찰 → Canonical Factor 도출 순수 함수 모음 (DB/Redis 없음).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Mapping, Optional, Tuple

from src.models.dmaengine import (
    AxisScoreTraceV13,
    ExtractedFactsV13,
    MediaNewsDedupTraceV13,
    MediaNewsEventResolutionTraceV13,
    MediaNewsResolvedAxisCandidateV13,
    TriState,
)
from src.utils.dmascoring import step1CalcAxes


def resolveMediaNewsEventObservation(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
    *,
    evaluationDate: Optional[str] = None,
) -> MediaNewsEventResolutionTraceV13:
    """
    Maps raw AI-extracted facts → resolver-level axis candidates.
    Pure function: no DB, no registry IO, no side effects.
    """
    dedupRules = policy.get("eventDedupRules", {})
    normalizedEventType = _normalizeEventType(fact.eventType, policy)
    eventDateBucket = _deriveEventDateBucket(fact, dedupRules)
    impactCandidate = _resolveImpactCandidate(fact, policy, evaluationDate)
    financialCandidate, ratioRejected = _resolveFinancialCandidate(fact, policy)
    dedup = _buildDedupTrace(fact)

    status: Literal["RESOLVED", "PARTIAL", "UNOBSERVED", "CONFLICTED", "REJECTED"] = (
        "REJECTED" if ratioRejected
        else _calcResolverStatus(impactCandidate, financialCandidate)
    )

    return MediaNewsEventResolutionTraceV13(
        resolverStatus=status,
        subIssueCode=fact.subIssueCode or "",
        normalizedEventType=normalizedEventType,
        eventDateBucket=eventDateBucket,
        impact=impactCandidate,
        financial=financialCandidate,
        dedup=dedup,
    )


def resolveMediaNewsCanonicalFactors(
    resolution: MediaNewsEventResolutionTraceV13,
    canonicalPolicy: Mapping[str, Any],
) -> Dict[str, Optional[AxisScoreTraceV13]]:
    """
    MediaNewsEventResolutionTraceV13 → step1CalcAxes() → AxisScoreTraceV13 dict.
    Reuses Canonical Core; does not reimplement scoring math.
    REJECTED / CONFLICTED resolution → both axes None (no Canonical calculation).
    """
    if (
        resolution.resolverStatus in ("REJECTED", "CONFLICTED")
        or resolution.dedup.dedupStatus == "CONFLICTED"
    ):
        return {"impact": None, "financial": None}

    impact_input: Optional[Dict[str, Any]] = None
    financial_input: Optional[Dict[str, Any]] = None

    if resolution.impact is not None and resolution.impact.polarity in ("negative", "positive"):
        impact_input = {
            "impactDirection": resolution.impact.polarity,
            "scale": resolution.impact.scale,
            "likelihood": resolution.impact.likelihood,
            "scope": resolution.impact.scope,
            "irremediability": resolution.impact.irremediability,
            "timeHorizon": resolution.impact.timeHorizon,
            "explicitNoUrgency": resolution.impact.explicitNoUrgencyYn is TriState.TRUE,
        }

    if resolution.financial is not None and resolution.financial.polarity in ("risk", "opportunity"):
        financial_input = {
            "financialIroType": resolution.financial.polarity,
            "magnitude": resolution.financial.magnitude,
            "likelihood": resolution.financial.likelihood,
            "timeHorizon": resolution.financial.timeHorizon,
            "explicitNoUrgency": resolution.financial.explicitNoUrgencyYn is TriState.TRUE,
        }

    return step1CalcAxes(
        policy=canonicalPolicy,
        impact=impact_input,
        financial=financial_input,
    )


def resolveMediaNewsEventGroup(
    resolutions: List[MediaNewsEventResolutionTraceV13],
    policy: Mapping[str, Any],
) -> List[MediaNewsEventResolutionTraceV13]:
    """
    Applies Event Dedup across a list of resolutions.

    Rule:
      A. mandatory key missing            → UNRESOLVED
      B. composite key unique (1 match)   → UNIQUE
      C. composite key duplicated
         AND all eventGroupCandidateIds non-null AND same → MERGED
      D. composite key duplicated
         BUT candidateId missing or different            → CONFLICTED

    eventGroupCandidateId alone → no merge (advisory only).
    """
    dedupRules = policy.get("eventDedupRules", {})
    mandatoryKeys: List[str] = dedupRules.get("mandatoryKeys", [])

    def _compositeKey(r: MediaNewsEventResolutionTraceV13) -> Optional[tuple]:
        parts = []
        for k in mandatoryKeys:
            if k == "subIssueCode":
                v = r.subIssueCode or None
            elif k == "normalizedEventType":
                v = r.normalizedEventType
            elif k == "eventDateBucket":
                v = r.eventDateBucket
            else:
                v = None
            if v is None:
                return None
            parts.append(v)
        return tuple(parts)

    key_to_indices: Dict[Any, List[int]] = {}
    unresolved_indices: List[int] = []

    for i, r in enumerate(resolutions):
        ck = _compositeKey(r)
        if ck is None:
            unresolved_indices.append(i)
        else:
            key_to_indices.setdefault(ck, []).append(i)

    results: List[MediaNewsEventResolutionTraceV13] = list(resolutions)

    for i in unresolved_indices:
        results[i] = results[i].model_copy(
            update={
                "dedup": MediaNewsDedupTraceV13(
                    eventGroupCandidateId=results[i].dedup.eventGroupCandidateId,
                    confirmedEventGroupKey=None,
                    dedupStatus="UNRESOLVED",
                    ruleTrace=[{"reason": "mandatory_key_missing"}],
                )
            }
        )

    for ck, indices in key_to_indices.items():
        confirmedKey = "|".join(str(v) for v in ck)
        if len(indices) == 1:
            i = indices[0]
            results[i] = results[i].model_copy(
                update={
                    "dedup": MediaNewsDedupTraceV13(
                        eventGroupCandidateId=results[i].dedup.eventGroupCandidateId,
                        confirmedEventGroupKey=confirmedKey,
                        dedupStatus="UNIQUE",
                        ruleTrace=[{"compositeKey": confirmedKey}],
                    )
                }
            )
        else:
            candidate_ids = [results[i].dedup.eventGroupCandidateId for i in indices]
            all_non_null = all(cid is not None for cid in candidate_ids)
            all_same = len(set(candidate_ids)) == 1
            dedup_status: Literal["MERGED", "CONFLICTED"] = (
                "MERGED" if (all_non_null and all_same) else "CONFLICTED"
            )
            for i in indices:
                if dedup_status == "MERGED":
                    new_dedup = MediaNewsDedupTraceV13(
                        eventGroupCandidateId=results[i].dedup.eventGroupCandidateId,
                        confirmedEventGroupKey=confirmedKey,
                        dedupStatus="MERGED",
                        ruleTrace=[{
                            "compositeKey": confirmedKey,
                            "groupCount": len(indices),
                            "mergePolicy": "COMPOSITE_PLUS_MATCHING_ADVISORY_HINT",
                        }],
                    )
                else:
                    new_dedup = MediaNewsDedupTraceV13(
                        eventGroupCandidateId=results[i].dedup.eventGroupCandidateId,
                        confirmedEventGroupKey=None,
                        dedupStatus="CONFLICTED",
                        ruleTrace=[{
                            "candidateCompositeKey": confirmedKey,
                            "groupCount": len(indices),
                            "mergePolicy": "COMPOSITE_PLUS_MATCHING_ADVISORY_HINT",
                            "reason": "candidate_hint_missing_or_conflicted",
                        }],
                    )
                results[i] = results[i].model_copy(
                    update={
                        "resolverStatus": (
                            "CONFLICTED"
                            if dedup_status == "CONFLICTED"
                            else results[i].resolverStatus
                        ),
                        "dedup": new_dedup,
                    }
                )

    return results



def _normalizeEventType(eventType: Optional[str], policy: Mapping[str, Any]) -> Optional[str]:
    if eventType is None:
        return None
    normalization = policy.get("eventTypeNormalization", {})
    aliases = normalization.get("aliases", {})
    if eventType in aliases:
        return aliases[eventType]
    return eventType if normalization.get("unknownPolicy", "PASSTHROUGH") == "PASSTHROUGH" else None


def _deriveEventDateBucket(fact: ExtractedFactsV13, dedupRules: Mapping[str, Any]) -> Optional[str]:
    priority: List[str] = dedupRules.get("dateBucketSourcePriority", ["eventDate", "effectiveDate", "deadlineDate"])
    precision: str = dedupRules.get("dateBucketPrecision", "DAY")
    for field_name in priority:
        raw = getattr(fact, field_name, None)
        if raw:
            try:
                d = date.fromisoformat(raw[:10])
                return d.isoformat() if precision == "DAY" else f"{d.year:04d}-{d.month:02d}"
            except Exception:
                continue
    return None


def _applyBand(value: float, bands: List[dict]) -> Optional[float]:
    """Unified band lookup with explicit minInclusive / maxExclusive flags."""
    for band in bands:
        lo = band.get("min")
        hi = band.get("max")
        min_inc: bool = band.get("minInclusive", True)
        max_exc: bool = band.get("maxExclusive", False)
        if lo is not None:
            if not (value >= lo if min_inc else value > lo):
                continue
        if hi is not None:
            if not (value < hi if max_exc else value <= hi):
                continue
        return float(band["score"])
    return None


def _normalizeProbability(raw: float) -> float:
    return raw / 100.0 if raw > 1.0 else raw


def _resolveTimeHorizon(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
    evaluationDate: Optional[str],
) -> Optional[str]:
    if evaluationDate is None:
        return None
    thRules = policy.get("timeHorizonRules", {})
    sourcePriority: List[str] = thRules.get("sourcePriority", ["deadlineDate", "effectiveDate", "eventDate"])
    shortMaxDays: int = thRules.get("shortMaxDays", 365)
    midMaxDays: int = thRules.get("midMaxDays", 1095)
    try:
        evalDate = date.fromisoformat(evaluationDate[:10])
    except Exception:
        return None
    for field_name in sourcePriority:
        raw = getattr(fact, field_name, None)
        if not raw:
            continue
        try:
            target = date.fromisoformat(raw[:10])
        except Exception:
            continue
        diff = (target - evalDate).days
        if diff <= shortMaxDays:
            return "short"
        return "mid" if diff <= midMaxDays else "long"
    return None


def _resolveImpactCandidate(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
    evaluationDate: Optional[str],
) -> Optional[MediaNewsResolvedAxisCandidateV13]:
    polarity = fact.impactDirection

    scale: Optional[float] = None
    if fact.affectedCount is not None:
        scale = _applyBand(float(fact.affectedCount), policy.get("impactScaleRules", {}).get("bands", []))

    likelihood: Optional[float] = None
    if fact.probabilityValue is not None:
        pnorm = _normalizeProbability(fact.probabilityValue)
        likelihood = _applyBand(pnorm, policy.get("impactLikelihoodRules", {}).get("bands", []))

    timeHorizon = _resolveTimeHorizon(fact, policy, evaluationDate)
    explicitNoUrgency = fact.explicitNoUrgencyYn

    if polarity is None and scale is None and likelihood is None and timeHorizon is None and explicitNoUrgency is None:
        return None

    ruleTrace: List[Dict[str, Any]] = []
    if scale is not None:
        ruleTrace.append({"factor": "scale", "source": "affectedCount", "rawValue": fact.affectedCount, "score": scale})
    if likelihood is not None:
        ruleTrace.append({"factor": "likelihood", "source": "probabilityValue", "rawValue": fact.probabilityValue, "score": likelihood})
    if timeHorizon is not None:
        ruleTrace.append({"factor": "timeHorizon", "value": timeHorizon})

    return MediaNewsResolvedAxisCandidateV13(
        polarity=polarity,
        scale=scale,
        scope=None,
        likelihood=likelihood,
        irremediability=None,
        magnitude=None,
        timeHorizon=timeHorizon,
        explicitNoUrgencyYn=explicitNoUrgency,
        ruleTrace=ruleTrace,
    )


def _resolveFinancialCandidate(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
) -> Tuple[Optional[MediaNewsResolvedAxisCandidateV13], bool]:
    """Returns (candidate, ratio_rejected). ratio_rejected=True → resolverStatus REJECTED."""
    polarity = fact.financialIroType
    magnitude: Optional[float] = None

    if fact.ratioValue is not None:
        contract = policy.get("ratioValueContract", {})
        min_val: float = contract.get("min", 0.0)
        max_val: float = contract.get("max", 1.0)
        if fact.ratioValue < min_val or fact.ratioValue > max_val:
            return MediaNewsResolvedAxisCandidateV13(
                polarity=polarity,
                ruleTrace=[{
                    "factor": "magnitude",
                    "reason": "RATIO_VALUE_OUT_OF_RANGE",
                    "rawValue": fact.ratioValue,
                    "outOfRangePolicy": contract.get("outOfRangePolicy", "REJECTED"),
                }],
            ), True
        magnitude = _applyBand(fact.ratioValue, policy.get("financialMagnitudeRules", {}).get("bands", []))

    likelihood: Optional[float] = None
    if fact.probabilityValue is not None:
        pnorm = _normalizeProbability(fact.probabilityValue)
        likelihood = _applyBand(pnorm, policy.get("financialLikelihoodRules", {}).get("bands", []))

    if polarity is None and magnitude is None and likelihood is None:
        return None, False

    ruleTrace: List[Dict[str, Any]] = []
    if magnitude is not None:
        ruleTrace.append({"factor": "magnitude", "source": "ratioValue", "rawValue": fact.ratioValue, "score": magnitude})
    if likelihood is not None:
        ruleTrace.append({"factor": "likelihood", "source": "probabilityValue", "rawValue": fact.probabilityValue, "score": likelihood})

    return MediaNewsResolvedAxisCandidateV13(
        polarity=polarity,
        scale=None,
        scope=None,
        likelihood=likelihood,
        irremediability=None,
        magnitude=magnitude,
        timeHorizon=None,
        explicitNoUrgencyYn=None,
        ruleTrace=ruleTrace,
    ), False


def _buildDedupTrace(fact: ExtractedFactsV13) -> MediaNewsDedupTraceV13:
    if fact.eventGroupCandidateId:
        return MediaNewsDedupTraceV13(
            eventGroupCandidateId=fact.eventGroupCandidateId,
            confirmedEventGroupKey=None,
            dedupStatus="UNRESOLVED",
            ruleTrace=[{"source": "eventGroupCandidateId", "policy": "ADVISORY_ONLY"}],
        )
    return MediaNewsDedupTraceV13(
        eventGroupCandidateId=None,
        confirmedEventGroupKey=None,
        dedupStatus="UNRESOLVED",
        ruleTrace=[],
    )


def _calcResolverStatus(
    impact: Optional[MediaNewsResolvedAxisCandidateV13],
    financial: Optional[MediaNewsResolvedAxisCandidateV13],
) -> Literal["RESOLVED", "PARTIAL", "UNOBSERVED", "CONFLICTED", "REJECTED"]:
    has_full_impact = (
        impact is not None
        and impact.polarity in ("negative", "positive")
        and impact.scale is not None
        and impact.likelihood is not None
    )
    has_full_financial = (
        financial is not None
        and financial.polarity in ("risk", "opportunity")
        and financial.magnitude is not None
    )
    if has_full_impact or has_full_financial:
        return "RESOLVED"

    has_any_impact = impact is not None and any([impact.polarity, impact.scale, impact.likelihood, impact.timeHorizon])
    has_any_financial = financial is not None and any([financial.polarity, financial.magnitude])
    if has_any_impact or has_any_financial:
        return "PARTIAL"

    return "UNOBSERVED"
