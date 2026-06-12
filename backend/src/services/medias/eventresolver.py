"""
Pure functions for media_external.news Event Observation → Canonical Factor derivation.
No DB connections, no Runtime Wiring, no repository writes.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Mapping, Optional

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
    normalizedEventType = _normalizeEventType(fact.eventType, policy)
    eventDateBucket = _deriveEventDateBucket(fact)
    impactCandidate = _resolveImpactCandidate(fact, policy, evaluationDate)
    financialCandidate = _resolveFinancialCandidate(fact, policy)
    dedup = _buildDedupTrace(fact)
    status = _calcResolverStatus(impactCandidate, financialCandidate)

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
    """
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
    Same composite mandatory key → MERGED; missing mandatory key → UNRESOLVED;
    eventGroupCandidateId match alone → no merge (advisory only).
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
            for i in indices:
                results[i] = results[i].model_copy(
                    update={
                        "dedup": MediaNewsDedupTraceV13(
                            eventGroupCandidateId=results[i].dedup.eventGroupCandidateId,
                            confirmedEventGroupKey=confirmedKey,
                            dedupStatus="MERGED",
                            ruleTrace=[{"compositeKey": confirmedKey, "mergedCount": len(indices)}],
                        )
                    }
                )

    return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _normalizeEventType(eventType: Optional[str], policy: Mapping[str, Any]) -> Optional[str]:
    if eventType is None:
        return None
    normalization = policy.get("eventTypeNormalization", {})
    aliases = normalization.get("aliases", {})
    if eventType in aliases:
        return aliases[eventType]
    unknownPolicy = normalization.get("unknownPolicy", "PASSTHROUGH")
    return eventType if unknownPolicy == "PASSTHROUGH" else None


def _deriveEventDateBucket(fact: ExtractedFactsV13) -> Optional[str]:
    for raw in (fact.deadlineDate, fact.effectiveDate, fact.eventDate):
        if raw:
            try:
                d = date.fromisoformat(raw[:10])
                return f"{d.year:04d}-{d.month:02d}"
            except Exception:
                continue
    return None


def _applySimpleBand(value: float, bands: List[dict]) -> Optional[float]:
    """Inclusive-inclusive band lookup (integer counts / probability values)."""
    for band in bands:
        lo = band.get("min")
        hi = band.get("max")
        score = band.get("score")
        if lo is not None and value < lo:
            continue
        if hi is not None and value > hi:
            continue
        return float(score)
    return None


def _applyRatioBand(value: float, bands: List[dict]) -> Optional[float]:
    """Band lookup with explicit minInclusive / maxExclusive flags (canonical ratio bands)."""
    for band in bands:
        lo = band.get("min")
        hi = band.get("max")
        minInclusive = band.get("minInclusive", True)
        maxExclusive = band.get("maxExclusive", False)
        score = band.get("score")
        if lo is not None:
            lo_ok = (value >= lo) if minInclusive else (value > lo)
            if not lo_ok:
                continue
        if hi is not None:
            hi_ok = (value < hi) if maxExclusive else (value <= hi)
            if not hi_ok:
                continue
        return float(score)
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
        if diff <= midMaxDays:
            return "mid"
        return "long"
    return None


def _resolveImpactCandidate(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
    evaluationDate: Optional[str],
) -> Optional[MediaNewsResolvedAxisCandidateV13]:
    polarity = fact.impactDirection

    scale: Optional[float] = None
    scaleRules = policy.get("impactScaleRules", {})
    if fact.affectedCount is not None:
        scale = _applySimpleBand(float(fact.affectedCount), scaleRules.get("bands", []))

    likelihood: Optional[float] = None
    likRules = policy.get("impactLikelihoodRules", {})
    if fact.probabilityValue is not None:
        pnorm = _normalizeProbability(fact.probabilityValue)
        likelihood = _applySimpleBand(pnorm, likRules.get("bands", []))

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
) -> Optional[MediaNewsResolvedAxisCandidateV13]:
    polarity = fact.financialIroType

    magnitude: Optional[float] = None
    magRules = policy.get("financialMagnitudeRules", {})
    if fact.ratioValue is not None:
        magnitude = _applyRatioBand(fact.ratioValue, magRules.get("bands", []))

    likelihood: Optional[float] = None
    finLikRules = policy.get("financialLikelihoodRules", {})
    if fact.probabilityValue is not None:
        pnorm = _normalizeProbability(fact.probabilityValue)
        likelihood = _applySimpleBand(pnorm, finLikRules.get("bands", []))

    if polarity is None and magnitude is None and likelihood is None:
        return None

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
    )


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

    has_any_impact = impact is not None and any([
        impact.polarity, impact.scale, impact.likelihood, impact.timeHorizon,
    ])
    has_any_financial = financial is not None and any([
        financial.polarity, financial.magnitude,
    ])
    if has_any_impact or has_any_financial:
        return "PARTIAL"

    return "UNOBSERVED"
