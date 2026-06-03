import { STEP12_UI_FIXTURE_ENABLED } from '@/dev/step12UiPreview/config';

export const ONBOARDING_SCENARIOS = {
  UNASSIGNED: 'onboarding_unassigned',
  ASSIGNED: 'onboarding_assigned',
  INVITE_PENDING: 'onboarding_invite_pending',
  SELF_ASSIGNED: 'onboarding_self_assigned',
  CONSULTANT_READONLY: 'onboarding_consultant_readonly',
  DUE_DATE_OVERDUE: 'onboarding_due_date_overdue',
};

export const APPROVAL_SCENARIOS = {
  NO_CONSULTANT: 'approval_without_consultant',
  CONSULTANT_PENDING: 'approval_with_consultant_pending',
  REVIEWED: 'approval_reviewed',
  REJECTED: 'approval_rejected',
  APPROVED: 'approval_approved',
};

export const ROLLUP_SCENARIOS = {
  PARENT_PENDING: 'rollup_parent_pending',
  PARENT_READY: 'rollup_parent_calculate_ready',
  SUB_READY: 'rollup_subsidiary_send_ready',
  SUB_MISSING: 'rollup_subsidiary_missing_inputs',
};

export const ONBOARDING_PREVIEW_ROWS = [
  {
    metricId: "G0-01",
    metricName: "조직 정보",
    atomicItems: [],
  },
  {
    metricId: "G0-02",
    metricName: "보고 경계",
    atomicItems: [],
  },
  {
    metricId: "G0-03",
    metricName: "지배구조 정보",
    atomicItems: [],
  },
];

export const APPROVAL_PREVIEW_ROWS = [
  {
    id: "G0-01",
    metricId: "G0-01",
    metricName: "조직 정보",
  },
  {
    id: "G0-02",
    metricId: "G0-02",
    metricName: "보고 경계",
  },
  {
    id: "G0-03",
    metricId: "G0-03",
    metricName: "지배구조 정보",
  },
];

export const PREVIEW_WORKFLOW = {
  runId: "PREVIEW_RUN",
  workflowStep: "G0_INPUT",
  reportBasisType: "CONSOLIDATED",
  nextAction: "REQUEST_ROLLUP",
};

export const PREVIEW_TODAY = "2026-06-03";

export const mergeOnboardingFixtureRows = (groupedItems, scenario) => {
  const baseRows =
    Array.isArray(groupedItems) && groupedItems.length > 0
      ? groupedItems
      : ONBOARDING_PREVIEW_ROWS;

  return baseRows.map((item, index) => {
    let mock = {
      assigneeName: null,
      assigneeEmail: null,
      assignmentStatus: 'UNASSIGNED',
      inviteStatus: null,
      selfAssignedYn: false,
      submissionDueDate: null,
      inputStatus: '미입력',
      approvalStatus: '미제출',
    };

    switch (scenario) {
      case ONBOARDING_SCENARIOS.ASSIGNED:
        mock = { ...mock, assigneeName: '최수아', assigneeEmail: 'sua@company.com', assignmentStatus: 'ASSIGNED', submissionDueDate: '2026-06-30' };
        break;
      case ONBOARDING_SCENARIOS.INVITE_PENDING:
        mock = { ...mock, assigneeName: '김하영', assigneeEmail: 'hayoung@example.com', assignmentStatus: 'ASSIGNED', inviteStatus: 'PENDING', submissionDueDate: '2026-06-30' };
        break;
      case ONBOARDING_SCENARIOS.SELF_ASSIGNED:
        mock = { ...mock, assigneeName: '최수아', selfAssignedYn: true, assignmentStatus: 'ASSIGNED', submissionDueDate: '2026-06-30', inputStatus: '작성중' };
        break;
      case ONBOARDING_SCENARIOS.CONSULTANT_READONLY:
        mock = { ...mock, assigneeName: '최수아', assigneeEmail: 'sua@company.com', assignmentStatus: 'ASSIGNED', submissionDueDate: '2026-06-30', inputStatus: '제출완료', approvalStatus: '검토대기' };
        break;
      case ONBOARDING_SCENARIOS.DUE_DATE_OVERDUE:
        mock = { ...mock, assigneeName: '최수아', assigneeEmail: 'sua@company.com', assignmentStatus: 'ASSIGNED', submissionDueDate: '2026-06-01', inputStatus: '작성중' };
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

  return baseRows.map(item => {
    let mock = {
      metricId: item.issueId || item.id,
      metricName: item.checklistQuestion || item.questionName || '지표명',
      assigneeName: item.userName || '최수아',
      inputCompletedCount: 4,
      inputMissingCount: 1,
      submitStatus: 'SUBMITTED',
      reviewStatus: 'PENDING',
      approvalStatus: 'PENDING',
      submittedAt: '2026-06-02',
    };

    switch (scenario) {
      case APPROVAL_SCENARIOS.NO_CONSULTANT:
        mock.submitStatus = 'SUBMITTED';
        mock.reviewStatus = 'PENDING';
        mock.approvalStatus = 'PENDING';
        break;
      case APPROVAL_SCENARIOS.CONSULTANT_PENDING:
        mock.submitStatus = 'SUBMITTED';
        mock.reviewStatus = 'PENDING';
        mock.approvalStatus = 'PENDING';
        break;
      case APPROVAL_SCENARIOS.REVIEWED:
        mock.submitStatus = 'SUBMITTED';
        mock.reviewStatus = 'REVIEWED';
        mock.approvalStatus = 'PENDING';
        break;
      case APPROVAL_SCENARIOS.REJECTED:
        mock.submitStatus = 'SUBMITTED';
        mock.reviewStatus = 'REVIEWED';
        mock.approvalStatus = 'REJECTED';
        break;
      case APPROVAL_SCENARIOS.APPROVED:
        mock.submitStatus = 'SUBMITTED';
        mock.reviewStatus = 'REVIEWED';
        mock.approvalStatus = 'APPROVED';
        break;
    }
    
    return { ...item, ...mock };
  });
};

export const getFixtureRollupStatus = (scenario) => {
  switch (scenario) {
    case ROLLUP_SCENARIOS.PARENT_PENDING:
      return { persona: 'PARENT', requestedCount: 3, sentCount: 2, pendingCount: 1, calculateReadyYn: false, dmaReadyYn: false, batchStatus: 'PENDING' };
    case ROLLUP_SCENARIOS.PARENT_READY:
      return { persona: 'PARENT', requestedCount: 3, sentCount: 3, pendingCount: 0, calculateReadyYn: true, dmaReadyYn: true, batchStatus: 'COMPLETED' };
    case ROLLUP_SCENARIOS.SUB_READY:
      return { persona: 'SUBSIDIARY', parentCompanyName: 'SKM 지주사', reportingYear: 2026, sendReadyYn: true, missingAtomicMetricIds: [] };
    case ROLLUP_SCENARIOS.SUB_MISSING:
      return { persona: 'SUBSIDIARY', parentCompanyName: 'SKM 지주사', reportingYear: 2026, sendReadyYn: false, missingAtomicMetricIds: ['G0-01', 'G0-02'] };
    default:
      return null;
  }
};
