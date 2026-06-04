from __future__ import annotations

from typing import Optional

from src.utils.db import findAll, findOne
from src.utils import onboardingscoperepository as scopeRepo
from src.utils import onboardinginputrepository as inputRepo
from src.utils.onboardingassignmentrepository import listAssignmentRows


CYCLE_TYPE_PRE_DMA_G0 = scopeRepo.CYCLE_TYPE_PRE_DMA_G0
CYCLE_TYPE_POST_DMA_DISCLOSURE = scopeRepo.CYCLE_TYPE_POST_DMA_DISCLOSURE
APPROVAL_POLICY_ROLLUP_READONLY = scopeRepo.APPROVAL_POLICY_ROLLUP_READONLY
APPROVAL_POLICY_NO_APPROVAL_REQUIRED = scopeRepo.APPROVAL_POLICY_NO_APPROVAL_REQUIRED
METRIC_ID_G0_02 = scopeRepo.METRIC_ID_G0_02


def getLatestHistory(companyId: int, reportingYear: int, metricId: str, cycleId: Optional[int] = None) -> dict:
    params = [companyId, reportingYear, metricId]
    cycleFilter = ""
    if cycleId is not None:
        cycleFilter = "AND esg_onboarding_cycle_id = ?"
        params.append(cycleId)
    return findOne(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_APPROVAL_HISTORY
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          {cycleFilter}
          AND delete_yn = 0
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        tuple(params),
    ) or {}


def listCycleApprovalInboxRows(
    companyId: int,
    reportingYear: Optional[int] = None,
    status: Optional[str] = None,
    cycleType: Optional[str] = None,
    assignedOnlyYn: bool = True,
) -> list[dict]:
    normalizedCycleType = str(cycleType or CYCLE_TYPE_PRE_DMA_G0).strip().upper()
    if normalizedCycleType not in {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE}:
        return []

    year = scopeRepo.resolveReportingYear(companyId, reportingYear)
    cycle = scopeRepo.getCycle(companyId, year, normalizedCycleType)
    if not cycle or str(cycle.get("cycle_status") or "").strip().lower() != "active":
        return []

    cycleId = int(cycle["id"])
    scopes = scopeRepo.listMetricScopes(cycleId, companyId)
    if not scopes:
        return []

    metricIds = [row["metric_id"] for row in scopes if row.get("metric_id")]
    masterRows = scopeRepo.listAtomicMaster(metricIds)
    inputRows = listApprovalInputRows(companyId, year, metricIds)
    factRows = listApprovalFactRows(companyId, year, metricIds)
    assignmentRows = listAssignmentRows(cycleId, companyId)
    historyRows = listLatestApprovalHistories(companyId, year, metricIds, cycleId)

    masterByMetric = inputRepo.groupRows(masterRows, "metric_id")
    inputByMetric = inputRepo.groupRows(inputRows, "metric_id")
    factByMetric = inputRepo.groupRows(factRows, "metric_id")
    assignmentByMetric = {row.get("metric_id"): row for row in assignmentRows}
    historyByMetric = {row.get("metric_id"): row for row in historyRows}
    statusFilter = str(status or "").strip().upper()

    items = []
    for scope in scopes:
        metricId = scope.get("metric_id")
        if not metricId:
            continue

        metricInputRows = inputByMetric.get(metricId, [])
        metricFactRows = factByMetric.get(metricId, [])
        assignment = assignmentByMetric.get(metricId) or {}
        latestHistory = historyByMetric.get(metricId) or {}

        if assignedOnlyYn and not assignment and not metricInputRows and not latestHistory:
            continue

        requiredAtomicIds = [
            row["atomic_metric_id"]
            for row in masterByMetric.get(metricId, [])
            if row.get("atomic_metric_id") and inputRepo.truthy(row.get("onboarding_input_yn"))
        ]
        requiredAtomicSet = set(requiredAtomicIds)
        completedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet and inputRepo.hasMetricValue(row)
        }
        completedAtomicIds.update(
            row.get("atomic_metric_id")
            for row in metricFactRows
            if row.get("atomic_metric_id") in requiredAtomicSet and inputRepo.hasMetricValue(row)
        )
        submittedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet
            and inputRepo.hasMetricValue(row)
            and str(row.get("input_status") or "").strip().lower() in {"submitted", "reviewed", "approved"}
        }
        approvedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricFactRows
            if row.get("atomic_metric_id") in requiredAtomicSet and inputRepo.hasMetricValue(row)
        }
        approvedAtomicIds.update(
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet
            and inputRepo.hasMetricValue(row)
            and str(row.get("input_status") or "").strip().lower() == "approved"
        )

        approvalStatus = resolveCycleApprovalStatus(
            requiredAtomicCount=len(requiredAtomicSet),
            completedAtomicCount=len(completedAtomicIds),
            submittedAtomicCount=len(submittedAtomicIds),
            approvedAtomicCount=len(approvedAtomicIds),
            inputRows=metricInputRows,
            latestHistory=latestHistory,
        )
        if statusFilter and approvalStatus != statusFilter:
            continue

        actionSupportedYn, disabledReason = resolveActionSupport(scope)
        items.append(
            {
                "companyId": companyId,
                "reportingYear": year,
                "metricId": metricId,
                "metricName": scope.get("metric_name_kr") or inputRepo.getMetricName(metricId),
                "cycleType": cycle.get("cycle_type") or CYCLE_TYPE_PRE_DMA_G0,
                "issueDomain": inputRepo.normalizeIssueDomain(scope.get("sub_issue_domain")) or "general",
                "issueGroup": scope.get("issue_group") or None,
                "subIssueId": int(scope["sub_issue_id"]) if scope.get("sub_issue_id") is not None else None,
                "subIssueCode": scope.get("sub_issue_code"),
                "subIssueName": scope.get("sub_issue_name"),
                "approvalStatus": approvalStatus,
                "inputUserId": inputRepo.firstNonNull([row.get("input_user_id") for row in metricInputRows]),
                "assigneeUserId": assignment.get("assignee_user_id"),
                "cycleId": cycleId,
                "assignmentId": int(assignment["assignment_id"]) if assignment.get("assignment_id") is not None else None,
                "requiredAtomicCount": len(requiredAtomicSet),
                "completedAtomicCount": len(completedAtomicIds),
                "submittedAtomicCount": len(submittedAtomicIds),
                "approvedAtomicCount": len(approvedAtomicIds),
                "missingAtomicMetricIds": [
                    atomicId for atomicId in requiredAtomicIds if atomicId not in completedAtomicIds
                ],
                "submittedAt": inputRepo.formatDatetime(inputRepo.submittedAt(metricInputRows, latestHistory)),
                "approvedAt": inputRepo.formatDatetime(inputRepo.approvedAt(metricInputRows, metricFactRows, latestHistory)),
                "commentText": latestHistory.get("comment_text"),
                "selfSubmittedYn": False,
                "actionSupportedYn": actionSupportedYn,
                "actionDisabledReason": disabledReason,
            }
        )
    return items


def resolveActionSupport(scope: dict) -> tuple[bool, Optional[str]]:
    if inputRepo.truthy(scope.get("rollup_readonly_yn")):
        return False, "ROLLUP_READONLY scope cannot be manually approved."
    policy = str(scope.get("approval_policy_code") or "").strip().upper()
    if policy == APPROVAL_POLICY_ROLLUP_READONLY:
        return False, "ROLLUP_READONLY policy cannot be manually approved."
    if policy == APPROVAL_POLICY_NO_APPROVAL_REQUIRED:
        return False, "Approval is not required for this metric."
    if not inputRepo.truthy(scope.get("approval_required_yn")):
        return False, "Approval is not required for this scope."
    return True, None


def listApprovalInputRows(companyId: int, reportingYear: int, metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    return findAll(
        f"""
        SELECT
            metric_id,
            atomic_metric_id,
            value_text,
            value_numeric,
            unit,
            input_status,
            input_user_id,
            approved_at,
            updated_at
        FROM ESG_ONBOARDING_INPUT_VALUE
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id IN ({placeholders})
          AND delete_yn = 0
        ORDER BY metric_id, atomic_metric_id
        """,
        (companyId, reportingYear, *metricIds),
    ) or []


def listApprovalFactRows(companyId: int, reportingYear: int, metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    return findAll(
        f"""
        SELECT
            metric_id,
            atomic_metric_id,
            value_text,
            value_numeric,
            unit,
            approval_status AS input_status,
            approved_at,
            updated_at
        FROM ESG_KPI_FACT
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id IN ({placeholders})
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY metric_id, atomic_metric_id
        """,
        (companyId, reportingYear, *metricIds),
    ) or []


def listLatestApprovalHistories(
    companyId: int,
    reportingYear: int,
    metricIds: list[str],
    cycleId: Optional[int] = None,
) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    params = [companyId, reportingYear, *metricIds]
    cycleFilter = ""
    if cycleId is not None:
        cycleFilter = "AND esg_onboarding_cycle_id = ?"
        params.append(cycleId)
    return findAll(
        f"""
        SELECT h.*
        FROM ESG_ONBOARDING_APPROVAL_HISTORY h
        JOIN (
            SELECT metric_id, MAX(id) AS latest_id
            FROM ESG_ONBOARDING_APPROVAL_HISTORY
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id IN ({placeholders})
              {cycleFilter}
              AND delete_yn = 0
            GROUP BY metric_id
        ) latest
          ON latest.latest_id = h.id
        ORDER BY h.metric_id
        """,
        tuple(params),
    ) or []


def resolveCycleApprovalStatus(
    *,
    requiredAtomicCount: int,
    completedAtomicCount: int,
    submittedAtomicCount: int,
    approvedAtomicCount: int,
    inputRows: list[dict],
    latestHistory: dict,
) -> str:
    if requiredAtomicCount > 0 and approvedAtomicCount >= requiredAtomicCount:
        return "APPROVED"
    latestStatus = str(latestHistory.get("action_status") or "").strip().lower()
    inputStatuses = {str(row.get("input_status") or "").strip().lower() for row in inputRows}
    if latestStatus == "rejected" or "rejected" in inputStatuses:
        return "REJECTED"
    if latestStatus == "reviewed" or "reviewed" in inputStatuses:
        return "REVIEWED"
    if completedAtomicCount > 0 and submittedAtomicCount >= completedAtomicCount:
        return "SUBMITTED"
    if completedAtomicCount > 0:
        return "DRAFT"
    return "NOT_STARTED"


def listApprovalSummaries(
    companyId: int,
    reportingYear: Optional[int] = None,
    status: Optional[str] = None,
    cycleType: Optional[str] = None,
) -> list[dict]:
    rows = listCycleApprovalInboxRows(companyId, reportingYear, status, cycleType, assignedOnlyYn=False)
    return rows


def buildApprovalSummary(
    companyId: int,
    reportingYear: int,
    metricId: str,
    cycleType: str = CYCLE_TYPE_PRE_DMA_G0,
) -> dict:
    cycle = scopeRepo.getCycle(companyId, reportingYear, cycleType) or {}
    cycleId = int(cycle["id"]) if cycle.get("id") is not None else None
    scopes = scopeRepo.listMetricScopes(cycleId, companyId, metricId) if cycleId is not None else []
    scope = scopes[0] if scopes else {}
    requiredAtomicIds = inputRepo.listRequiredAtomicIds(metricId)
    requiredAtomicSet = set(requiredAtomicIds)
    inputs = inputRepo.listMetricInputs(companyId, reportingYear, metricId)
    facts = inputRepo.listMetricKpiFacts(companyId, reportingYear, metricId)
    approvalPolicyCode = str(scope.get("approval_policy_code") or scopeRepo.APPROVAL_POLICY_INPUT_APPROVAL_ONLY).strip().upper()
    promotedQuantAtomicIds = (
        inputRepo.listQuantInputAtomicIds(metricId)
        if approvalPolicyCode in {
            scopeRepo.APPROVAL_POLICY_PROMOTE_TO_KPI_FACT,
            scopeRepo.APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP,
        }
        else []
    )
    promotedQuantAtomicSet = set(promotedQuantAtomicIds)
    assignment = {}
    if cycleId is not None:
        assignment = findOne(
            """
            SELECT *
            FROM ESG_METRIC_ASSIGNMENT
            WHERE esg_onboarding_cycle_id = ?
              AND company_id = ?
              AND metric_id = ?
              AND delete_yn = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (cycleId, companyId, metricId),
        ) or {}
    latestHistory = getLatestHistory(companyId, reportingYear, metricId, cycleId)
    approvedFactAtomicIds = {row["atomic_metric_id"] for row in facts}
    approvedAtomicIds = set(approvedFactAtomicIds)
    inputByAtomic = {row["atomic_metric_id"]: row for row in inputs}
    completedAtomicIds = {
        atomicId
        for atomicId, row in inputByAtomic.items()
        if atomicId in requiredAtomicSet and inputRepo.hasMetricValue(row)
    }
    submittedAtomicIds = {
        atomicId
        for atomicId, row in inputByAtomic.items()
        if atomicId in requiredAtomicSet
        and str(row.get("input_status") or "").lower() in {"submitted", "reviewed", "approved"}
        and inputRepo.hasMetricValue(row)
    }
    approvedAtomicIds.update(
        atomicId
        for atomicId, row in inputByAtomic.items()
        if atomicId in requiredAtomicSet
        and str(row.get("input_status") or "").lower() == "approved"
        and inputRepo.hasMetricValue(row)
    )
    missingAtomicIds = [
        atomicId
        for atomicId in requiredAtomicIds
        if atomicId not in completedAtomicIds
    ]
    actionSupportedYn, disabledReason = resolveActionSupport(scope) if scope else (False, "Metric is not in active cycle scope.")
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "metricId": metricId,
        "metricName": scope.get("metric_name_kr") or inputRepo.getMetricName(metricId),
        "cycleType": cycle.get("cycle_type") or cycleType,
        "issueDomain": inputRepo.normalizeIssueDomain(scope.get("sub_issue_domain")) or "general",
        "issueGroup": scope.get("issue_group") or None,
        "subIssueId": int(scope["sub_issue_id"]) if scope.get("sub_issue_id") is not None else None,
        "subIssueCode": scope.get("sub_issue_code"),
        "subIssueName": scope.get("sub_issue_name"),
        "approvalStatus": inputRepo.resolveApprovalStatus(inputs, facts, requiredAtomicIds),
        "approvalPolicyCode": approvalPolicyCode,
        "rollupReadonlyYn": inputRepo.truthy(scope.get("rollup_readonly_yn")),
        "promotedQuantAtomicCount": len(promotedQuantAtomicSet),
        "approvedPromotedFactCount": len(approvedFactAtomicIds.intersection(promotedQuantAtomicSet)),
        "inputUserId": inputRepo.firstNonNull([row.get("input_user_id") for row in inputs]),
        "assigneeUserId": assignment.get("assignee_user_id"),
        "cycleId": cycleId,
        "assignmentId": int(assignment["id"]) if assignment.get("id") is not None else None,
        "requiredAtomicCount": len(requiredAtomicIds),
        "completedAtomicCount": len(completedAtomicIds),
        "submittedAtomicCount": len(submittedAtomicIds),
        "approvedAtomicCount": len(approvedAtomicIds),
        "missingAtomicMetricIds": missingAtomicIds,
        "submittedAt": inputRepo.formatDatetime(inputRepo.submittedAt(inputs, latestHistory)),
        "approvedAt": inputRepo.formatDatetime(inputRepo.approvedAt(inputs, facts, latestHistory)),
        "commentText": latestHistory.get("comment_text"),
        "selfSubmittedYn": False,
        "actionSupportedYn": actionSupportedYn,
        "actionDisabledReason": disabledReason,
    }


def insertHistory(
    cur,
    cycleId: int,
    assignmentId: Optional[int],
    companyId: int,
    reportingYear: int,
    metricId: str,
    actionType: str,
    actionStatus: str,
    actorUserId: Optional[int],
    assigneeUserId: Optional[int],
    commentText: Optional[str],
) -> None:
    cur.execute(
        """
        INSERT INTO ESG_ONBOARDING_APPROVAL_HISTORY (
            esg_onboarding_cycle_id,
            esg_metric_assignment_id,
            company_id,
            reporting_year,
            metric_id,
            atomic_metric_id,
            action_type,
            action_status,
            actor_user_id,
            assignee_user_id,
            comment_text
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
        """,
        (
            cycleId,
            assignmentId,
            companyId,
            reportingYear,
            metricId,
            actionType,
            actionStatus,
            actorUserId,
            assigneeUserId,
            commentText,
        ),
    )


def submitG002Approval(companyId: int, reportingYear: int, reportBasisType=None, sourceMaterialityRunId=None, actorUserId=None) -> dict:
    from src.services.onboardings.approval_service import submitMetricApproval

    return submitMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=None,
        reportBasisType=reportBasisType,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )


def approveG002Approval(companyId: int, reportingYear: int, actorUserId: Optional[int], commentText: Optional[str] = None) -> dict:
    from src.services.onboardings.approval_service import approveMetricApproval

    return approveMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=commentText,
    )


def rejectG002Approval(companyId: int, reportingYear: int, actorUserId: Optional[int], commentText: str) -> dict:
    from src.services.onboardings.approval_service import rejectMetricApproval

    return rejectMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=commentText,
    )

__all__ = [
    "CYCLE_TYPE_PRE_DMA_G0",
    "CYCLE_TYPE_POST_DMA_DISCLOSURE",
    "APPROVAL_POLICY_ROLLUP_READONLY",
    "APPROVAL_POLICY_NO_APPROVAL_REQUIRED",
    "METRIC_ID_G0_02",
    "getLatestHistory",
    "listCycleApprovalInboxRows",
    "resolveActionSupport",
    "listApprovalInputRows",
    "listApprovalFactRows",
    "listLatestApprovalHistories",
    "resolveCycleApprovalStatus",
    "listApprovalSummaries",
    "buildApprovalSummary",
    "insertHistory",
    "submitG002Approval",
    "approveG002Approval",
    "rejectG002Approval",
]
