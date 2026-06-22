/**
 * onboardingUtils.js
 * 레이어: Utils (onboards)
 * 역할: 온보딩 지표 입력 모드 판별·상태 계산·통계 집계·역할 판별·항목 병합 등 순수 유틸리티 함수 모음
 */
export const STRUCTURED_LOOKUP_IDS = new Set(["G0-05__QL0002", "G0-06__QL0001"]);
export const EDITABLE_INPUT_MODES = new Set([
  "MANUAL_NUMBER",
  "MANUAL_TEXTAREA",
  "YEAR_RANGE",
  "STRUCTURED_LOOKUP",
]);

export const getAtomicId = (item = {}) => item.atomicMetricId || item.issueId || "";

export const resolveG0InputMode = (item = {}) => {
  const atomicMetricId = getAtomicId(item);
  const dataValueType = String(item.dataValueType || "").trim().toUpperCase();

  if (
    item.atomicDataRole === "DERIVED" ||
    item.rollupRole === "consolidated_result" ||
    /^G0-02__G\d+/.test(atomicMetricId) ||
    atomicMetricId === "G0-03__G0001"
  ) {
    return "ROLLUP_READONLY";
  }

  if (
    STRUCTURED_LOOKUP_IDS.has(atomicMetricId) ||
    item.inputMode === "STRUCTURED_LOOKUP"
  ) {
    return "STRUCTURED_LOOKUP";
  }

  if (item.editableYn === false) {
    return "ROLLUP_READONLY";
  }

  if (item.inputMode) {
    return item.inputMode;
  }

  if (atomicMetricId === "G0-05__QL0001") {
    return "YEAR_RANGE";
  }

  if (
    /^G0-02__Q\d+/.test(atomicMetricId) ||
    /^G0-03__Q\d+/.test(atomicMetricId) ||
    dataValueType === "QUANT" ||
    dataValueType === "NUMBER" ||
    dataValueType === "NUMERIC" ||
    item.dataValueType === "정량"
  ) {
    return "MANUAL_NUMBER";
  }

  return "MANUAL_TEXTAREA";
};

export const isEditableItem = (item) => EDITABLE_INPUT_MODES.has(resolveG0InputMode(item));

export const getInputTypeBadge = (item = {}) => {
  switch (resolveG0InputMode(item)) {
    case "MANUAL_NUMBER":
      return { label: "숫자 입력", cls: "direct" };
    case "MANUAL_TEXTAREA":
      return { label: "서술 입력", cls: "narrative" };
    case "YEAR_RANGE":
      return { label: "기간 입력", cls: "direct" };
    case "STRUCTURED_LOOKUP":
      return { label: "범위 설정", cls: "reference" };
    case "ROLLUP_READONLY":
      return { label: "자동 산출", cls: "reference" };
    default:
      return { label: resolveG0InputMode(item) || "-", cls: "" };
  }
};

export const hasAtomicValue = (item) =>
  (item.valueText !== null && item.valueText !== undefined && item.valueText !== "") ||
  (item.valueNumeric !== null && item.valueNumeric !== undefined);

export const calculateMetricStatus = (subMetrics = []) => {
  const statusTargets = subMetrics.filter((sub) => isEditableItem(sub));
  if (statusTargets.length === 0) {
    const modes = new Set(subMetrics.map((sub) => resolveG0InputMode(sub)));
    if (modes.has("ROLLUP_READONLY")) return { label: "자동 산출", cls: "draft" };
    if (modes.has("STRUCTURED_LOOKUP")) return { label: "범위 설정 필요", cls: "draft" };
    return { label: "조회 전용", cls: "draft" };
  }

  const completed = statusTargets.filter((sub) => hasAtomicValue(sub)).length;
  if (completed === 0) return { label: "미입력", cls: "not-started" };
  if (completed < statusTargets.length) return { label: "진행중", cls: "draft" };
  return { label: "입력 완료", cls: "approved" };
};

export const calculateProfileStats = (items = []) => {
  const metricsMap = new Map();
  items.forEach((item) => {
    if (!item.metricId) return;
    if (!metricsMap.has(item.metricId)) {
      metricsMap.set(item.metricId, []);
    }
    metricsMap.get(item.metricId).push(item);
  });

  let totalCount = 0;
  let completedCount = 0;
  let inProgressCount = 0;
  let notStartedCount = 0;

  for (const subItems of metricsMap.values()) {
    const editableItems = subItems.filter(isEditableItem);
    if (editableItems.length === 0) {
      // Exclude auto-calculated / read-only metrics from the count
      continue;
    }
    totalCount++;
    const filledCount = editableItems.filter(hasAtomicValue).length;
    if (filledCount === 0) {
      notStartedCount++;
    } else if (filledCount < editableItems.length) {
      inProgressCount++;
    } else {
      completedCount++;
    }
  }

  return {
    totalCount,
    completedCount,
    inProgressCount,
    notStartedCount,
  };
};

export const getStatusInfo = (status) => {
  if (status === "COMPLETED") return { label: "완료", cls: "approved" };
  if (status === "IN_PROGRESS") return { label: "진행중", cls: "not-started" };
  return { label: "미시작", cls: "not-started" };
};

export const getStatusText = (status) => {
  if (status === "DRAFT" || status === "IN_PROGRESS") return "작성중";
  if (status === "SUBMITTED") return "검토요청";
  if (status === "APPROVED" || status === "COMPLETED") return "완료";
  return "미입력";
};

export const getStatusClass = (status) => {
  if (status === "DRAFT" || status === "IN_PROGRESS") return "draft";
  if (status === "SUBMITTED") return "submitted";
  if (status === "APPROVED" || status === "COMPLETED") return "approved";
  return "not-started";
};

export const normalizeViewerRole = (role) => String(role || "").trim().toUpperCase();

export const isAssignmentManagerRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return [
    "ADMIN", "ESG", "ESG_MANAGER", "MANAGER", "OWNER",
    "관리자", "ESG담당자", "ESG 담당자",
  ].includes(normalized);
};

export const isEmployeeRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return ["EMPLOYEE", "ASSIGNEE", "부서담당자", "부서 담당자"].includes(normalized);
};

export const isConsultantRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return ["CONSULTANT", "컨설턴트"].includes(normalized);
};

export const isNoRunWorkflow = (workflow) => workflow?.workflowStep === "NO_RUN";

export const isPendingSubsidiaryRequest = (request = {}) => {
  const requestStatus = String(request.requestStatus || "").trim().toUpperCase();
  const transferStatus = String(request.transferStatus || "").trim().toUpperCase();
  if (transferStatus === "SENT" || transferStatus === "RECEIVED" || requestStatus === "RECEIVED") {
    return false;
  }
  return (
    request.sendReadyYn === true ||
    transferStatus === "NOT_SENT" ||
    transferStatus === "PENDING" ||
    requestStatus === "REQUESTED" ||
    requestStatus === "PENDING"
  );
};

export const flattenOnboardingItems = (metrics = []) =>
  metrics.flatMap((metric) =>
    (metric.atomicItems || []).map((atomic) => ({
      ...atomic,
      metricId: atomic.metricId || metric.metricId,
      metricName: atomic.metricName || metric.metricName,
      issueDomain: metric.issueDomain,
      subIssueId: metric.subIssueId,
      subIssueCode: metric.subIssueCode,
      subIssueName: metric.subIssueName,
      scopeSourceType: metric.scopeSourceType,
      approvalPolicyCode: metric.approvalPolicyCode,
      approvalStatus: metric.approvalStatus,
      assignment: metric.assignment,
    }))
  );

export const normalizeAssignmentStatus = (status) => String(status || "").trim().toUpperCase();

export const normalizeInviteStatus = (status) => {
  const normalized = String(status || "").trim().toUpperCase();
  if (normalized === "승인대기" || normalized === "PENDING") return "PENDING";
  if (normalized === "승인완료" || normalized === "COMPLETED" || normalized === "ACCEPTED") return "COMPLETED";
  if (normalized === "승인취소" || normalized === "REVOKED" || normalized === "CANCELLED") return "REVOKED";
  return normalized;
};

export const resolveOnboardingCycleType = (workflow, requestedCycleType, preferredCycleType) => {
  const requested = String(requestedCycleType || "").trim().toUpperCase();
  if (requested === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";
  if (requested === "PRE_DMA_G0") return "PRE_DMA_G0";

  const preferred = String(preferredCycleType || "").trim().toUpperCase();
  if (preferred === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";
  if (preferred === "PRE_DMA_G0") return "PRE_DMA_G0";

  const explicitCycle = String(
    workflow?.currentCycleType || workflow?.cycleType || workflow?.onboardingCycleType || ""
  ).trim().toUpperCase();
  if (explicitCycle === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";

  const nextAction = String(workflow?.nextAction || "").trim().toUpperCase();
  if (
    ["POST_DMA_INPUT", "POST_DMA_ASSIGNMENT", "POST_DMA_DISCLOSURE",
     "REPORT_DISCLOSURE_INPUT", "REPORT_DISCLOSURE_ROLLUP"].includes(nextAction)
  ) {
    return "POST_DMA_DISCLOSURE";
  }

  const selectionSource = String(workflow?.selectionSource || "").trim().toUpperCase();
  const fallbackYn = workflow?.fallbackYn === true;
  const selectedCount = Number(workflow?.selectedSubIssueCount || 0);
  const postDmaCycleId = workflow?.postDmaCycleId;
  const postDmaScopeMetricCount = Number(workflow?.postDmaScopeMetricCount || 0);
  if (
    selectionSource === "TABLE" && !fallbackYn && selectedCount >= 5 &&
    postDmaCycleId && postDmaScopeMetricCount > 0
  ) {
    return "POST_DMA_DISCLOSURE";
  }

  return "PRE_DMA_G0";
};

export const resolveRollupContext = (cycleType) => {
  const normalized = String(cycleType || "").trim().toUpperCase();
  if (normalized === "POST_DMA_DISCLOSURE") {
    return { rollupPurposeCode: "REPORT_DISCLOSURE", metricScopeCode: "SELECTED_DISCLOSURE" };
  }
  return { rollupPurposeCode: "DMA_PRECHECK", metricScopeCode: "G0_02_FINANCIAL_BASIS" };
};

export const formatApiDetail = (detail) => {
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || item?.message || JSON.stringify(item)).join("\n");
  }
  if (detail && typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return String(detail || "");
};

export const mergeAssignmentIntoItems = (items = [], assignments = []) => {
  const assignmentByMetric = new Map((assignments || []).map((item) => [item.metricId, item]));
  return items.map((item) => {
    const assignment = assignmentByMetric.get(item.metricId) || item.assignment || {};
    const assignmentStatus = normalizeAssignmentStatus(assignment.assignmentStatus);
    const inviteStatus = normalizeInviteStatus(assignment.inviteStatus);
    const assigneeEmail = assignment.assigneeEmailMasked || item.assigneeEmail || null;
    return {
      ...item,
      assignment,
      assignmentStatus,
      inviteStatus,
      assigneeUserId: assignment.assigneeUserId ?? item.assigneeUserId,
      assigneeEmail,
      assigneeName: item.assigneeName || null,
      submissionDueDate: assignment.dueDate || item.submissionDueDate || item.dueDate,
    };
  });
};

export const getProfileStatusFromItems = (items = []) => {
  const editableItems = items.filter((item) => isEditableItem(item));
  if (editableItems.length === 0) return "NOT_STARTED";
  const completedCount = editableItems.filter((item) => hasAtomicValue(item)).length;
  if (completedCount === 0) return "NOT_STARTED";
  if (completedCount < editableItems.length) return "IN_PROGRESS";
  return "COMPLETED";
};
