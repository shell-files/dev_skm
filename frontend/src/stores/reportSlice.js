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

const rejectIfFailed = (res, rejectWithValue, fallbackMessage) => {
  if (isApiFailed(res)) {
    return rejectWithValue(toApiError(res, fallbackMessage));
  }
  return res;
};

const dataOf = (payload) => payload?.data ?? payload;

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
  },

  onboarding: {
    metrics: [],
    assignments: [],
  },

  approval: {
    projects: [],
    selectedProject: null,
    items: [],
  },

  rollup: {
    subsidiaries: [],
    requests: [],
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
    subsidiaries: false,
    createBatch: false,
    requests: false,
    sendSource: false,
    batchStatus: false,
    calculateBatch: false,
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
    subsidiaries: null,
    createBatch: null,
    requests: null,
    sendSource: null,
    batchStatus: null,
    calculateBatch: null,
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
      const res = await GET("/onboardingApproval", params);
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
  async ({ runId }, { rejectWithValue }) => {
    try {
      const res = await GET("/rollup/subsidiaries", { runId });
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

export const createRollupBatch = createAsyncThunk(
  "report/createRollupBatch",
  async (payload, { rejectWithValue }) => {
    try {
      const res = await POST("/rollup/batches", payload);
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

export const fetchRollupRequests = createAsyncThunk(
  "report/fetchRollupRequests",
  async (_, { rejectWithValue }) => {
    try {
      const res = await GET("/rollup/requests");
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

export const sendRollupSource = createAsyncThunk(
  "report/sendRollupSource",
  async ({ batchId }, { rejectWithValue }) => {
    try {
      const res = await POST(`/rollup/batches/${batchId}/sources/send`);
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
      const res = await GET(`/rollup/batches/${batchId}/status`);
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
      const res = await POST(`/rollup/batches/${batchId}/calculate`);
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

const setPending = (state, key) => {
  state.loading[key] = true;
  state.error[key] = null;
};

const setRejected = (state, key, action) => {
  state.loading[key] = false;
  state.error[key] = action.payload || action.error || null;
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
    },

    clearApprovalProject: (state) => {
      state.approval.selectedProject = null;
      state.approval.items = [];
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
      .addCase(createRollupBatch.pending, (state) => setPending(state, "createBatch"))
      .addCase(createRollupBatch.fulfilled, (state, action) => {
        state.loading.createBatch = false;
        state.error.createBatch = null;
        state.rollup.activeBatchId = dataOf(action.payload)?.batchId ?? state.rollup.activeBatchId;
      })
      .addCase(createRollupBatch.rejected, (state, action) => setRejected(state, "createBatch", action));

    builder
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
  },
});

export const {
  clearApprovalProject,
  clearReportError,
  resetReportState,
  selectApprovalProject,
  setActiveBatchId,
} = reportSlice.actions;

export default reportSlice.reducer;
