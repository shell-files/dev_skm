"""
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/selection
Responsibility:
- Build selection candidates from canonical axis scores (threshold gate)
- Deterministic multi-key sort (MAX axis, MIN axis, survey priority rate, code)
- Recommended Top10 / Top5 cuts
- Governance gate: manual ADD/EXCLUDE allowed, manual SCORE override forbidden
Public functions:
- build_selection_candidates_v13
- sort_selection_candidates_v13
- select_recommended_top_v13
- run_selection_v13
- apply_manual_selection_action_v13
Do not:
- do not let a human edit / override a canonical score (governance != scoring)
- do not mutate the canonical scores during selection
- do not connect to a DB
- do not eval / exec config strings

Threshold / sort strategy / Top-N은 selection_policy.json에 있고, 알고리즘은 여기 Python에 둔다.
Selection은 점수를 바꾸지 않는다. 후보 선정/정렬/거버넌스 게이트만 담당한다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

# Manual selection actions that change *selection*, never the score.
SELECTION_TYPE_AUTO = "AUTO_SELECTED"
SELECTION_TYPE_MANUAL_ADD = "MANUAL_ADD"
SELECTION_TYPE_MANUAL_EXCLUDE = "MANUAL_EXCLUDE"

# Keys that would imply a human is overriding a computed score -> always rejected.
_SCORE_OVERRIDE_KEYS = frozenset(
    {
        "score",
        "finalScore",
        "impactScore",
        "financialScore",
        "overrideScore",
        "scoreOverride",
        "proposedScore",
        "assignedScore",
        "confirmedScore",
        "scoreCandidate",
    }
)


class SelectionGovernanceError(ValueError):
    """Raised when a selection action attempts a forbidden manual score override."""


def _axis_value(item: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in item and item[key] is not None:
            return float(item[key])
    return None


def _max_axis(impact: Optional[float], financial: Optional[float]) -> float:
    candidates = [v for v in (impact, financial) if v is not None]
    return max(candidates) if candidates else 0.0


def _min_axis(impact: Optional[float], financial: Optional[float]) -> float:
    candidates = [v for v in (impact, financial) if v is not None]
    return min(candidates) if candidates else 0.0


def _normalize_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    impact = _axis_value(item, "impactScore", "impact_score", "finalImpactScore", "final_impact_score")
    financial = _axis_value(item, "financialScore", "financial_score", "finalFinancialScore", "final_financial_score")
    survey_rate = _axis_value(item, "surveyPriorityRate", "survey_priority_rate")
    sub_issue_code = item.get("subIssueCode") or item.get("sub_issue_code") or ""
    return {
        "subIssueCode": sub_issue_code,
        "impactScore": impact,
        "financialScore": financial,
        "surveyPriorityRate": survey_rate if survey_rate is not None else 0.0,
        "maxAxis": _max_axis(impact, financial),
        "minAxis": _min_axis(impact, financial),
    }


def build_selection_candidates_v13(
    items: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """
    Keep items where EITHER axis >= candidateThreshold (default 3.0).

    A missing axis does not qualify on its own; the other axis must clear the threshold.
    Returns normalized candidate dicts (the original canonical scores are not mutated).
    """
    threshold = float(policy["candidateThreshold"])
    candidates: List[Dict[str, Any]] = []
    for item in items:
        norm = _normalize_item(item)
        impact = norm["impactScore"]
        financial = norm["financialScore"]
        qualifies = (impact is not None and impact >= threshold) or (
            financial is not None and financial >= threshold
        )
        if qualifies:
            candidates.append(norm)
    return candidates


def sort_selection_candidates_v13(
    candidates: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """
    Deterministic sort per selection_policy.sortStrategy:
      1. MAX(impact, financial)        DESC
      2. MIN(impact, financial)        DESC
      3. surveyPriorityRate            DESC
      4. subIssueCode                  ASC

    A missing axis is treated as 0.0 for sort-key purposes only.
    """
    normalized = [c if "maxAxis" in c else _normalize_item(c) for c in candidates]
    return sorted(
        normalized,
        key=lambda c: (
            -c["maxAxis"],
            -c["minAxis"],
            -c["surveyPriorityRate"],
            c["subIssueCode"],
        ),
    )


def select_recommended_top_v13(
    sorted_candidates: Sequence[Mapping[str, Any]],
    n: int,
) -> List[Dict[str, Any]]:
    """Return the top ``n`` already-sorted candidates."""
    if n < 0:
        raise ValueError("n must be >= 0")
    return [dict(c) for c in sorted_candidates[:n]]


def run_selection_v13(
    items: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Full selection pass: candidates -> sorted -> Top10 / Top5.

    Returns {"candidates", "sorted", "recommendedTop10", "recommendedTop5"}.
    """
    candidates = build_selection_candidates_v13(items, policy)
    ordered = sort_selection_candidates_v13(candidates, policy)
    top10 = select_recommended_top_v13(ordered, int(policy.get("recommendedTop10", 10)))
    top5 = select_recommended_top_v13(ordered, int(policy.get("recommendedTop5", 5)))
    return {
        "candidates": candidates,
        "sorted": ordered,
        "recommendedTop10": top10,
        "recommendedTop5": top5,
    }


def apply_manual_selection_action_v13(
    action: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Apply a manual governance action (ADD / EXCLUDE). A manual SCORE override is forbidden.

    Raises SelectionGovernanceError if:
      - the policy disables manual score override but the action carries a score key, or
      - the action type is not in the allowed manual selection actions.

    Returns a sanitized action dict (subIssueCode, selectionType, selectionReason).
    """
    gate = policy.get("governanceGate", {})
    override_allowed = bool(gate.get("manualScoreOverrideAllowedYn", False))

    offending = sorted(set(action.keys()) & _SCORE_OVERRIDE_KEYS)
    if offending and not override_allowed:
        raise SelectionGovernanceError(
            f"Manual score override is not allowed (offending keys: {offending})"
        )

    allowed_actions = set(
        gate.get("manualSelectionActionsAllowed", [SELECTION_TYPE_MANUAL_ADD, SELECTION_TYPE_MANUAL_EXCLUDE])
    )
    selection_type = action.get("selectionType") or action.get("selection_type")
    if selection_type not in allowed_actions:
        raise SelectionGovernanceError(
            f"selectionType {selection_type!r} is not an allowed manual action {sorted(allowed_actions)}"
        )

    return {
        "subIssueCode": action.get("subIssueCode") or action.get("sub_issue_code"),
        "selectionType": selection_type,
        "selectionReason": action.get("selectionReason") or action.get("selection_reason"),
    }


__all__ = [
    "SELECTION_TYPE_AUTO",
    "SELECTION_TYPE_MANUAL_ADD",
    "SELECTION_TYPE_MANUAL_EXCLUDE",
    "SelectionGovernanceError",
    "build_selection_candidates_v13",
    "sort_selection_candidates_v13",
    "select_recommended_top_v13",
    "run_selection_v13",
    "apply_manual_selection_action_v13",
]
