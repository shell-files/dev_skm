"""
service.py
레이어: Service (onboardings)
역할: 온보딩 지표 조회·입력·저장 서비스 — 사이클별 지표 목록 및 입력값 관리.
"""
from __future__ import annotations

from typing import Optional

from src.models.onboarding import (
    OnboardingAssignmentDto,
    OnboardingAtomicItemDto,
    OnboardingMetricItemDto,
    OnboardingMetricsResponseDto,
    OnboardingMetricValuesRequestDto,
    OnboardingMetricValuesResponseDto,
)
from src.repositories import onboardingassignmentrepository as assignmentRepo
from src.repositories import onboardingrepository as repo
from src.repositories import onboardingscoperepository as scopeRepo
from src.utils.companyscope import checkScope
from src.utils.typeutils import normalizeIssueDomain, groupRows, maskEmail
from src.services.calculations.service import invalidateAffectedEntityFactsTx


CYCLE_TYPE_PRE_DMA_G0 = repo.CYCLE_TYPE_PRE_DMA_G0
CYCLE_TYPE_POST_DMA_DISCLOSURE = repo.CYCLE_TYPE_POST_DMA_DISCLOSURE
CYCLE_TYPE_ROLLUP_RESPONSE = repo.CYCLE_TYPE_ROLLUP_RESPONSE

CYCLE_TYPE_LABELS = {
    "PRE_DMA_G0": "경영일반 지표",
    "POST_DMA_DISCLOSURE": "중대성 이슈 지표",
    "ROLLUP_RESPONSE": "지주사 요청 대응 데이터",
}
PRE_DMA_G0_CYCLE_NOT_READY = "보고연도 프로젝트를 먼저 시작해 주세요."
PRE_DMA_G0_SCOPE_NOT_READY = "온보딩 지표 범위가 초기화되지 않았습니다. 기존 프로젝트를 재개해 주세요."
POST_DMA_DISCLOSURE_CYCLE_NOT_READY = "생성된 프로젝트를 먼저 초기화해 주세요."
POST_DMA_DISCLOSURE_SCOPE_NOT_READY = "공시범위가 초기화되지 않았습니다."
STRUCTURED_LOOKUP_IDS = {"G0-05__QL0002", "G0-06__QL0001"}
EDITABLE_INPUT_MODES = {"MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE", "STRUCTURED_LOOKUP"}
SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
SUPPORTED_INPUT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE, CYCLE_TYPE_ROLLUP_RESPONSE}
SUPPORTED_ASSIGNMENT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE, CYCLE_TYPE_ROLLUP_RESPONSE}
ASSIGNMENT_MANAGER_ROLES = {"ADMIN", "ESG"}
ASSIGNMENT_MANAGER_ROLE_NAMES = {"관리자", "ESG담당자", "ESG 담당자"}
EMPLOYEE_ROLES = {"EMPLOYEE", "ASSIGNEE"}
EMPLOYEE_ROLE_NAMES = {"부서담당자", "부서 담당자"}
CONSULTANT_ROLES = {"CONSULTANT"}
CONSULTANT_ROLE_NAMES = {"컨설턴트"}
REVIEWER_ROLES = {"CONSULTANT", "ADMIN", "ESG"}
REVIEWER_ROLE_NAMES = {"컨설턴트", "관리자", "ESG담당자", "ESG 담당자"}
PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE = "기존 프로젝트를 먼저 시작해 주세요."
APPROVER_ROLES = {"ADMIN", "ESG"}
APPROVER_ROLE_NAMES = {"관리자", "ESG담당자", "ESG 담당자"}


def listMetrics(
    *,
    companyId: int,
    reportingYear: Optional[int],
    cycleType: str,
    metricId: Optional[str] = None,
    batchId: Optional[int] = None,
    userModel=None,
) -> OnboardingMetricsResponseDto:
    year = repo.resolveReportingYear(companyId, reportingYear)
    sourceMaterialityRunId = resolveCycleSourceMaterialityRunId(companyId, year, cycleType)
    if cycleType == repo.CYCLE_TYPE_ROLLUP_RESPONSE and batchId:
        cycle = requireCycle(companyId, year, cycleType, batchId=batchId)
    else:
        cycle = requireCycle(
            companyId,
            year,
            cycleType,
            sourceMaterialityRunId=sourceMaterialityRunId,
        )
    allScopes = repo.listMetricScopes(int(cycle["id"]), companyId)
    if not allScopes:
        raise ValueError(scopeNotReadyMessage(cycle.get("cycle_type") or cycleType))
    assignmentRows = assignmentRepo.listAssignmentRows(int(cycle["id"]), companyId)
    scopes, status, message = listVisibleMetricScopesForUser(allScopes, assignmentRows, userModel)
    if status == False:
        return OnboardingMetricsResponseDto(
            companyId=companyId,
            reportingYear=year,
            cycleId=0,
            cycleType="",
            items=[],
            status=status,
            message=message
        )
    if metricId:
        scopes = [row for row in allScopes if row.get("metric_id") == metricId]
        scopes, status, message = listVisibleMetricScopesForUser(scopes, assignmentRows, userModel)
        if not scopes:
            raise ValueError(f"Unsupported metricId for cycle scope: {metricId}")
    metricIds = [row["metric_id"] for row in scopes]
    masterRows = repo.listAtomicMaster(metricIds)
    actualCycleType = str(cycle.get("cycle_type") or cycleType).strip().upper()
    
    if actualCycleType == repo.CYCLE_TYPE_ROLLUP_RESPONSE and batchId:
        from src.repositories import rolluprepository as rollupRepo
        snapshotAtomicIds = set(rollupRepo.resolveExternalEntitySourceAtomicIds(int(batchId)))
        masterRows = [row for row in masterRows if row.get("atomic_metric_id") in snapshotAtomicIds]

    valueRows = repo.listValueRows(
        companyId, 
        year, 
        metricIds,
        includeGroupRollupResultYn=(actualCycleType != repo.CYCLE_TYPE_ROLLUP_RESPONSE),
    )
    assignmentByMetric = {row["metric_id"]: buildAssignment(row) for row in assignmentRows}
    atomicRowsByMetric = groupRows(masterRows, "metric_id")

    from src.repositories.onboardingapprovalrepository import listCycleApprovalInboxRows
    approvalSummaries = listCycleApprovalInboxRows(
        companyId=companyId,
        reportingYear=year,
        cycleType=actualCycleType,
        assignedOnlyYn=False,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    approvalByMetric = {row["metricId"]: row.get("approvalStatus") for row in approvalSummaries}

    items = []
    for scope in scopes:
        scopedMetricId = scope["metric_id"]
        scopeMetadata = resolveScopeMetadata(scope, cycle)
        atomicItems = [
            buildAtomicItem(row, latestValueForInputMode(valueRows, row.get("atomic_metric_id"), resolveInputMode(row)))
            for row in atomicRowsByMetric.get(scopedMetricId, [])
        ]
        items.append(
            OnboardingMetricItemDto(
                metricId=scopedMetricId,
                metricName=scope.get("metric_name_kr"),
                issueDomain=scopeMetadata["issueDomain"],
                subIssueId=scopeMetadata["subIssueId"],
                subIssueCode=scopeMetadata["subIssueCode"],
                subIssueName=scopeMetadata["subIssueName"],
                scopeSourceType=scope.get("scope_source_type") or "PRE_DMA_G0",
                requiredYn=bool(scope.get("required_yn")),
                inputRequiredYn=bool(scope.get("input_required_yn")),
                approvalRequiredYn=bool(scope.get("approval_required_yn")),
                approvalPolicyCode=scope.get("approval_policy_code") or "INPUT_APPROVAL_ONLY",
                approvalStatus=approvalByMetric.get(scopedMetricId),
                rollupReadonlyYn=bool(scope.get("rollup_readonly_yn")),
                displayOrder=int(scope.get("display_order") or 0),
                assignment=assignmentByMetric.get(scopedMetricId),
                atomicItems=atomicItems,
            )
        )

    return OnboardingMetricsResponseDto(
        companyId=companyId,
        reportingYear=year,
        cycleId=int(cycle["id"]),
        cycleType=cycle.get("cycle_type") or CYCLE_TYPE_PRE_DMA_G0,
        metricScopeCode=cycle.get("metric_scope_code"),
        items=items,
    )


def saveMetricValues(
    *,
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userId: Optional[int] = None,
    userModel=None,
) -> OnboardingMetricValuesResponseDto:
    prepared = validateMetricValues(metricId=metricId, request=request, userId=userId, userModel=userModel)
    cycle = prepared["cycle"]
    group = prepared["group"]
    savedCount = saveMetricValueGroupsWithInvalidation([group])
    return OnboardingMetricValuesResponseDto(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=request.cycleType,
        metricId=metricId,
        savedItemCount=savedCount,
    )


def saveMetricValueGroupsWithInvalidation(groups: list[dict]) -> int:
    """Save metric values and invalidate downstream derived Facts for changed atomics."""
    if not groups:
        return 0
    from src.utils.db import getConn
    from src.repositories import onboardinginputrepository as inputRepo
    from src.repositories import rolluprepository as rollupRepo
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        savedCount = 0
        with conn.cursor(dictionary=True) as cur:
            for group in groups:
                companyId = group["companyId"]
                reportingYear = group["reportingYear"]
                metricId = group["metricId"]
                values = group["values"]
                cycleId = group["cycleId"]
                
                # ROLLUP_RESPONSE 사이클 쓰기 가능 여부 확인
                cur.execute(
                    "SELECT cycle_type, parent_rollup_batch_id FROM ESG_ONBOARDING_CYCLE WHERE id = ?",
                    (cycleId,),
                )
                cycleRow = cur.fetchone()
                if cycleRow:
                    scopeRepo.requireWritableCycleTx(cur, cycleRow, companyId, batchId=group.get("batchId"))

                # 변경 감지를 위한 기존 값 조회
                oldByAtomic = {}
                for value in values:
                    atomicId = value["atomicMetricId"]
                    cur.execute(
                        """
                        SELECT value_numeric, value_text
                        FROM ESG_ONBOARDING_INPUT_VALUE
                        WHERE company_id = ?
                          AND reporting_year = ?
                          AND metric_id = ?
                          AND atomic_metric_id = ?
                          AND delete_yn = 0
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (companyId, reportingYear, metricId, atomicId),
                    )
                    oldByAtomic[atomicId] = cur.fetchone()

                # 저장
                savedCount += inputRepo.upsertMetricInputValuesTx(
                    cur,
                    cycleId=cycleId,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    metricId=metricId,
                    assignmentId=group.get("assignmentId"),
                    values=values,
                    userId=group.get("userId"),
                )

                # 변경된 원자 지표 감지
                changedAtomicIds = []
                for value in values:
                    atomicId = value["atomicMetricId"]
                    old = oldByAtomic.get(atomicId)
                    if _atomicValueChanged(old, value):
                        changedAtomicIds.append(atomicId)

                # 변경된 원자 지표 하위 무효화
                if changedAtomicIds:
                    invalidateAffectedEntityFactsTx(
                        cur,
                        companyId=companyId,
                        reportingYear=reportingYear,
                        changedAtomicMetricIds=changedAtomicIds,
                    )
                if group.get("batchId") is not None:
                    rollupRepo.syncSourceReadinessTx(
                        cur,
                        batchId=int(group["batchId"]),
                        sourceCompanyId=companyId,
                        reportingYear=reportingYear,
                    )
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _atomicValueChanged(oldRow: dict, newValue: dict) -> bool:
    """기존 DB 행과 비교해 값이 실제로 변경되었으면 True를 반환."""
    if oldRow is None:
        # 신규 입력 — 항상 변경으로 간주
        return True
    oldNumeric = oldRow.get("value_numeric")
    newNumeric = newValue.get("valueNumeric")
    oldText = str(oldRow.get("value_text") or "").strip()
    newText = str(newValue.get("valueText") or "").strip()
    # 수치 비교
    if oldNumeric is not None or newNumeric is not None:
        try:
            if float(oldNumeric or 0) != float(newNumeric or 0):
                return True
        except (TypeError, ValueError):
            return True
    # 텍스트 비교
    if oldText != newText:
        return True
    return False


def validateMetricValues(
    *,
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userId: Optional[int] = None,
    userModel=None,
) -> dict:
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType, batchId=request.batchId)
    checkMetricInputPermission(
        cycle=cycle,
        companyId=request.companyId,
        metricId=metricId,
        userModel=userModel,
    )
    metrics = listMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=metricId,
        batchId=request.batchId,
        userModel=userModel,
    )
    metric = metrics.items[0]
    atomicById = {item.atomicMetricId: item for item in metric.atomicItems}
    cleanedValues = []
    for item in request.values or []:
        atomic = atomicById.get(item.atomicMetricId)
        if not atomic:
            raise ValueError(f"atomicMetricId does not belong to metricId={metricId}: {item.atomicMetricId}")
        if not atomic.editableYn:
            raise ValueError(f"Manual input is not allowed for atomicMetricId={item.atomicMetricId}, inputMode={atomic.inputMode}")
        cleanedValues.append(
            {
                "atomicMetricId": item.atomicMetricId,
                "valueNumeric": item.valueNumeric,
                "valueText": item.valueText,
                "unit": item.unit or atomic.unit,
            }
        )
    if not cleanedValues:
        raise ValueError("values is required")

    assignmentId = repo.resolveAssignmentId(int(cycle["id"]), request.companyId, metricId)
    return {
        "cycle": cycle,
        "metric": metric,
        "group": {
            "cycleId": int(cycle["id"]),
            "companyId": request.companyId,
            "reportingYear": request.reportingYear,
            "metricId": metricId,
            "assignmentId": assignmentId,
            "values": cleanedValues,
            "userId": userId,
            "batchId": request.batchId,
        },
    }


def saveMetricValueGroups(groups: list[dict]) -> int:
    sanitizedGroups = []
    for item in groups:
        group = item["group"] if "group" in item else item
        sanitizedGroups.append({
            key: value
            for key, value in group.items()
            if key != "batchId"
        })
    return repo.upsertMetricValueGroups(sanitizedGroups)


def requireCycle(
    companyId: int,
    reportingYear: int,
    cycleType: str,
    batchId: Optional[int] = None,
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    effectiveRunId = resolveCycleSourceMaterialityRunId(
        companyId,
        reportingYear,
        cycleType,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    cycle = repo.getCycle(
        companyId,
        reportingYear,
        cycleType,
        batchId=batchId,
        sourceMaterialityRunId=effectiveRunId,
    )
    if not cycle:
        raise ValueError(scopeNotReadyMessage(cycleType))
    if str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(scopeNotReadyMessage(cycleType))
    return cycle


def resolveCycleSourceMaterialityRunId(
    companyId: int,
    reportingYear: int,
    cycleType: str,
    sourceMaterialityRunId: Optional[int] = None,
) -> Optional[int]:
    if sourceMaterialityRunId is not None:
        return int(sourceMaterialityRunId)
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType != CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return None
    from src.repositories import reportworkflowrepository

    currentRun = reportworkflowrepository.getCurrent(companyId, reportingYear)
    if currentRun.get("id") is None:
        return 0
    return int(currentRun["id"])


def cycleNotReadyMessage(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return POST_DMA_DISCLOSURE_CYCLE_NOT_READY
    if normalizedCycleType == CYCLE_TYPE_ROLLUP_RESPONSE:
        return "받은 요청함 프로젝트가 초기화되지 않았습니다."
    return PRE_DMA_G0_CYCLE_NOT_READY


def scopeNotReadyMessage(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return POST_DMA_DISCLOSURE_SCOPE_NOT_READY
    if normalizedCycleType == CYCLE_TYPE_ROLLUP_RESPONSE:
        return "받은 요청함 지표 범위가 초기화되지 않았습니다."
    return PRE_DMA_G0_SCOPE_NOT_READY


def syntheticGeneralMetadata():
    return {
        "issueDomain": "general",
        "subIssueId": None,
        "subIssueCode": "GENERAL_MANAGEMENT",
        "subIssueName": "경영일반",
    }

def syntheticDependencyMetadata():
    return {
        "issueDomain": "general",
        "subIssueId": None,
        "subIssueCode": "DEPENDENCY_INPUT",
        "subIssueName": "추가 입력 필요 데이터",
    }

def requireMappedSubIssueMetadata(scope: dict, cycle: dict):
    issueDomain = normalizeIssueDomain(scope.get("sub_issue_domain"))
    subIssueId = scope.get("source_selected_sub_issue_id") or scope.get("sub_issue_id")
    subIssueCode = scope.get("source_sub_issue_code") or scope.get("sub_issue_code")
    subIssueName = scope.get("sub_issue_name")
    
    # If sub_issue_name is missing from JOIN but we have subIssueCode
    if subIssueCode and not subIssueName:
        subIssueName = subIssueCode
        
    if not issueDomain or subIssueId is None or not subIssueCode or not subIssueName:
        raise ValueError(
            "공시범위 메타데이터가 준비되지 않았습니다. "
            f"cycleId={cycle.get('id')}, "
            f"metricId={scope.get('metric_id')}, "
            f"subIssueCode={subIssueCode}"
        )
    return {
        "issueDomain": issueDomain,
        "subIssueId": int(subIssueId),
        "subIssueCode": subIssueCode,
        "subIssueName": subIssueName,
    }

def resolveScopeMetadata(scope: dict, cycle: dict) -> dict:
    cycleType = str(cycle.get("cycle_type") or "").strip().upper()
    
    if cycleType == CYCLE_TYPE_PRE_DMA_G0:
        return syntheticGeneralMetadata()

    if cycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return requireMappedSubIssueMetadata(scope, cycle)
        
    if cycleType == CYCLE_TYPE_ROLLUP_RESPONSE:
        if scope.get("source_sub_issue_code"):
            return requireMappedSubIssueMetadata(scope, cycle)
        scopeSourceType = str(scope.get("scope_source_type") or "").strip().upper()
        if scopeSourceType == "PRE_DMA_G0":
            return syntheticGeneralMetadata()
        return syntheticDependencyMetadata()

    return {
        "issueDomain": "general",
        "subIssueId": None,
        "subIssueCode": None,
        "subIssueName": None,
    }




def buildAtomicItem(row: dict, value: dict) -> OnboardingAtomicItemDto:
    inputMode = resolveInputMode(row)
    return OnboardingAtomicItemDto(
        metricId=row.get("metric_id"),
        atomicMetricId=row.get("atomic_metric_id"),
        metricName=row.get("metric_name_kr"),
        atomicName=row.get("atomic_name_kr"),
        dataValueType=row.get("data_value_type"),
        atomicDataRole=row.get("atomic_data_role"),
        rollupRole=row.get("rollup_role"),
        inputMode=inputMode,
        editableYn=isEditable(inputMode),
        requiredYn=bool(row.get("onboarding_input_yn")) and isEditable(inputMode),
        valueText=value.get("value_text"),
        valueNumeric=floatOrNone(value.get("value_numeric")),
        unit=value.get("unit") or row.get("unit"),
        inputStatus=value.get("input_status"),
        updatedAt=str(value.get("updated_at")) if value.get("updated_at") is not None else None,
    )


def resolveInputMode(row: dict) -> str:
    atomicMetricId = row.get("atomic_metric_id")
    atomicRole = row.get("atomic_data_role")
    rollupRole = row.get("rollup_role")

    if (
        atomicRole == "DERIVED"
        or rollupRole == "consolidated_result"
        or str(atomicMetricId or "").startswith("G0-02__G")
        or atomicMetricId == "G0-03__G0001"
    ):
        return "ROLLUP_READONLY"

    if atomicMetricId in STRUCTURED_LOOKUP_IDS:
        return "STRUCTURED_LOOKUP"

    if atomicMetricId == "G0-05__QL0001":
        return "YEAR_RANGE"

    dataValueType = str(row.get("data_value_type") or "").strip().upper()
    if (
        str(atomicMetricId or "").startswith("G0-02__Q")
        or str(atomicMetricId or "").startswith("G0-03__Q")
        or dataValueType in {"QUANT", "NUMBER", "NUMERIC"}
        or row.get("data_value_type") == "정량"
    ):
        return "MANUAL_NUMBER"

    return "MANUAL_TEXTAREA"


def isEditable(inputMode: str) -> bool:
    return inputMode in EDITABLE_INPUT_MODES


def latestValueForInputMode(rows: list[dict], atomicMetricId: str, inputMode: str) -> dict:
    if inputMode == "ROLLUP_READONLY":
        allowedSources = {"group_rollup_result"}
        priority = {"group_rollup_result": 0}
    elif inputMode == "STRUCTURED_LOOKUP":
        allowedSources = {
            "onboarding_input",
            "kpi_fact",
        }
        priority = {
            "onboarding_input": 0,
            "kpi_fact": 1,
        }
    else:
        allowedSources = {"onboarding_input", "kpi_fact"}
        priority = {"onboarding_input": 0, "kpi_fact": 1}

    candidates = [
        row
        for row in rows
        if row.get("atomic_metric_id") == atomicMetricId
        and row.get("source_table") in allowedSources
    ]
    if not candidates:
        return {}

    bestPriority = min(priority.get(row.get("source_table"), 99) for row in candidates)
    samePriorityRows = [
        row
        for row in candidates
        if priority.get(row.get("source_table"), 99) == bestPriority
    ]
    return max(samePriorityRows, key=lambda row: str(row.get("updated_at") or ""))


def buildAssignment(row: dict) -> OnboardingAssignmentDto:
    assignmentStatus = row.get("assignment_status")
    email = None
    if str(assignmentStatus or "").strip().lower() != "unassigned":
        email = row.get("invite_email") or row.get("user_email") or row.get("assignee_email")
    return OnboardingAssignmentDto(
        assignmentId=int(row["assignment_id"]) if row.get("assignment_id") is not None else None,
        assignmentStatus=assignmentStatus,
        assigneeUserId=int(row["assignee_user_id"]) if row.get("assignee_user_id") is not None else None,
        assigneeEmailMasked=maskEmail(email),
        dueDate=str(row.get("due_date")) if row.get("due_date") is not None else None,
    )






def floatOrNone(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def listVisibleMetricScopesForUser(scopes: list[dict], assignmentRows: list[dict], userModel) -> tuple[list[dict], bool, str]:
    if userModel is None or isAssignmentManager(userModel):
        return scopes, True, ""
    if isConsultant(userModel):
        return [], False, "Consultants cannot access onboarding input metrics"
        # raise PermissionError("Consultants cannot access onboarding input metrics")
    if not isEmployee(userModel):
        # raise PermissionError("Only assigned users can access onboarding input metrics")
        return [], False, "Only assigned users can access onboarding input metrics"
    actorUserId = getActorUserId(userModel)
    assignedMetricIds = {
        row.get("metric_id")
        for row in assignmentRows
        if row.get("assignee_user_id") is not None
        and actorUserId is not None
        and int(row.get("assignee_user_id")) == int(actorUserId)
        and str(row.get("assignment_status") or "").strip().lower() == assignmentRepo.ASSIGNMENT_STATUS_ASSIGNED
    }
    return [scope for scope in scopes if scope.get("metric_id") in assignedMetricIds], True, ""


def checkMetricInputPermission(*, cycle: dict, companyId: int, metricId: str, userModel) -> None:
    if userModel is None:
        return
    if isConsultant(userModel):
        raise PermissionError("Consultants cannot input onboarding metrics")
    if isAssignmentManager(userModel):
        return
    actorUserId = getActorUserId(userModel)
    if actorUserId is None:
        raise PermissionError("Authenticated user id is required")
    assignmentRows = assignmentRepo.listAssignmentRows(int(cycle["id"]), companyId)
    assignment = next((row for row in assignmentRows if row.get("metric_id") == metricId), None)
    if not assignment:
        raise PermissionError(f"Metric assignment is required: {metricId}")
    if str(assignment.get("assignment_status") or "").strip().lower() != assignmentRepo.ASSIGNMENT_STATUS_ASSIGNED:
        raise PermissionError(f"Metric assignment must be assigned before input: {metricId}")
    if assignment.get("assignee_user_id") is None or int(assignment.get("assignee_user_id")) != int(actorUserId):
        raise PermissionError(f"Only the assigned user can input metricId={metricId}")


def checkMetricStatusPermission(summary: dict, userModel) -> bool:
    if isReviewer(userModel) or isAssignmentManager(userModel):
        return True
    if isEmployee(userModel):
        actorUserId = getActorUserId(userModel)
        return (
            actorUserId is not None
            and summary.get("assigneeUserId") is not None
            and int(summary.get("assigneeUserId")) == int(actorUserId)
        )
    return False


def isAssignmentManager(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in ASSIGNMENT_MANAGER_ROLES or roleName in ASSIGNMENT_MANAGER_ROLE_NAMES


def isEmployee(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in EMPLOYEE_ROLES or roleName in EMPLOYEE_ROLE_NAMES


def isConsultant(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in CONSULTANT_ROLES or roleName in CONSULTANT_ROLE_NAMES


def isReviewer(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in REVIEWER_ROLES or roleName in REVIEWER_ROLE_NAMES


def ensureWorkflowPreDmaG0Cycle(run: dict, actorUserId: Optional[int] = None) -> dict:
    if not run:
        return {}
    return repo.ensurePreDmaG0Cycle(
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=run.get("report_basis_type"),
        sourceMaterialityRunId=int(run["id"]) if run.get("id") is not None else None,
        actorUserId=actorUserId,
    )


def ensureWorkflowPostDmaDisclosureCycle(run: dict, actorUserId: Optional[int] = None) -> dict:
    if not run:
        return {}
    return repo.ensurePostDmaDisclosureCycle(
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=run.get("report_basis_type"),
        sourceMaterialityRunId=int(run["id"]),
        actorUserId=actorUserId,
    )


def getActorUserId(userModel) -> Optional[int]:
    value = readUserField(userModel, "id")
    return int(value) if value is not None else None


def readUserField(userModel, key: str):
    if userModel is None:
        return None
    if isinstance(userModel, dict):
        return userModel.get(key)
    return getattr(userModel, key, None)
