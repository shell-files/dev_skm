import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GET, POST, POST_FORM, PUT, PATCH } from "@utils/Network";

export const DEFAULT_REPORTING_YEAR = new Date().getFullYear();

export const normalizeReportingYear = (value) => {
  const year = Number(value);
  return Number.isInteger(year) && year >= 2000 && year <= 2100
    ? year
    : DEFAULT_REPORTING_YEAR;
};

const ONBOARDING_ASSIGNMENT_ROOT = "/onboardingAssignment";

const normalizeDirectDtoResponse = (res) => {
  if (!res || res?.status === false || res?.success === false) {
    return res;
  }
  if (res?.data) {
    return res;
  }
  return {
    success: true,
    data: res,
  };
};

const isApiFailed = (res) =>
  !res || res?.status === false || res?.success === false;

const toApiError = (res, fallbackMessage) => ({
  status: false,
  message:
    res?.error?.message ||
    res?.error?.detail ||
    res?.detail ||
    res?.message ||
    fallbackMessage,
  error: res?.error || null,
});

export const apiErrorMessage = (error, fallbackMessage = "요청 처리 중 오류가 발생했습니다.") => {
  if (typeof error === "string") return error;
  return error?.response?.data?.message ||
    error?.response?.data?.detail ||
    error?.error?.message ||
    error?.error?.detail ||
    error?.data?.message ||
    error?.data?.detail ||
    error?.message ||
    error?.detail ||
    error?.msg ||
    fallbackMessage;
};

const ROLLUP_API_ROOT = "/api/v1/rollups";
const ONBOARDING_APPROVAL_API_ROOT = "/api/v1/onboarding-approvals";
const REPORT_WORKFLOW_API_ROOT = "/api/v1/report-workflow";

const normalizeRollupPurposeCode = (code) =>
  String(code || "DMA_PRECHECK").trim().toUpperCase();

const assertRollupId = (value, name) => {
  const normalized = Number(value);
  if (!Number.isFinite(normalized) || normalized <= 0) {
    throw new Error(`${name} is required`);
  }
  return normalized;
};

const buildRollupLookupParams = ({
  runId,
  sourceCycleId,
  rollupPurposeCode,
  metricScopeCode,
} = {}) => {
  const purposeCode = normalizeRollupPurposeCode(rollupPurposeCode);
  const params = {};

  if (rollupPurposeCode) params.rollupPurposeCode = purposeCode;
  if (metricScopeCode) params.metricScopeCode = metricScopeCode;

  if (purposeCode === "REPORT_DISCLOSURE") {
    params.sourceCycleId = assertRollupId(sourceCycleId, "sourceCycleId");
    return params;
  }

  params.runId = assertRollupId(runId, "runId");
  return params;
};

const buildRollupBatchBody = ({
  runId,
  sourceCycleId,
  sourceCompanyIds,
  rollupPurposeCode,
  metricScopeCode,
} = {}) => {
  const purposeCode = normalizeRollupPurposeCode(rollupPurposeCode);
  const body = {
    sourceCompanyIds: Array.isArray(sourceCompanyIds) ? sourceCompanyIds : [],
  };

  if (rollupPurposeCode) body.rollupPurposeCode = purposeCode;
  if (metricScopeCode) body.metricScopeCode = metricScopeCode;

  if (purposeCode === "REPORT_DISCLOSURE") {
    body.sourceCycleId = assertRollupId(sourceCycleId, "sourceCycleId");
    return body;
  }

  body.runId = assertRollupId(runId, "runId");
  return body;
};

const rejectIfFailed = (res, rejectWithValue, fallbackMessage) => {
  if (isApiFailed(res)) {
    return rejectWithValue(toApiError(res, fallbackMessage));
  }
  return res;
};

const dataOf = (payload) => payload?.data ?? payload ?? null;

const normalizeApprovalDecisionPayload = (payload = {}) => {
  const normalized = { ...payload };
  if (normalized.commentText == null && normalized.comment != null) {
    normalized.commentText = normalized.comment;
  }
  delete normalized.comment;
  return normalized;
};

const attachExplicitBatchContext = (payload = {}, batchId) => {
  const normalized = { ...payload };
  if (batchId != null) {
    normalized.batchId = Number(batchId);
  }
  const cycleType = String(normalized.cycleType || "").trim().toUpperCase();
  if (
    cycleType === "ROLLUP_RESPONSE" &&
    (!Number.isInteger(Number(normalized.batchId)) || Number(normalized.batchId) <= 0)
  ) {
    throw new Error("batchId is required for ROLLUP_RESPONSE");
  }
  return normalized;
};

const approvalContextKeyOf = ({
  companyId,
  reportingYear = DEFAULT_REPORTING_YEAR,
  cycleType = "PRE_DMA_G0",
  status = "",
  assignedOnlyYn = true,
  batchId,
} = {}) => {
  const normalizedCycleType = String(cycleType || "").trim().toUpperCase();
  const normalizedBatchId =
    normalizedCycleType === "ROLLUP_RESPONSE" ? Number(batchId) || "" : "";
  return [
    companyId ?? "",
    reportingYear ?? "",
    normalizedCycleType,
    normalizedBatchId,
    status ?? "",
    assignedOnlyYn === false ? "0" : "1",
  ].join("|");
};

const itemsOf = (payload) => {
  const data = dataOf(payload);
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data)) return data;
  return [];
};

const initialState = {
  workflow: {
    current: null,
    g0Status: null,
    postDmaScope: null,
  },

  onboarding: {
    metrics: [],
    assignments: [],
  },

  survey: {
    form: null,
    responseStatus: null,
    targets: null,
    importResult: null,
    recalculateResult: null,
    result: null,
  },

  approval: {
    projects: [],
    selectedProject: null,
    items: [],
    itemsContextKey: null,
    selectedItemDetail: null,
    lastMutationResult: null,
    lastMutationError: null,
  },

  rollup: {
    subsidiaries: [],
    scopePreview: null,
    requests: [],
    selectedRequestDetail: null,
    batchSources: [],
    activeBatchId: null,
    batchStatus: null,
  },
  rollupBaseline: {
    loading: false,
    saving: false,
    dataByBatchId: {},
    error: null,
  },
  // S5-B16: DMA 외부 시그널 단계(벤치마킹/미디어)의 진행상태·결과를 Redux로 통일 관리한다.
  dmaStages: {
    benchmark: { workflowStatus: null, result: null, loading: false, error: null },
    media: { workflowStatus: null, result: null, loading: false, error: null },
  },
  currentYear: localStorage.getItem("currentYear"),
  currentRunId: localStorage.getItem("currentRunId"),
  generateReportStatus: { loading: false, data: null, error: null },
  reportData: null,
  materialityResults: null,
  materialitySelectionProcess: null,
  finalizedSelection: null,
  loading: {
    workflow: false,
    onboarding: false,
    saveMetric: false,
    assignmentList: false,
    assignMetrics: false,
    unassignMetrics: false,
    approvalProjects: false,
    approvals: false,
    approvalDetail: false,
    subsidiaries: false,
    rollupScopePreview: false,
    createBatch: false,
    requests: false,
    rollupRequestDetail: false,
    rollupBatchSources: false,
    sendSource: false,
    batchStatus: false,
    calculateBatch: false,
    onboardingApprovalSubmit: false,
    onboardingApprovalReview: false,
    onboardingApprovalApprove: false,
    onboardingApprovalReject: false,
    initializePostDmaDisclosureScope: false,
    fetchActiveRollupBatch: false,
    ensureRollupResponseWorkspace: false,
    materialityResults: false,
    materialitySelectionProcess: false,
    finalizeSelectedSubIssues: false,
    surveyForm: false,
    surveyImport: false,
    surveyScorePreview: false,
    surveyRecalculate: false,
    surveyRetry: false,
    surveyResponseStatus: false,
    surveyTargets: false,
    surveyResult: false,
  },

  error: {
    workflow: null,
    onboarding: null,
    saveMetric: null,
    assignmentList: null,
    assignMetrics: null,
    unassignMetrics: null,
    approvalProjects: null,
    approvals: null,
    approvalDetail: null,
    subsidiaries: null,
    rollupScopePreview: null,
    createBatch: null,
    requests: null,
    rollupRequestDetail: null,
    rollupBatchSources: null,
    sendSource: null,
    batchStatus: null,
    calculateBatch: null,
    onboardingApprovalSubmit: null,
    onboardingApprovalReview: null,
    onboardingApprovalApprove: null,
    onboardingApprovalReject: null,
    initializePostDmaDisclosureScope: null,
    fetchActiveRollupBatch: null,
    ensureRollupResponseWorkspace: null,
    materialityResults: null,
    materialitySelectionProcess: null,
    finalizeSelectedSubIssues: null,
    surveyForm: null,
    surveyImport: null,
    surveyScorePreview: null,
    surveyRecalculate: null,
    surveyRetry: null,
    surveyResponseStatus: null,
    surveyTargets: null,
    surveyResult: null,
  },
};

export const fetchCurrentWorkflow = createAsyncThunk(
  "report/fetchCurrentWorkflow",
  async (
    { companyId, reportingYear = DEFAULT_REPORTING_YEAR } = {},
    { rejectWithValue }
  ) => {
    const params = companyId == null
      ? undefined
      : { companyId, reportingYear: normalizeReportingYear(reportingYear) };
    try {
      const res = await GET("/reportWorkflow/current", params);
      return rejectIfFailed(res, rejectWithValue, "보고서 워크플로우 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "보고서 워크플로우 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const probeCurrentWorkflow = createAsyncThunk(
  "report/probeCurrentWorkflow",
  async (
    { companyId, reportingYear = DEFAULT_REPORTING_YEAR } = {},
    { rejectWithValue }
  ) => {
    const params = companyId == null
      ? undefined
      : { companyId, reportingYear: normalizeReportingYear(reportingYear) };
    try {
      const res = await GET("/reportWorkflow/current", params);
      return rejectIfFailed(res, rejectWithValue, "보고서 워크플로우 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "보고서 워크플로우 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const startReportWorkflow = createAsyncThunk(
  "report/startReportWorkflow",
  async (payload, { rejectWithValue }) => {
    try {
      const normalizedPayload = {
        ...payload,
        reportingYear: normalizeReportingYear(payload?.reportingYear),
      };
      const res = await POST("/reportWorkflow/start", normalizedPayload);
      return rejectIfFailed(res, rejectWithValue, "보고서 워크플로우 시작에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "보고서 워크플로우 시작 중 오류가 발생했습니다.",
      });
    }
  }
);

export const resumeReportWorkflow = createAsyncThunk(
  "report/resumeReportWorkflow",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await POST(`/reportWorkflow/${runId}/resume`);
      return rejectIfFailed(res, rejectWithValue, "기존 프로젝트 재개에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "기존 프로젝트 재개 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchG0Status = createAsyncThunk(
  "report/fetchG0Status",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await GET(`/reportWorkflow/${runId}/g0-status`);
      return rejectIfFailed(res, rejectWithValue, "G0 상태 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "G0 상태 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchOnboardingMetrics = createAsyncThunk(
  "report/fetchOnboardingMetrics",
  async (
    {
      companyId,
      reportingYear = DEFAULT_REPORTING_YEAR,
      cycleType = "PRE_DMA_G0",
      metricId,
      batchId,
    },
    { rejectWithValue }
  ) => {
    const params = { companyId, reportingYear: normalizeReportingYear(reportingYear), cycleType };
    if (metricId) params.metricId = metricId;
    if (batchId) params.batchId = batchId;
    try {
      const res = normalizeDirectDtoResponse(await GET("/onboarding", params));
      return rejectIfFailed(res, rejectWithValue, "G0 프로필 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "G0 프로필 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const saveOnboardingMetric = createAsyncThunk(
  "report/saveOnboardingMetric",
  async ({ metricId, payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = normalizeDirectDtoResponse(await PATCH(`/onboarding/${metricId}`, normalizedPayload));
      return rejectIfFailed(res, rejectWithValue, "온보딩 지표 저장에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "온보딩 지표 저장 중 오류가 발생했습니다."),
      });
    }
  }
);

export const fetchOnboardingAssignments = createAsyncThunk(
  "report/fetchOnboardingAssignments",
  async (
    {
      companyId,
      reportingYear = DEFAULT_REPORTING_YEAR,
      cycleType = "PRE_DMA_G0",
      batchId,
    },
    { rejectWithValue }
  ) => {
    try {
      const params = { companyId, reportingYear: normalizeReportingYear(reportingYear), cycleType };
      if (batchId) params.batchId = batchId;
      const res = normalizeDirectDtoResponse(
        await GET(ONBOARDING_ASSIGNMENT_ROOT, params)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 담당자 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 담당자 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const bulkAssignOnboardingMetrics = createAsyncThunk(
  "report/bulkAssignOnboardingMetrics",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = normalizeDirectDtoResponse(
        await POST(`${ONBOARDING_ASSIGNMENT_ROOT}/bulk-assign`, normalizedPayload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 담당자 지정에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 담당자 지정 중 오류가 발생했습니다.",
      });
    }
  }
);

export const bulkUnassignOnboardingMetrics = createAsyncThunk(
  "report/bulkUnassignOnboardingMetrics",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = normalizeDirectDtoResponse(
        await POST(`${ONBOARDING_ASSIGNMENT_ROOT}/bulk-unassign`, normalizedPayload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 담당자 해제에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 담당자 해제 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchApprovalItems = createAsyncThunk(
  "report/fetchApprovalItems",
  async (
    {
      companyId,
      reportingYear = DEFAULT_REPORTING_YEAR,
      cycleType = "PRE_DMA_G0",
      status,
      assignedOnlyYn = true,
      batchId,
    },
    { rejectWithValue }
  ) => {
    const params = {
      companyId,
      reportingYear: normalizeReportingYear(reportingYear),
      cycleType,
      assignedOnlyYn,
    };
    if (status) params.status = status;
    if (batchId) params.batchId = batchId;
    try {
      const res = await GET(`${ONBOARDING_APPROVAL_API_ROOT}`, params);
      return rejectIfFailed(res, rejectWithValue, "승인 작업함 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "승인 작업함 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchOnboardingApprovalDetail = createAsyncThunk(
  "report/fetchOnboardingApprovalDetail",
  async (
    {
      companyId,
      reportingYear = DEFAULT_REPORTING_YEAR,
      metricId,
      cycleType = "PRE_DMA_G0",
      batchId,
    },
    { rejectWithValue }
  ) => {
    try {
      const params = { companyId, reportingYear: normalizeReportingYear(reportingYear), metricId, cycleType };
      if (batchId) params.batchId = batchId;
      const res = await GET(`${ONBOARDING_APPROVAL_API_ROOT}/detail`, params);
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 상세 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 승인 상세 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchApprovalProjects = createAsyncThunk(
  "report/fetchApprovalProjects",
  async ({ companyId }, { rejectWithValue }) => {
    try {
      const res = await GET("/reportWorkflow/projects", { companyId });
      return rejectIfFailed(res, rejectWithValue, "보고서 프로젝트 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "보고서 프로젝트 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupSubsidiaries = createAsyncThunk(
  "report/fetchRollupSubsidiaries",
  async (payload = {}, { rejectWithValue }) => {
    try {
      const params = buildRollupLookupParams(payload);
      const res = await GET(`${ROLLUP_API_ROOT}/subsidiaries`, params);
      return rejectIfFailed(res, rejectWithValue, "자회사 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: error?.message || "자회사 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupScopePreview = createAsyncThunk(
  "report/fetchRollupScopePreview",
  async (payload = {}, { rejectWithValue }) => {
    try {
      const params = buildRollupLookupParams(payload);
      const res = await GET(`${ROLLUP_API_ROOT}/scope-preview`, params);
      return rejectIfFailed(res, rejectWithValue, "롤업 범위 미리보기 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: error?.message || "롤업 범위 미리보기 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const createRollupBatch = createAsyncThunk(
  "report/createRollupBatch",
  async (payload, { rejectWithValue }) => {
    try {
      const body = buildRollupBatchBody(payload);
      const res = await POST(`${ROLLUP_API_ROOT}/batches`, body);
      return rejectIfFailed(res, rejectWithValue, "자회사 데이터 요청에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: error?.message || "자회사 데이터 요청 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchActiveRollupBatch = createAsyncThunk(
  "report/fetchActiveRollupBatch",
  async (payload, { rejectWithValue }) => {
    try {
      const params = buildRollupLookupParams(payload);
      const res = await GET(`${ROLLUP_API_ROOT}/batches/active`, params);
      return rejectIfFailed(res, rejectWithValue, "진행 중인 롤업 배치 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message:
          error?.message ||
          "진행 중인 롤업 배치 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const initializePostDmaDisclosureScope = createAsyncThunk(
  "report/initializePostDmaDisclosureScope",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await POST(`${REPORT_WORKFLOW_API_ROOT}/${runId}/post-dma-scope/initialize`);
      return rejectIfFailed(res, rejectWithValue, "이중중대성 평가 범위 초기화에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message:
          error?.message ||
          "이중중대성 평가 범위 초기화 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupRequests = createAsyncThunk(
  "report/fetchRollupRequests",
  async (payload = {}, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/requests`, payload);
      return rejectIfFailed(res, rejectWithValue, "자회사 요청 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "자회사 요청 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupRequestDetail = createAsyncThunk(
  "report/fetchRollupRequestDetail",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/requests/${batchId}`);
      return rejectIfFailed(res, rejectWithValue, "데이터 취합 요청 상세 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "데이터 취합 요청 상세 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const ensureRollupResponseWorkspace = createAsyncThunk(
  "report/ensureRollupResponseWorkspace",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/requests/${batchId}/workspace/ensure`);
      return rejectIfFailed(res, rejectWithValue, "작업 공간 생성에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "작업 공간 생성 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupBatchSources = createAsyncThunk(
  "report/fetchRollupBatchSources",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/${batchId}/sources`);
      return rejectIfFailed(res, rejectWithValue, "데이터 취합 자회사 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "데이터 취합 자회사 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const sendRollupSource = createAsyncThunk(
  "report/sendRollupSource",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/batches/${batchId}/sources/send`);
      return rejectIfFailed(res, rejectWithValue, "자회사 데이터 전송에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "자회사 데이터 전송 중 오류가 발생했습니다."),
      });
    }
  }
);

export const fetchRollupBatchStatus = createAsyncThunk(
  "report/fetchRollupBatchStatus",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/${batchId}/status`);
      return rejectIfFailed(res, rejectWithValue, "데이터 취합 배치 상태 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "데이터 취합 배치 상태 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const calculateRollupBatch = createAsyncThunk(
  "report/calculateRollupBatch",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/batches/${batchId}/calculate`);
      return rejectIfFailed(res, rejectWithValue, "데이터 취합에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "데이터 취합 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupBaselineRequirements = createAsyncThunk(
  "report/fetchRollupBaselineRequirements",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/${batchId}/baseline-requirements`);
      return rejectIfFailed(res, rejectWithValue, "전년도 기준값 요구 항목 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "전년도 기준값 요구 항목 조회 중 오류가 발생했습니다."),
      });
    }
  }
);

export const saveRollupBaselineValues = createAsyncThunk(
  "report/saveRollupBaselineValues",
  async ({ batchId, values }, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/batches/${batchId}/baseline-values`, { values });
      return rejectIfFailed(res, rejectWithValue, "전년도 기준값 저장에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "전년도 기준값 저장 중 오류가 발생했습니다."),
      });
    }
  }
);

// ── S5-B16: DMA 외부 시그널 단계(벤치마킹/미디어) thunk ──
// 컴포넌트(BenchMarking.jsx/Media.jsx)에서 직접 GET/POST/PUT/POST_FORM 을 호출하지 않고
// 모든 네트워크를 이 thunk 들로 흡수한다.

const DMA_WORKFLOW_TYPES = new Set(["BENCHMARK", "MEDIA", "SURVEY_FORM"]);

export const fetchDmaWorkflowStatus = createAsyncThunk(
  "report/fetchDmaWorkflowStatus",
  async ({ runId, workflowType }, { rejectWithValue }) => {
    try {
      const normalizedType = String(workflowType || "").trim().toUpperCase();
      if (!DMA_WORKFLOW_TYPES.has(normalizedType)) {
        return rejectWithValue({ status: false, message: `잘못된 workflowType: ${workflowType}` });
      }
      const res = await GET(`/materiality/workflow-status/${runId}/${normalizedType}`);
      return rejectIfFailed(res, rejectWithValue, "분석 진행 상태 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "분석 진행 상태 조회 중 오류가 발생했습니다."),
      });
    }
  }
);

export const uploadBenchmarkGroup = createAsyncThunk(
  "report/uploadBenchmarkGroup",
  async ({ fileType, companyName, files, page = "SR" }, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      (files || []).forEach((file) => formData.append("file", file));
      formData.append("fileType", fileType);
      formData.append("companyName", companyName);
      formData.append("page", page);
      const res = await POST_FORM("/benchmk", formData);
      return rejectIfFailed(res, rejectWithValue, "벤치마킹 파일 업로드에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "벤치마킹 파일 업로드 중 오류가 발생했습니다."),
      });
    }
  }
);

export const runBenchmarkAnalysis = createAsyncThunk(
  "report/runBenchmarkAnalysis",
  async ({ runId, fileNames, page = "SR", sourceStep = "benchmark", usePgPipeline, pgSrType, pgSrYear }, { rejectWithValue }) => {
    try {
      const body = {
        file: fileNames ?? [],
        page,
        esg_materiality_run_id: runId,
        source_step: sourceStep,
      };
      if (usePgPipeline != null) body.use_pg_pipeline = usePgPipeline;
      if (pgSrType != null) body.pg_sr_type = pgSrType;
      if (pgSrYear != null) body.pg_sr_year = pgSrYear;
      const res = await PUT("/benchmk", body);
      return rejectIfFailed(res, rejectWithValue, "벤치마킹 분석에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "벤치마킹 분석 중 오류가 발생했습니다."),
      });
    }
  }
);

export const fetchBenchmarkResult = createAsyncThunk(
  "report/fetchBenchmarkResult",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await GET(`/materiality/benchmark/${runId}`);
      return rejectIfFailed(res, rejectWithValue, "벤치마킹 결과 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "벤치마킹 결과 조회 중 오류가 발생했습니다."),
      });
    }
  }
);

export const runMediaCrawlAndAnalyze = createAsyncThunk(
  "report/runMediaCrawlAndAnalyze",
  async ({ runId, sources, dateFrom, dateTo }, { rejectWithValue }) => {
    try {
      const res = await POST("/media/news/crawl-and-analyze", {
        runId,
        sources,
        dateFrom,
        dateTo,
      });
      return rejectIfFailed(res, rejectWithValue, "미디어 분석에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "미디어 분석 중 오류가 발생했습니다."),
      });
    }
  }
);

export const fetchMediaResult = createAsyncThunk(
  "report/fetchMediaResult",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await GET(`/materiality/media/${runId}`);
      return rejectIfFailed(res, rejectWithValue, "미디어 분석 결과 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "미디어 분석 결과 조회 중 오류가 발생했습니다."),
      });
    }
  }
);

export const submitOnboardingApproval = createAsyncThunk(
  "report/submitOnboardingApproval",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = await POST(`${ONBOARDING_APPROVAL_API_ROOT}/submit`, normalizedPayload);
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 요청에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "온보딩 승인 요청 중 오류가 발생했습니다."),
      });
    }
  }
);

export const reviewOnboardingApproval = createAsyncThunk(
  "report/reviewOnboardingApproval",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/review`,
        normalizeApprovalDecisionPayload(normalizedPayload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 검토에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "온보딩 승인 검토 중 오류가 발생했습니다."),
      });
    }
  }
);

export const approveOnboardingApproval = createAsyncThunk(
  "report/approveOnboardingApproval",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/approve`,
        normalizeApprovalDecisionPayload(normalizedPayload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 처리에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "온보딩 승인 처리 중 오류가 발생했습니다."),
      });
    }
  }
);

export const rejectOnboardingApproval = createAsyncThunk(
  "report/rejectOnboardingApproval",
  async ({ payload, batchId }, { rejectWithValue }) => {
    try {
      const normalizedPayload = attachExplicitBatchContext(payload, batchId);
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/reject`,
        normalizeApprovalDecisionPayload(normalizedPayload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 반려에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: apiErrorMessage(error, "온보딩 승인 반려 중 오류가 발생했습니다."),
      });
    }
  }
);

export const generateReport = createAsyncThunk(
  "report/generateReport",
  async ({ companyId, materialityRunId, year }, { rejectWithValue }) => {
    try {
      const res = await POST("/ai", { companyId, materialityRunId, year });
      return rejectIfFailed(res, rejectWithValue, "보고서 생성에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "보고서 생성 중 오류가 발생했습니다.",
      });
    }
  }
);

// ── DMA Result API ───────────────────────────────────────────────
// GET /materiality/results/{runId}  : DMA 통합 결과 조회
export const fetchMaterialityResults = createAsyncThunk(
  "report/fetchMaterialityResults",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await GET(`/materiality/results/${runId}`)
      );
      return rejectIfFailed(res, rejectWithValue, "DMA 결과 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "DMA 결과 조회 중 오류가 발생했습니다." });
    }
  }
);

// GET /materiality/selection-process/{runId}  : 후보군→최종 선정 과정 조회
export const fetchMaterialitySelectionProcess = createAsyncThunk(
  "report/fetchMaterialitySelectionProcess",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await GET(`/materiality/selection-process/${runId}`)
      );
      return rejectIfFailed(res, rejectWithValue, "선정 과정 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "선정 과정 조회 중 오류가 발생했습니다." });
    }
  }
);

// GET /materiality/survey/{runId}  : 설문 단계 결과(축 분리 점수) 조회
export const fetchMaterialitySurveyResult = createAsyncThunk(
  "report/fetchMaterialitySurveyResult",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await GET(`/materiality/survey/${runId}`)
      );
      return rejectIfFailed(res, rejectWithValue, "설문 결과 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 결과 조회 중 오류가 발생했습니다." });
    }
  }
);

// POST /materiality/results/{runId}/selected-sub-issues/finalize
export const finalizeSelectedSubIssues = createAsyncThunk(
  "report/finalizeSelectedSubIssues",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await POST(`/materiality/results/${runId}/selected-sub-issues/finalize`, {})
      );
      return rejectIfFailed(res, rejectWithValue, "최종 이슈 확정에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "최종 이슈 확정 중 오류가 발생했습니다." });
    }
  }
);

// ── Survey API ───────────────────────────────────────────────────
// GET /survey/form/{runId}
// form이 없을 때(404) Network.js는 {status:false}를 반환하므로 rejected 대신 null fulfilled로 처리
export const fetchSurveyForm = createAsyncThunk(
  "report/fetchSurveyForm",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const raw = await GET(`/survey/form/${runId}`);
      if (raw?.status === false) {
        return { success: true, data: null };
      }
      return normalizeDirectDtoResponse(raw);
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 URL 정보를 불러오지 못했습니다." });
    }
  }
);

// POST /survey/form/{runId}/retry
export const retrySurveyForm = createAsyncThunk(
  "report/retrySurveyForm",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await POST(`/survey/form/${runId}/retry`, {}));
      return rejectIfFailed(res, rejectWithValue, "설문 URL 재시도에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 URL 재시도에 실패했습니다." });
    }
  }
);

// POST /survey/form/{runId}/responses/import
export const importSurveyResponses = createAsyncThunk(
  "report/importSurveyResponses",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await POST(`/survey/form/${runId}/responses/import`, {}));
      return rejectIfFailed(res, rejectWithValue, "설문 응답 Import에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 응답 Import에 실패했습니다." });
    }
  }
);

// GET /survey/form/{runId}/scores/preview
export const previewSurveyScores = createAsyncThunk(
  "report/previewSurveyScores",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await GET(`/survey/form/${runId}/scores/preview`));
      return rejectIfFailed(res, rejectWithValue, "설문 점수 Preview 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 점수 Preview 조회에 실패했습니다." });
    }
  }
);

// POST /survey/form/{runId}/scores/recalculate
export const recalculateSurveyScores = createAsyncThunk(
  "report/recalculateSurveyScores",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await POST(`/survey/form/${runId}/scores/recalculate`, {}));
      return rejectIfFailed(res, rejectWithValue, "설문 점수 반영에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "설문 점수 반영에 실패했습니다." });
    }
  }
);

// GET /survey/form/{runId}/response-status
export const fetchSurveyResponseStatus = createAsyncThunk(
  "report/fetchSurveyResponseStatus",
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await GET(`/survey/form/${runId}/response-status`));
      return rejectIfFailed(res, rejectWithValue, "응답 현황을 불러오지 못했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "응답 현황을 불러오지 못했습니다." });
    }
  }
);

// PUT /survey/form/{runId}/response-targets
export const saveSurveyResponseTargets = createAsyncThunk(
  "report/saveSurveyResponseTargets",
  async ({ runId, targets }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await PUT(`/survey/form/${runId}/response-targets`, { targets }));
      return rejectIfFailed(res, rejectWithValue, "목표 인원 저장에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({ status: false, message: "목표 인원 저장에 실패했습니다." });
    }
  }
);

const setPending = (state, key) => {
  state.loading[key] = true;
  state.error[key] = null;
};

const setRejected = (state, key, action) => {
  state.loading[key] = false;
  state.error[key] = action.payload || action.error || null;
};

// S5-B16: workflowType(BENCHMARK/MEDIA) → dmaStages 키 매핑
const stageKeyForWorkflowType = (workflowType) => {
  const type = String(workflowType || "").trim().toUpperCase();
  if (type === "BENCHMARK") return "benchmark";
  if (type === "MEDIA") return "media";
  return null;
};

const setApprovalMutationPending = (state, key) => {
  setPending(state, key);
  state.approval.lastMutationError = null;
};

const setApprovalMutationFulfilled = (state, key, action) => {
  state.loading[key] = false;
  state.error[key] = null;
  state.approval.lastMutationResult = dataOf(action.payload);
  state.approval.lastMutationError = null;
};

const setApprovalMutationRejected = (state, key, action) => {
  setRejected(state, key, action);
  state.approval.lastMutationError = action.payload || action.error || null;
};

const reportSlice = createSlice({
  name: "report",
  initialState,
  reducers: {
    setCurruntYear: (state, action) => {
      const normalized = normalizeReportingYear(action.payload);
      localStorage.setItem("currentYear", normalized);
      state.currentYear = normalized;
    },
    setMaterialityRunId: (state, action) => {
      localStorage.setItem("currentRunId", action.payload);
      state.currentRunId = action.payload ?? null;
    },

    setActiveBatchId: (state, action) => {
      state.rollup.activeBatchId = action.payload ?? null;
    },

    clearRollupTransientState: (state) => {
      state.rollup.subsidiaries = [];
      state.rollup.scopePreview = null;
      state.rollup.selectedRequestDetail = null;
      state.rollup.batchSources = [];
      state.rollup.activeBatchId = null;
      state.rollup.batchStatus = null;
      state.loading.subsidiaries = false;
      state.loading.rollupScopePreview = false;
      state.loading.createBatch = false;
      state.loading.rollupBatchSources = false;
      state.loading.batchStatus = false;
      state.loading.fetchActiveRollupBatch = false;
      state.error.subsidiaries = null;
      state.error.rollupScopePreview = null;
      state.error.createBatch = null;
      state.error.rollupBatchSources = null;
      state.error.batchStatus = null;
      state.error.fetchActiveRollupBatch = null;
    },

    clearReportError: (state, action) => {
      const key = action.payload;
      if (key && Object.prototype.hasOwnProperty.call(state.error, key)) {
        state.error[key] = null;
      }
    },
    setReportParams: (state, action) => {
      // payload로 전달된 runId와 year를 전역 상태에 저장
      state.currentRunId = action.payload.runId;
      state.currentYear = action.payload.year;
    },

    resetReportState: (state) => {
      const year = state.currentYear || normalizeReportingYear(localStorage.getItem("currentYear"));
      const runId = state.currentRunId ?? localStorage.getItem("currentRunId") ?? null;
      return { ...initialState, currentYear: year, currentRunId: runId };
    },

    selectApprovalProject: (state, action) => {
      state.approval.selectedProject = action.payload ?? null;
      state.approval.items = [];
      state.approval.itemsContextKey = null;
      state.approval.selectedItemDetail = null;
      state.loading.approvals = false;
    },

    clearApprovalProject: (state) => {
      state.approval.selectedProject = null;
      state.approval.items = [];
      state.approval.itemsContextKey = null;
      state.approval.selectedItemDetail = null;
      state.loading.approvals = false;
    },

    clearApprovalDetail: (state) => {
      state.approval.selectedItemDetail = null;
    },

    clearSurveyState: (state) => {
      state.survey.form = null;
      state.survey.responseStatus = null;
      state.survey.targets = null;
      state.survey.importResult = null;
      state.survey.recalculateResult = null;
      state.survey.result = null;
      state.loading.surveyForm = false;
      state.loading.surveyImport = false;
      state.loading.surveyScorePreview = false;
      state.loading.surveyRecalculate = false;
      state.loading.surveyRetry = false;
      state.loading.surveyResponseStatus = false;
      state.loading.surveyTargets = false;
      state.error.surveyForm = null;
      state.error.surveyImport = null;
      state.error.surveyScorePreview = null;
      state.error.surveyRecalculate = null;
      state.error.surveyRetry = null;
      state.error.surveyResponseStatus = null;
      state.error.surveyTargets = null;
      state.loading.surveyResult = false;
      state.error.surveyResult = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCurrentWorkflow.pending, (state) => setPending(state, "workflow"))
      .addCase(fetchCurrentWorkflow.fulfilled, (state, action) => {
        state.loading.workflow = false;
        state.error.workflow = null;
        state.workflow.current = dataOf(action.payload);
      })
      .addCase(fetchCurrentWorkflow.rejected, (state, action) => setRejected(state, "workflow", action));

    builder
      .addCase(startReportWorkflow.pending, (state) => setPending(state, "workflow"))
      .addCase(startReportWorkflow.fulfilled, (state, action) => {
        state.loading.workflow = false;
        state.error.workflow = null;
        state.workflow.current = dataOf(action.payload);
      })
      .addCase(startReportWorkflow.rejected, (state, action) => setRejected(state, "workflow", action));

    builder
      .addCase(resumeReportWorkflow.pending, (state) => setPending(state, "workflow"))
      .addCase(resumeReportWorkflow.fulfilled, (state, action) => {
        state.loading.workflow = false;
        state.error.workflow = null;
        state.workflow.current = dataOf(action.payload);
      })
      .addCase(resumeReportWorkflow.rejected, (state, action) => setRejected(state, "workflow", action));

    builder
      .addCase(fetchG0Status.pending, (state) => setPending(state, "workflow"))
      .addCase(fetchG0Status.fulfilled, (state, action) => {
        state.loading.workflow = false;
        state.error.workflow = null;
        state.workflow.g0Status = dataOf(action.payload);
      })
      .addCase(fetchG0Status.rejected, (state, action) => setRejected(state, "workflow", action));

    builder
      .addCase(fetchOnboardingMetrics.pending, (state) => setPending(state, "onboarding"))
      .addCase(fetchOnboardingMetrics.fulfilled, (state, action) => {
        state.loading.onboarding = false;
        state.error.onboarding = null;
        state.onboarding.metrics = dataOf(action.payload)?.items || [];
      })
      .addCase(fetchOnboardingMetrics.rejected, (state, action) => {
        setRejected(state, "onboarding", action);
        state.onboarding.metrics = [];
      });

    builder
      .addCase(saveOnboardingMetric.pending, (state) => setPending(state, "saveMetric"))
      .addCase(saveOnboardingMetric.fulfilled, (state) => {
        state.loading.saveMetric = false;
        state.error.saveMetric = null;
      })
      .addCase(saveOnboardingMetric.rejected, (state, action) => setRejected(state, "saveMetric", action));

    builder
      .addCase(fetchOnboardingAssignments.pending, (state) => setPending(state, "assignmentList"))
      .addCase(fetchOnboardingAssignments.fulfilled, (state, action) => {
        state.loading.assignmentList = false;
        state.error.assignmentList = null;
        state.onboarding.assignments = itemsOf(action.payload);
      })
      .addCase(fetchOnboardingAssignments.rejected, (state, action) => {
        setRejected(state, "assignmentList", action);
        state.onboarding.assignments = [];
      });

    builder
      .addCase(bulkAssignOnboardingMetrics.pending, (state) => setPending(state, "assignMetrics"))
      .addCase(bulkAssignOnboardingMetrics.fulfilled, (state) => {
        state.loading.assignMetrics = false;
        state.error.assignMetrics = null;
      })
      .addCase(bulkAssignOnboardingMetrics.rejected, (state, action) => setRejected(state, "assignMetrics", action));

    builder
      .addCase(bulkUnassignOnboardingMetrics.pending, (state) => setPending(state, "unassignMetrics"))
      .addCase(bulkUnassignOnboardingMetrics.fulfilled, (state) => {
        state.loading.unassignMetrics = false;
        state.error.unassignMetrics = null;
      })
      .addCase(bulkUnassignOnboardingMetrics.rejected, (state, action) => setRejected(state, "unassignMetrics", action));

    builder
      .addCase(fetchApprovalProjects.pending, (state) => setPending(state, "approvalProjects"))
      .addCase(fetchApprovalProjects.fulfilled, (state, action) => {
        state.loading.approvalProjects = false;
        state.error.approvalProjects = null;
        state.approval.projects = itemsOf(action.payload);
      })
      .addCase(fetchApprovalProjects.rejected, (state, action) => {
        setRejected(state, "approvalProjects", action);
        state.approval.projects = [];
      });

    builder
      .addCase(fetchApprovalItems.pending, (state, action) => {
        setPending(state, "approvals");
        state.approval.itemsContextKey = approvalContextKeyOf(action.meta.arg);
        state.approval.items = [];
        state.approval.selectedItemDetail = null;
      })
      .addCase(fetchApprovalItems.fulfilled, (state, action) => {
        if (state.approval.itemsContextKey !== approvalContextKeyOf(action.meta.arg)) {
          return;
        }
        state.loading.approvals = false;
        state.error.approvals = null;
        state.approval.items = itemsOf(action.payload);
      })
      .addCase(fetchApprovalItems.rejected, (state, action) => {
        if (state.approval.itemsContextKey !== approvalContextKeyOf(action.meta.arg)) {
          return;
        }
        setRejected(state, "approvals", action);
        state.approval.items = [];
      });

    builder
      .addCase(fetchOnboardingApprovalDetail.pending, (state) => {
        setPending(state, "approvalDetail");
        state.approval.selectedItemDetail = null;
      })
      .addCase(fetchOnboardingApprovalDetail.fulfilled, (state, action) => {
        state.loading.approvalDetail = false;
        state.error.approvalDetail = null;
        state.approval.selectedItemDetail = dataOf(action.payload);
      })
      .addCase(fetchOnboardingApprovalDetail.rejected, (state, action) => {
        setRejected(state, "approvalDetail", action);
        state.approval.selectedItemDetail = null;
      });

    builder
      .addCase(fetchRollupSubsidiaries.pending, (state) => setPending(state, "subsidiaries"))
      .addCase(fetchRollupSubsidiaries.fulfilled, (state, action) => {
        state.loading.subsidiaries = false;
        state.error.subsidiaries = null;
        state.rollup.subsidiaries = itemsOf(action.payload);
      })
      .addCase(fetchRollupSubsidiaries.rejected, (state, action) => {
        setRejected(state, "subsidiaries", action);
        state.rollup.subsidiaries = [];
      });

    builder
      .addCase(fetchRollupScopePreview.pending, (state) => setPending(state, "rollupScopePreview"))
      .addCase(fetchRollupScopePreview.fulfilled, (state, action) => {
        state.loading.rollupScopePreview = false;
        state.error.rollupScopePreview = null;
        state.rollup.scopePreview = dataOf(action.payload);
      })
      .addCase(fetchRollupScopePreview.rejected, (state, action) => {
        setRejected(state, "rollupScopePreview", action);
        state.rollup.scopePreview = null;
      });

    builder
      .addCase(createRollupBatch.pending, (state) => setPending(state, "createBatch"))
      .addCase(createRollupBatch.fulfilled, (state, action) => {
        state.loading.createBatch = false;
        state.error.createBatch = null;
        state.rollup.activeBatchId = dataOf(action.payload)?.batchId ?? state.rollup.activeBatchId;
      })
      .addCase(createRollupBatch.rejected, (state, action) => setRejected(state, "createBatch", action));

    builder
      // initializePostDmaDisclosureScope
      .addCase(initializePostDmaDisclosureScope.pending, (state) =>
        setPending(state, "initializePostDmaDisclosureScope")
      )
      .addCase(initializePostDmaDisclosureScope.fulfilled, (state, action) => {
        state.loading.initializePostDmaDisclosureScope = false;
        state.error.initializePostDmaDisclosureScope = null;
        state.workflow.postDmaScope = dataOf(action.payload);
      })
      .addCase(initializePostDmaDisclosureScope.rejected, (state, action) => {
        setRejected(state, "initializePostDmaDisclosureScope", action);
        state.workflow.postDmaScope = null;
      })

      // fetchActiveRollupBatch
      .addCase(fetchActiveRollupBatch.pending, (state) =>
        setPending(state, "fetchActiveRollupBatch")
      )
      .addCase(fetchActiveRollupBatch.fulfilled, (state, action) => {
        state.loading.fetchActiveRollupBatch = false;
        state.error.fetchActiveRollupBatch = null;

        const hasDataField =
          action.payload &&
          Object.prototype.hasOwnProperty.call(action.payload, "data");

        const data = hasDataField
          ? action.payload.data
          : action.payload;

        state.rollup.activeBatchId = data?.batchId ?? null;
        state.rollup.batchStatus = data || null;
      })
      .addCase(fetchActiveRollupBatch.rejected, (state, action) => {
        setRejected(state, "fetchActiveRollupBatch", action);
        state.rollup.activeBatchId = null;
        state.rollup.batchStatus = null;
        state.rollup.batchSources = [];
      })

      .addCase(fetchRollupRequests.pending, (state) => setPending(state, "requests"))
      .addCase(fetchRollupRequests.fulfilled, (state, action) => {
        state.loading.requests = false;
        state.error.requests = null;
        state.rollup.requests = itemsOf(action.payload);
      })
      .addCase(fetchRollupRequests.rejected, (state, action) => {
        setRejected(state, "requests", action);
        state.rollup.requests = [];
      });

    builder
      .addCase(fetchRollupRequestDetail.pending, (state) => setPending(state, "rollupRequestDetail"))
      .addCase(fetchRollupRequestDetail.fulfilled, (state, action) => {
        state.loading.rollupRequestDetail = false;
        state.error.rollupRequestDetail = null;
        const detail = dataOf(action.payload);
        state.rollup.selectedRequestDetail = detail;
        state.rollup.activeBatchId = detail?.batchId ?? state.rollup.activeBatchId;
      })
      .addCase(fetchRollupRequestDetail.rejected, (state, action) => {
        setRejected(state, "rollupRequestDetail", action);
        state.rollup.selectedRequestDetail = null;
      });

    builder
      .addCase(ensureRollupResponseWorkspace.pending, (state) => setPending(state, "ensureRollupResponseWorkspace"))
      .addCase(ensureRollupResponseWorkspace.fulfilled, (state, action) => {
        state.loading.ensureRollupResponseWorkspace = false;
        state.error.ensureRollupResponseWorkspace = null;
        state.rollup.selectedRequestDetail = dataOf(action.payload);
      })
      .addCase(ensureRollupResponseWorkspace.rejected, (state, action) => {
        setRejected(state, "ensureRollupResponseWorkspace", action);
      });

    builder
      .addCase(fetchRollupBatchSources.pending, (state) => setPending(state, "rollupBatchSources"))
      .addCase(fetchRollupBatchSources.fulfilled, (state, action) => {
        state.loading.rollupBatchSources = false;
        state.error.rollupBatchSources = null;
        state.rollup.batchSources = itemsOf(action.payload);
      })
      .addCase(fetchRollupBatchSources.rejected, (state, action) => {
        setRejected(state, "rollupBatchSources", action);
        state.rollup.batchSources = [];
      });

    builder
      .addCase(sendRollupSource.pending, (state) => setPending(state, "sendSource"))
      .addCase(sendRollupSource.fulfilled, (state) => {
        state.loading.sendSource = false;
        state.error.sendSource = null;
      })
      .addCase(sendRollupSource.rejected, (state, action) => setRejected(state, "sendSource", action));

    builder
      .addCase(fetchRollupBatchStatus.pending, (state) => setPending(state, "batchStatus"))
      .addCase(fetchRollupBatchStatus.fulfilled, (state, action) => {
        state.loading.batchStatus = false;
        state.error.batchStatus = null;
        state.rollup.batchStatus = dataOf(action.payload);
      })
      .addCase(fetchRollupBatchStatus.rejected, (state, action) => {
        setRejected(state, "batchStatus", action);
        state.rollup.batchStatus = null;
      });

    builder
      .addCase(calculateRollupBatch.pending, (state) => setPending(state, "calculateBatch"))
      .addCase(calculateRollupBatch.fulfilled, (state, action) => {
        state.loading.calculateBatch = false;
        state.error.calculateBatch = null;
        state.rollup.batchStatus = dataOf(action.payload) || state.rollup.batchStatus;
      })
      .addCase(calculateRollupBatch.rejected, (state, action) => setRejected(state, "calculateBatch", action));

    builder
      .addCase(fetchRollupBaselineRequirements.pending, (state) => {
        state.rollupBaseline.loading = true;
        state.rollupBaseline.error = null;
      })
      .addCase(fetchRollupBaselineRequirements.fulfilled, (state, action) => {
        state.rollupBaseline.loading = false;
        state.rollupBaseline.error = null;
        const data = dataOf(action.payload);
        const batchId = data?.batchId ?? action.meta.arg?.batchId;
        if (batchId != null) {
          state.rollupBaseline.dataByBatchId[batchId] = data;
        }
      })
      .addCase(fetchRollupBaselineRequirements.rejected, (state, action) => {
        state.rollupBaseline.loading = false;
        state.rollupBaseline.error = action.payload || action.error || null;
      });

    builder
      .addCase(saveRollupBaselineValues.pending, (state) => {
        state.rollupBaseline.saving = true;
        state.rollupBaseline.error = null;
      })
      .addCase(saveRollupBaselineValues.fulfilled, (state) => {
        state.rollupBaseline.saving = false;
        state.rollupBaseline.error = null;
      })
      .addCase(saveRollupBaselineValues.rejected, (state, action) => {
        state.rollupBaseline.saving = false;
        state.rollupBaseline.error = action.payload || action.error || null;
      });

    // S5-B16: DMA 외부 시그널 단계(벤치마킹/미디어) reducers
    builder
      .addCase(fetchDmaWorkflowStatus.fulfilled, (state, action) => {
        const dto = dataOf(action.payload);
        const type = String(dto?.workflowType || action.meta.arg?.workflowType || "")
          .trim()
          .toUpperCase();
        const stageKey = stageKeyForWorkflowType(type);
        if (stageKey) {
          state.dmaStages[stageKey].workflowStatus = dto;
        }
      })
      .addCase(fetchDmaWorkflowStatus.rejected, (state, action) => {
        const type = String(action.meta.arg?.workflowType || "").trim().toUpperCase();
        const stageKey = stageKeyForWorkflowType(type);
        if (stageKey) {
          state.dmaStages[stageKey].error = action.payload || action.error || null;
        }
      });

    builder
      .addCase(runBenchmarkAnalysis.pending, (state) => {
        state.dmaStages.benchmark.loading = true;
        state.dmaStages.benchmark.error = null;
      })
      .addCase(runBenchmarkAnalysis.fulfilled, (state) => {
        state.dmaStages.benchmark.loading = false;
      })
      .addCase(runBenchmarkAnalysis.rejected, (state, action) => {
        state.dmaStages.benchmark.loading = false;
        state.dmaStages.benchmark.error = action.payload || action.error || null;
      });

    builder
      .addCase(fetchBenchmarkResult.fulfilled, (state, action) => {
        state.dmaStages.benchmark.result = dataOf(action.payload);
        state.dmaStages.benchmark.error = null;
      })
      .addCase(fetchBenchmarkResult.rejected, (state, action) => {
        state.dmaStages.benchmark.error = action.payload || action.error || null;
      });

    builder
      .addCase(runMediaCrawlAndAnalyze.pending, (state) => {
        state.dmaStages.media.loading = true;
        state.dmaStages.media.error = null;
      })
      .addCase(runMediaCrawlAndAnalyze.fulfilled, (state) => {
        state.dmaStages.media.loading = false;
      })
      .addCase(runMediaCrawlAndAnalyze.rejected, (state, action) => {
        state.dmaStages.media.loading = false;
        state.dmaStages.media.error = action.payload || action.error || null;
      });

    builder
      .addCase(fetchMediaResult.fulfilled, (state, action) => {
        state.dmaStages.media.result = dataOf(action.payload);
        state.dmaStages.media.error = null;
      })
      .addCase(fetchMediaResult.rejected, (state, action) => {
        state.dmaStages.media.error = action.payload || action.error || null;
      });

    builder
      .addCase(submitOnboardingApproval.pending, (state) =>
        setApprovalMutationPending(state, "onboardingApprovalSubmit")
      )
      .addCase(submitOnboardingApproval.fulfilled, (state, action) =>
        setApprovalMutationFulfilled(state, "onboardingApprovalSubmit", action)
      )
      .addCase(submitOnboardingApproval.rejected, (state, action) =>
        setApprovalMutationRejected(state, "onboardingApprovalSubmit", action)
      );

    builder
      .addCase(reviewOnboardingApproval.pending, (state) =>
        setApprovalMutationPending(state, "onboardingApprovalReview")
      )
      .addCase(reviewOnboardingApproval.fulfilled, (state, action) =>
        setApprovalMutationFulfilled(state, "onboardingApprovalReview", action)
      )
      .addCase(reviewOnboardingApproval.rejected, (state, action) =>
        setApprovalMutationRejected(state, "onboardingApprovalReview", action)
      );

    builder
      .addCase(approveOnboardingApproval.pending, (state) =>
        setApprovalMutationPending(state, "onboardingApprovalApprove")
      )
      .addCase(approveOnboardingApproval.fulfilled, (state, action) =>
        setApprovalMutationFulfilled(state, "onboardingApprovalApprove", action)
      )
      .addCase(approveOnboardingApproval.rejected, (state, action) =>
        setApprovalMutationRejected(state, "onboardingApprovalApprove", action)
      );

    builder
      .addCase(rejectOnboardingApproval.pending, (state) =>
        setApprovalMutationPending(state, "onboardingApprovalReject")
      )
      .addCase(rejectOnboardingApproval.fulfilled, (state, action) =>
        setApprovalMutationFulfilled(state, "onboardingApprovalReject", action)
      )
      .addCase(rejectOnboardingApproval.rejected, (state, action) =>
        setApprovalMutationRejected(state, "onboardingApprovalReject", action)
      );
    builder
    .addCase(generateReport.pending, (state) => {
      state.generateReportStatus.loading = true;
      state.generateReportStatus.error = null;
    })
    .addCase(generateReport.fulfilled, (state, action) => {
      console.log("API 응답 확인:", action.payload);
      state.generateReportStatus.loading = false;
      state.generateReportStatus.data = action.payload; // 결과 저장
      state.reportData = action.payload; // 기존 데이터 저장소와 동기화
    })
    .addCase(generateReport.rejected, (state, action) => {
      state.generateReportStatus.loading = false;
      state.generateReportStatus.error = action.payload;
    });

    builder
      .addCase(fetchMaterialityResults.pending, (state) => setPending(state, "materialityResults"))
      .addCase(fetchMaterialityResults.fulfilled, (state, action) => {
        state.loading.materialityResults = false;
        state.error.materialityResults = null;
        state.materialityResults = dataOf(action.payload);
      })
      .addCase(fetchMaterialityResults.rejected, (state, action) => {
        setRejected(state, "materialityResults", action);
        state.materialityResults = null;
      });

    builder
      .addCase(fetchMaterialitySelectionProcess.pending, (state) => setPending(state, "materialitySelectionProcess"))
      .addCase(fetchMaterialitySelectionProcess.fulfilled, (state, action) => {
        state.loading.materialitySelectionProcess = false;
        state.error.materialitySelectionProcess = null;
        state.materialitySelectionProcess = dataOf(action.payload);
      })
      .addCase(fetchMaterialitySelectionProcess.rejected, (state, action) => {
        setRejected(state, "materialitySelectionProcess", action);
        state.materialitySelectionProcess = null;
      });

    builder
      .addCase(finalizeSelectedSubIssues.pending, (state) => setPending(state, "finalizeSelectedSubIssues"))
      .addCase(finalizeSelectedSubIssues.fulfilled, (state, action) => {
        state.loading.finalizeSelectedSubIssues = false;
        state.error.finalizeSelectedSubIssues = null;
        state.finalizedSelection = dataOf(action.payload);
      })
      .addCase(finalizeSelectedSubIssues.rejected, (state, action) => {
        setRejected(state, "finalizeSelectedSubIssues", action);
        state.finalizedSelection = null;
      });

    builder
      .addCase(fetchSurveyForm.pending, (state) => setPending(state, "surveyForm"))
      .addCase(fetchSurveyForm.fulfilled, (state, action) => {
        state.loading.surveyForm = false;
        state.error.surveyForm = null;
        state.survey.form = dataOf(action.payload);
      })
      .addCase(fetchSurveyForm.rejected, (state, action) => {
        setRejected(state, "surveyForm", action);
        state.survey.form = null;
      });

    builder
      .addCase(retrySurveyForm.pending, (state) => setPending(state, "surveyRetry"))
      .addCase(retrySurveyForm.fulfilled, (state, action) => {
        state.loading.surveyRetry = false;
        state.error.surveyRetry = null;
        state.survey.form = dataOf(action.payload);
      })
      .addCase(retrySurveyForm.rejected, (state, action) => setRejected(state, "surveyRetry", action));

    builder
      .addCase(importSurveyResponses.pending, (state) => setPending(state, "surveyImport"))
      .addCase(importSurveyResponses.fulfilled, (state, action) => {
        state.loading.surveyImport = false;
        state.error.surveyImport = null;
        state.survey.importResult = dataOf(action.payload);
      })
      .addCase(importSurveyResponses.rejected, (state, action) => {
        setRejected(state, "surveyImport", action);
        state.survey.importResult = null;
      });

    builder
      .addCase(previewSurveyScores.pending, (state) => setPending(state, "surveyScorePreview"))
      .addCase(previewSurveyScores.fulfilled, (state, action) => {
        state.loading.surveyScorePreview = false;
        state.error.surveyScorePreview = null;
        state.survey.scorePreview = dataOf(action.payload);
      })
      .addCase(previewSurveyScores.rejected, (state, action) => {
        setRejected(state, "surveyScorePreview", action);
        state.survey.scorePreview = null;
      });

    builder
      .addCase(recalculateSurveyScores.pending, (state) => setPending(state, "surveyRecalculate"))
      .addCase(recalculateSurveyScores.fulfilled, (state, action) => {
        state.loading.surveyRecalculate = false;
        state.error.surveyRecalculate = null;
        state.survey.recalculateResult = dataOf(action.payload);
      })
      .addCase(recalculateSurveyScores.rejected, (state, action) => {
        setRejected(state, "surveyRecalculate", action);
        state.survey.recalculateResult = null;
      });

    builder
      .addCase(fetchSurveyResponseStatus.pending, (state) => setPending(state, "surveyResponseStatus"))
      .addCase(fetchSurveyResponseStatus.fulfilled, (state, action) => {
        state.loading.surveyResponseStatus = false;
        state.error.surveyResponseStatus = null;
        state.survey.responseStatus = dataOf(action.payload);
      })
      .addCase(fetchSurveyResponseStatus.rejected, (state, action) => {
        setRejected(state, "surveyResponseStatus", action);
        state.survey.responseStatus = null;
      });

    builder
      .addCase(saveSurveyResponseTargets.pending, (state) => setPending(state, "surveyTargets"))
      .addCase(saveSurveyResponseTargets.fulfilled, (state, action) => {
        state.loading.surveyTargets = false;
        state.error.surveyTargets = null;
        const status = dataOf(action.payload);
        state.survey.responseStatus = status;
        state.survey.targets = status
          ? {
              employee: status.groups?.employee?.targetCount ?? 0,
              management: status.groups?.management?.targetCount ?? 0,
              external: status.groups?.external?.targetCount ?? 0,
            }
          : null;
      })
      .addCase(saveSurveyResponseTargets.rejected, (state, action) =>
        setRejected(state, "surveyTargets", action)
      );

    builder
      .addCase(fetchMaterialitySurveyResult.pending, (state) => setPending(state, "surveyResult"))
      .addCase(fetchMaterialitySurveyResult.fulfilled, (state, action) => {
        state.loading.surveyResult = false;
        state.error.surveyResult = null;
        state.survey.result = dataOf(action.payload);
      })
      .addCase(fetchMaterialitySurveyResult.rejected, (state, action) => {
        setRejected(state, "surveyResult", action);
        state.survey.result = null;
      });
  },
});

export const {
  clearApprovalDetail,
  clearApprovalProject,
  clearReportError,
  clearRollupTransientState,
  clearSurveyState,
  resetReportState,
  selectApprovalProject,
  setActiveBatchId,
  setCurruntYear,
  setMaterialityRunId,
  setReportParams,
} = reportSlice.actions;


// ── S5-B16: DMA 외부 시그널 단계 게이트/상태 selector ──
//
// 벤치마킹·미디어 분석은 G0/롤업(연결 재무기준)이 끝난 DMA 단계에서만 실행해야 한다.
// reportWorkflow.current 의 basisStatus(ENTITY_READY/CONSOLIDATED_READY)와 nextAction 으로
// 판정한다. (reportworkflows/service.resolveNextAction 에서 두 상태는 START_DMA 로 매핑된다.)
const DMA_READY_BASIS_STATUSES = new Set(["ENTITY_READY", "CONSOLIDATED_READY"]);
const PRE_DMA_NEXT_ACTIONS = new Set([
  "SELECT_REPORT_BASIS",
  "OPEN_G0_ONBOARDING",
  "REQUEST_ROLLUP",
  "WAIT_ROLLUP",
]);
const upperStr = (value) => String(value || "").trim().toUpperCase();

export const selectCurrentWorkflow = (state) => state.report.workflow.current;

export const selectCanRunDmaStage = (state) => {
  const workflow = state.report.workflow.current;
  if (!workflow) return false;
  const basisStatus = upperStr(workflow.basisStatus);
  const nextAction = upperStr(workflow.nextAction);
  const workflowStep = upperStr(workflow.workflowStep);
  if (PRE_DMA_NEXT_ACTIONS.has(nextAction)) return false;
  if (DMA_READY_BASIS_STATUSES.has(basisStatus)) return true;
  if (workflowStep === "DMA_READY") return true;
  return false;
};

export const selectDmaGateReason = (state) => {
  const workflow = state.report.workflow.current;
  const nextAction = upperStr(workflow?.nextAction);
  if (!workflow || nextAction === "SELECT_REPORT_BASIS") {
    return "보고서 기준(개별/연결)을 먼저 선택한 뒤 G0 온보딩을 완료해주세요.";
  }
  if (nextAction === "OPEN_G0_ONBOARDING") {
    return "G0 온보딩(재무 기준 데이터 입력)을 먼저 완료해주세요.";
  }
  if (nextAction === "REQUEST_ROLLUP" || nextAction === "WAIT_ROLLUP") {
    return "자회사 데이터 취합(롤업)이 완료된 후 분석을 실행할 수 있습니다.";
  }
  return "G0 재무 기준 준비가 완료된 후 분석을 실행할 수 있습니다.";
};

export const selectDmaStage = (stageKey) => (state) => state.report.dmaStages[stageKey];

export default reportSlice.reducer;
