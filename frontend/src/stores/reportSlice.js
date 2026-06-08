import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GET, POST, PATCH } from "@utils/Network";

export const DEFAULT_REPORTING_YEAR = new Date().getFullYear();
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

const ROLLUP_API_ROOT = "/api/v1/rollups";
const ONBOARDING_APPROVAL_API_ROOT = "/api/v1/onboarding-approvals";
const REPORT_WORKFLOW_API_ROOT = "/api/v1/report-workflow";

const rejectIfFailed = (res, rejectWithValue, fallbackMessage) => {
  if (isApiFailed(res)) {
    return rejectWithValue(toApiError(res, fallbackMessage));
  }
  return res;
};

const dataOf = (payload) => payload?.data ?? payload;

const normalizeApprovalDecisionPayload = (payload = {}) => {
  const normalized = { ...payload };
  if (normalized.commentText == null && normalized.comment != null) {
    normalized.commentText = normalized.comment;
  }
  delete normalized.comment;
  return normalized;
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

  approval: {
    projects: [],
    selectedProject: null,
    items: [],
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
  },
};

export const fetchCurrentWorkflow = createAsyncThunk(
  "report/fetchCurrentWorkflow",
  async (
    { companyId, reportingYear = DEFAULT_REPORTING_YEAR } = {},
    { rejectWithValue }
  ) => {
    const params = companyId == null ? undefined : { companyId, reportingYear };
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
    const params = companyId == null ? undefined : { companyId, reportingYear };
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
      const res = await POST("/reportWorkflow/start", payload);
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
    },
    { rejectWithValue }
  ) => {
    const params = { companyId, reportingYear, cycleType };
    if (metricId) params.metricId = metricId;
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
  async ({ metricId, payload }, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(await PATCH(`/onboarding/${metricId}`, payload));
      return rejectIfFailed(res, rejectWithValue, "온보딩 지표 저장에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 지표 저장 중 오류가 발생했습니다.",
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
    },
    { rejectWithValue }
  ) => {
    try {
      const res = normalizeDirectDtoResponse(
        await GET(ONBOARDING_ASSIGNMENT_ROOT, {
          companyId,
          reportingYear,
          cycleType,
        })
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
  async (payload, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await POST(`${ONBOARDING_ASSIGNMENT_ROOT}/bulk-assign`, payload)
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
  async (payload, { rejectWithValue }) => {
    try {
      const res = normalizeDirectDtoResponse(
        await POST(`${ONBOARDING_ASSIGNMENT_ROOT}/bulk-unassign`, payload)
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
    },
    { rejectWithValue }
  ) => {
    const params = {
      companyId,
      reportingYear,
      cycleType,
      assignedOnlyYn,
    };
    if (status) params.status = status;
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
    },
    { rejectWithValue }
  ) => {
    try {
      const res = await GET(`${ONBOARDING_APPROVAL_API_ROOT}/detail`, {
        companyId,
        reportingYear,
        metricId,
        cycleType,
      });
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
  async ({ runId, sourceCycleId, rollupPurposeCode, metricScopeCode } = {}, { rejectWithValue }) => {
    const params = {};
    if (runId != null) params.runId = runId;
    if (sourceCycleId != null) params.sourceCycleId = sourceCycleId;
    if (rollupPurposeCode) params.rollupPurposeCode = rollupPurposeCode;
    if (metricScopeCode) params.metricScopeCode = metricScopeCode;
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/subsidiaries`, params);
      return rejectIfFailed(res, rejectWithValue, "자회사 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "자회사 목록 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupScopePreview = createAsyncThunk(
  "report/fetchRollupScopePreview",
  async (payload = {}, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/scope-preview`, payload);
      return rejectIfFailed(res, rejectWithValue, "롤업 범위 미리보기 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "롤업 범위 미리보기 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const createRollupBatch = createAsyncThunk(
  "report/createRollupBatch",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/batches`, payload);
      return rejectIfFailed(res, rejectWithValue, "자회사 데이터 요청에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "자회사 데이터 요청 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchActiveRollupBatch = createAsyncThunk(
  "report/fetchActiveRollupBatch",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/active`, payload);
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
      return rejectIfFailed(res, rejectWithValue, "POST DMA 스코프 초기화에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message:
          error?.message ||
          "POST DMA 스코프 초기화 중 오류가 발생했습니다.",
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
      return rejectIfFailed(res, rejectWithValue, "롤업 요청 상세 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "롤업 요청 상세 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupBatchSources = createAsyncThunk(
  "report/fetchRollupBatchSources",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/${batchId}/sources`);
      return rejectIfFailed(res, rejectWithValue, "롤업 배치 자회사 목록 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "롤업 배치 자회사 목록 조회 중 오류가 발생했습니다.",
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
        message: "자회사 데이터 전송 중 오류가 발생했습니다.",
      });
    }
  }
);

export const fetchRollupBatchStatus = createAsyncThunk(
  "report/fetchRollupBatchStatus",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await GET(`${ROLLUP_API_ROOT}/batches/${batchId}/status`);
      return rejectIfFailed(res, rejectWithValue, "롤업 배치 상태 조회에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "롤업 배치 상태 조회 중 오류가 발생했습니다.",
      });
    }
  }
);

export const calculateRollupBatch = createAsyncThunk(
  "report/calculateRollupBatch",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await POST(`${ROLLUP_API_ROOT}/batches/${batchId}/calculate`);
      return rejectIfFailed(res, rejectWithValue, "롤업 계산에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "롤업 계산 중 오류가 발생했습니다.",
      });
    }
  }
);

export const submitOnboardingApproval = createAsyncThunk(
  "report/submitOnboardingApproval",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST(`${ONBOARDING_APPROVAL_API_ROOT}/submit`, payload);
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 요청에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 승인 요청 중 오류가 발생했습니다.",
      });
    }
  }
);

export const reviewOnboardingApproval = createAsyncThunk(
  "report/reviewOnboardingApproval",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/review`,
        normalizeApprovalDecisionPayload(payload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 검토에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 승인 검토 중 오류가 발생했습니다.",
      });
    }
  }
);

export const approveOnboardingApproval = createAsyncThunk(
  "report/approveOnboardingApproval",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/approve`,
        normalizeApprovalDecisionPayload(payload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 처리에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 승인 처리 중 오류가 발생했습니다.",
      });
    }
  }
);

export const rejectOnboardingApproval = createAsyncThunk(
  "report/rejectOnboardingApproval",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST(
        `${ONBOARDING_APPROVAL_API_ROOT}/reject`,
        normalizeApprovalDecisionPayload(payload)
      );
      return rejectIfFailed(res, rejectWithValue, "온보딩 승인 반려에 실패했습니다.");
    } catch (error) {
      console.error(error);
      return rejectWithValue({
        status: false,
        message: "온보딩 승인 반려 중 오류가 발생했습니다.",
      });
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
    setActiveBatchId: (state, action) => {
      state.rollup.activeBatchId = action.payload ?? null;
    },

    clearReportError: (state, action) => {
      const key = action.payload;
      if (key && Object.prototype.hasOwnProperty.call(state.error, key)) {
        state.error[key] = null;
      }
    },

    resetReportState: () => initialState,

    selectApprovalProject: (state, action) => {
      state.approval.selectedProject = action.payload ?? null;
      state.approval.items = [];
      state.approval.selectedItemDetail = null;
    },

    clearApprovalProject: (state) => {
      state.approval.selectedProject = null;
      state.approval.items = [];
      state.approval.selectedItemDetail = null;
    },

    clearApprovalDetail: (state) => {
      state.approval.selectedItemDetail = null;
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
      .addCase(fetchApprovalItems.pending, (state) => setPending(state, "approvals"))
      .addCase(fetchApprovalItems.fulfilled, (state, action) => {
        state.loading.approvals = false;
        state.error.approvals = null;
        state.approval.items = itemsOf(action.payload);
      })
      .addCase(fetchApprovalItems.rejected, (state, action) => {
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
        state.rollup.selectedRequestDetail = dataOf(action.payload);
      })
      .addCase(fetchRollupRequestDetail.rejected, (state, action) => {
        setRejected(state, "rollupRequestDetail", action);
        state.rollup.selectedRequestDetail = null;
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
  },
});

export const {
  clearApprovalDetail,
  clearApprovalProject,
  clearReportError,
  resetReportState,
  selectApprovalProject,
  setActiveBatchId,
} = reportSlice.actions;

export default reportSlice.reducer;
