export const ONBOARDING_SCENARIOS = {
  UNASSIGNED: "onboarding_unassigned",
  ASSIGNED: "onboarding_assigned",
  INVITE_PENDING: "onboarding_invite_pending",
  SELF_ASSIGNED: "onboarding_self_assigned",
  CONSULTANT_READONLY: "onboarding_consultant_readonly",
  DUE_DATE_OVERDUE: "onboarding_due_date_overdue",
};

export const APPROVAL_SCENARIOS = {
  NO_CONSULTANT: "approval_without_consultant",
  CONSULTANT_PENDING: "approval_with_consultant_pending",
  REVIEWED: "approval_reviewed",
  REJECTED: "approval_rejected",
  APPROVED: "approval_approved",
};

export const ROLLUP_SCENARIOS = {
  PARENT_PENDING: "rollup_parent_pending",
  PARENT_READY: "rollup_parent_calculate_ready",
  SUB_READY: "rollup_subsidiary_send_ready",
  SUB_MISSING: "rollup_subsidiary_missing_inputs",
};

export const APPROVAL_PROJECT_PREVIEW_ROWS = [
  {
    runId: "PREVIEW_RUN_2026",
    companyId: "PREVIEW_COMPANY",
    reportingYear: 2026,
    reportBasisType: "CONSOLIDATED",
    runStatus: "ACTIVE",
    workflowStep: "G0_ONBOARDING",
    currentStageLabel: "경영일반 승인",
    pendingCount: 7,
    readOnlyYn: false,
  },
  {
    runId: "PREVIEW_RUN_2025",
    companyId: "PREVIEW_COMPANY",
    reportingYear: 2025,
    reportBasisType: "CONSOLIDATED",
    runStatus: "COMPLETED",
    workflowStep: "COMPLETED",
    currentStageLabel: "전체 승인 완료",
    pendingCount: 0,
    readOnlyYn: true,
  },
  {
    runId: "PREVIEW_RUN_2024",
    companyId: "PREVIEW_COMPANY",
    reportingYear: 2024,
    reportBasisType: "ENTITY",
    runStatus: "COMPLETED",
    workflowStep: "COMPLETED",
    currentStageLabel: "전체 승인 완료",
    pendingCount: 0,
    readOnlyYn: true,
  },
];

export const ONBOARDING_PREVIEW_ROWS = [
  {
    metricId: "G0-01",
    metricName: "회사 개요",
    atomicItems: [],
  },
  {
    metricId: "G0-02",
    metricName: "재무 기준값",
    atomicItems: [],
  },
  {
    metricId: "G0-03",
    metricName: "조직 구조",
    atomicItems: [],
  },
];

export const APPROVAL_PREVIEW_ROWS = [
  {
    id: "G0-01",
    metricId: "G0-01",
    metricName: "회사 개요",
    issueDomain: "general",
    issueGroup: "경영일반",
    actionSupportedYn: false,
    actionDisabledReason: "현재 MVP에서는 G0-02 승인 처리만 지원합니다.",
  },
  {
    id: "G0-02",
    metricId: "G0-02",
    metricName: "재무 기준값",
    issueDomain: "general",
    issueGroup: "경영일반",
    actionSupportedYn: true,
    actionDisabledReason: null,
  },
  {
    id: "G0-03",
    metricId: "G0-03",
    metricName: "조직 구조",
    issueDomain: "general",
    issueGroup: "경영일반",
    actionSupportedYn: false,
    actionDisabledReason: "현재 MVP에서는 G0-02 승인 처리만 지원합니다.",
  },
];

export const PREVIEW_WORKFLOW = {
  runId: "PREVIEW_RUN",
  workflowStep: "G0_INPUT",
  reportBasisType: "CONSOLIDATED",
  nextAction: "REQUEST_ROLLUP",
};

export const mergeOnboardingFixtureRows = (groupedItems, scenario) => {
  const baseRows =
    Array.isArray(groupedItems) && groupedItems.length > 0
      ? groupedItems
      : ONBOARDING_PREVIEW_ROWS;

  return baseRows.map((item) => {
    let mock = {
      assigneeName: null,
      assigneeEmail: null,
      assignmentStatus: "UNASSIGNED",
      inviteStatus: null,
      selfAssignedYn: false,
      submissionDueDate: null,
      inputStatus: "미입력",
      approvalStatus: "미제출",
    };

    switch (scenario) {
      case ONBOARDING_SCENARIOS.ASSIGNED:
        mock = {
          ...mock,
          assigneeName: "최수아",
          assigneeEmail: "sua@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
        };
        break;
      case ONBOARDING_SCENARIOS.INVITE_PENDING:
        mock = {
          ...mock,
          assigneeName: "김하영",
          assigneeEmail: "hayoung@example.com",
          assignmentStatus: "ASSIGNED",
          inviteStatus: "PENDING",
          submissionDueDate: "2026-06-30",
        };
        break;
      case ONBOARDING_SCENARIOS.SELF_ASSIGNED:
        mock = {
          ...mock,
          assigneeName: "최수아",
          selfAssignedYn: true,
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
          inputStatus: "작성중",
        };
        break;
      case ONBOARDING_SCENARIOS.CONSULTANT_READONLY:
        mock = {
          ...mock,
          assigneeName: "최수아",
          assigneeEmail: "sua@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
          inputStatus: "제출완료",
          approvalStatus: "검토대기",
        };
        break;
      case ONBOARDING_SCENARIOS.DUE_DATE_OVERDUE:
        mock = {
          ...mock,
          assigneeName: "최수아",
          assigneeEmail: "sua@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-01",
          inputStatus: "작성중",
        };
        break;
      default:
        break;
    }

    return { ...item, ...mock };
  });
};

export const mergeApprovalFixtureRows = (pagedInputs, scenario) => {
  const baseRows =
    Array.isArray(pagedInputs) && pagedInputs.length > 0
      ? pagedInputs
      : APPROVAL_PREVIEW_ROWS;

  return baseRows.map((item) => {
    let mock = {
      id: item.id || item.metricId,
      metricId: item.metricId || item.issueId || item.id,
      metricName: item.metricName || item.checklistQuestion || item.questionName || "지표명",
      issueDomain: item.issueDomain || "general",
      issueGroup: item.issueGroup || "경영일반",
      actionSupportedYn: item.actionSupportedYn ?? true,
      actionDisabledReason: item.actionDisabledReason ?? null,
      assigneeName: item.assigneeName || item.userName || "최수아",
      inputCompletedCount: item.inputCompletedCount ?? 4,
      inputMissingCount: item.inputMissingCount ?? 1,
      submitStatus: item.submitStatus || "SUBMITTED",
      reviewStatus: item.reviewStatus || "PENDING",
      approvalStatus: item.approvalStatus || "PENDING",
      submittedAt: item.submittedAt || "2026-06-02",
      value: item.value ?? "125,000",
      unit: item.unit ?? "원",
    };

    switch (scenario) {
      case APPROVAL_SCENARIOS.NO_CONSULTANT:
      case APPROVAL_SCENARIOS.CONSULTANT_PENDING:
        mock = {
          ...mock,
          submitStatus: "SUBMITTED",
          reviewStatus: "PENDING",
          approvalStatus: "PENDING",
        };
        break;
      case APPROVAL_SCENARIOS.REVIEWED:
        mock = {
          ...mock,
          submitStatus: "SUBMITTED",
          reviewStatus: "REVIEWED",
          approvalStatus: "PENDING",
        };
        break;
      case APPROVAL_SCENARIOS.REJECTED:
        mock = {
          ...mock,
          submitStatus: "SUBMITTED",
          reviewStatus: "REVIEWED",
          approvalStatus: "REJECTED",
        };
        break;
      case APPROVAL_SCENARIOS.APPROVED:
        mock = {
          ...mock,
          submitStatus: "SUBMITTED",
          reviewStatus: "REVIEWED",
          approvalStatus: "APPROVED",
        };
        break;
      default:
        break;
    }

    return { ...item, ...mock };
  });
};

export const getFixtureRollupStatus = (scenario) => {
  switch (scenario) {
    case ROLLUP_SCENARIOS.PARENT_PENDING:
      return {
        persona: "PARENT",
        requestedCount: 3,
        sentCount: 2,
        pendingCount: 1,
        calculateReadyYn: false,
        dmaReadyYn: false,
        batchStatus: "PENDING",
      };
    case ROLLUP_SCENARIOS.PARENT_READY:
      return {
        persona: "PARENT",
        requestedCount: 3,
        sentCount: 3,
        pendingCount: 0,
        calculateReadyYn: true,
        dmaReadyYn: true,
        batchStatus: "COMPLETED",
      };
    case ROLLUP_SCENARIOS.SUB_READY:
      return {
        persona: "SUBSIDIARY",
        parentCompanyName: "SKM 지주사",
        reportingYear: 2026,
        sendReadyYn: true,
        missingAtomicMetricIds: [],
      };
    case ROLLUP_SCENARIOS.SUB_MISSING:
      return {
        persona: "SUBSIDIARY",
        parentCompanyName: "SKM 지주사",
        reportingYear: 2026,
        sendReadyYn: false,
        missingAtomicMetricIds: ["G0-01", "G0-02"],
      };
    default:
      return null;
  }
};
