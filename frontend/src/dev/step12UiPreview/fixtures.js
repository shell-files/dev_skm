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
    currentStageLabel: "G0 approval",
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
    currentStageLabel: "All approvals completed",
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
    currentStageLabel: "All approvals completed",
    pendingCount: 0,
    readOnlyYn: true,
  },
];

export const ONBOARDING_PREVIEW_ROWS = [
  {
    metricId: "G0-01",
    metricName: "Company overview",
    atomicItems: [],
  },
  {
    metricId: "G0-02",
    metricName: "Financial basis",
    atomicItems: [],
  },
  {
    metricId: "G0-03",
    metricName: "Organization structure",
    atomicItems: [],
  },
];

export const APPROVAL_PREVIEW_ROWS = [
  {
    id: "G0-01",
    metricId: "G0-01",
    metricName: "Company overview",
    issueDomain: "general",
    issueGroup: "General",
    actionSupportedYn: false,
    actionDisabledReason: "MVP approval action is limited to G0-02.",
  },
  {
    id: "G0-02",
    metricId: "G0-02",
    metricName: "Financial basis",
    issueDomain: "general",
    issueGroup: "General",
    actionSupportedYn: true,
    actionDisabledReason: null,
  },
  {
    id: "G0-03",
    metricId: "G0-03",
    metricName: "Organization structure",
    issueDomain: "general",
    issueGroup: "General",
    actionSupportedYn: false,
    actionDisabledReason: "MVP approval action is limited to G0-02.",
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
      inputStatus: "NOT_STARTED",
      approvalStatus: "NOT_SUBMITTED",
    };

    switch (scenario) {
      case ONBOARDING_SCENARIOS.ASSIGNED:
        mock = {
          ...mock,
          assigneeName: "Assignee",
          assigneeEmail: "assignee@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
        };
        break;
      case ONBOARDING_SCENARIOS.INVITE_PENDING:
        mock = {
          ...mock,
          assigneeName: "Invited user",
          assigneeEmail: "invitee@example.com",
          assignmentStatus: "ASSIGNED",
          inviteStatus: "PENDING",
          submissionDueDate: "2026-06-30",
        };
        break;
      case ONBOARDING_SCENARIOS.SELF_ASSIGNED:
        mock = {
          ...mock,
          assigneeName: "Self assigned",
          selfAssignedYn: true,
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
          inputStatus: "IN_PROGRESS",
        };
        break;
      case ONBOARDING_SCENARIOS.CONSULTANT_READONLY:
        mock = {
          ...mock,
          assigneeName: "Assignee",
          assigneeEmail: "assignee@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-30",
          inputStatus: "SUBMITTED",
          approvalStatus: "PENDING_REVIEW",
        };
        break;
      case ONBOARDING_SCENARIOS.DUE_DATE_OVERDUE:
        mock = {
          ...mock,
          assigneeName: "Assignee",
          assigneeEmail: "assignee@company.com",
          assignmentStatus: "ASSIGNED",
          submissionDueDate: "2026-06-01",
          inputStatus: "IN_PROGRESS",
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
      metricName:
        item.metricName ||
        item.checklistQuestion ||
        item.questionName ||
        "Metric",
      issueDomain: item.issueDomain || "general",
      issueGroup: item.issueGroup || "General",
      actionSupportedYn: item.actionSupportedYn ?? true,
      actionDisabledReason: item.actionDisabledReason ?? null,
      assigneeName: item.assigneeName || item.userName || "Assignee",
      inputCompletedCount: item.inputCompletedCount ?? 4,
      inputMissingCount: item.inputMissingCount ?? 1,
      submitStatus: item.submitStatus || "SUBMITTED",
      reviewStatus: item.reviewStatus || "PENDING",
      approvalStatus: item.approvalStatus || "PENDING",
      submittedAt: item.submittedAt || "2026-06-02",
      value: item.value ?? "125,000",
      unit: item.unit ?? "KRW",
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
    case ROLLUP_SCENARIOS.PARENT_READY:
      return {
        nextAction: "CALCULATE_ROLLUP",
        statusLabel: "Ready to calculate",
      };
    case ROLLUP_SCENARIOS.SUB_READY:
      return {
        nextAction: "SEND_SOURCE_DATA",
        statusLabel: "Ready to send",
      };
    case ROLLUP_SCENARIOS.SUB_MISSING:
      return {
        nextAction: "COMPLETE_INPUTS",
        statusLabel: "Missing required inputs",
      };
    default:
      return {
        nextAction: "WAIT_ROLLUP",
        statusLabel: "Waiting for subsidiary data",
      };
  }
};
