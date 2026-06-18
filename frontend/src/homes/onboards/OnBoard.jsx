import { useState, useEffect, useCallback, useMemo } from "react";
import { useLocation, useNavigate } from "react-router";
import { useDispatch, useSelector } from "react-redux";
import "@styles/onboarding1.css";
import { useAuth } from "@hooks/AuthContext.jsx";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import ReportBasisSelectModal from "@components/UI/ReportBasisSelectModal.jsx";
import ApprovalProjectSelectModal from "../mains/modal/ApprovalProjectSelectModal";
import OnboardingModalShell from "./modal/OnboardingModalShell";
import SubsidiaryRequestModal from "./modal/SubsidiaryRequestModal";
import SubsidiaryTransferModal from "./modal/SubsidiaryTransferModal";
import RollupSummaryPanel from "./RollupSummaryPanel";
import RollupInboxPanel from "./RollupInboxPanel";
import MetricAssignmentModal from "./modal/MetricAssignmentModal";
import PageHeader from '@components/UI/PageHeader';
import OnboardingStatCards from "./OnboardingStatCards";
import OnboardingWorkflowCta from "./OnboardingWorkflowCta";
import OnboardingMetricTable from "./OnboardingMetricTable";
import {
  calculateProfileStats,
  getAtomicId,
  getStatusInfo,
  hasAtomicValue,
  isEditableItem,
  resolveG0InputMode,
} from "./onboardingUtils";
import {
  DEFAULT_REPORTING_YEAR,
  bulkAssignOnboardingMetrics,
  fetchOnboardingAssignments,
  fetchCurrentWorkflow,
  fetchOnboardingMetrics,
  fetchRollupRequests,
  fetchActiveRollupBatch,
  fetchRollupBatchStatus,
  fetchRollupBatchSources,
  fetchRollupRequestDetail,
  ensureRollupResponseWorkspace,
  initializePostDmaDisclosureScope,
  clearRollupTransientState,
  resetReportState,
  saveOnboardingMetric,
  setActiveBatchId,
  submitOnboardingApproval,
  fetchApprovalProjects,
  selectApprovalProject,
} from "@stores/reportSlice";

const normalizeViewerRole = (role) => String(role || "").trim().toUpperCase();

const isAssignmentManagerRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return [
    "ADMIN",
    "ESG",
    "ESG_MANAGER",
    "MANAGER",
    "OWNER",
    "관리자",
    "ESG담당자",
    "ESG 담당자",
  ].includes(normalized);
};

const isEmployeeRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return ["EMPLOYEE", "ASSIGNEE", "부서담당자", "부서 담당자"].includes(normalized);
};

const isConsultantRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return ["CONSULTANT", "컨설턴트"].includes(normalized);
};

const isNoRunWorkflow = (workflow) => workflow?.workflowStep === "NO_RUN";

const isPendingSubsidiaryRequest = (request = {}) => {
  const requestStatus = String(request.requestStatus || "").trim().toUpperCase();
  const transferStatus = String(request.transferStatus || "").trim().toUpperCase();

  if (
    transferStatus === "SENT" ||
    transferStatus === "RECEIVED" ||
    requestStatus === "RECEIVED"
  ) {
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

const flattenOnboardingItems = (metrics = []) =>
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

const normalizeAssignmentStatus = (status) => String(status || "").trim().toUpperCase();

const normalizeInviteStatus = (status) => {
  const normalized = String(status || "").trim().toUpperCase();
  if (normalized === "승인대기" || normalized === "PENDING") return "PENDING";
  if (normalized === "승인완료" || normalized === "COMPLETED" || normalized === "ACCEPTED") return "COMPLETED";
  if (normalized === "승인취소" || normalized === "REVOKED" || normalized === "CANCELLED") return "REVOKED";
  return normalized;
};

const resolveOnboardingCycleType = (workflow, requestedCycleType, preferredCycleType) => {
  // 1. URL query override (QA/debug 전용)
  const requested = String(requestedCycleType || "").trim().toUpperCase();
  if (requested === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";
  if (requested === "PRE_DMA_G0") return "PRE_DMA_G0";

  // 2. navigation state hint (Result 등에서 navigate state로 전달)
  const preferred = String(preferredCycleType || "").trim().toUpperCase();
  if (preferred === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";
  if (preferred === "PRE_DMA_G0") return "PRE_DMA_G0";

  // 3. workflow가 명시적으로 반환한 currentCycleType
  const explicitCycle = String(
    workflow?.currentCycleType ||
    workflow?.cycleType ||
    workflow?.onboardingCycleType ||
    ""
  ).trim().toUpperCase();
  if (explicitCycle === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";

  // 4. nextAction 기반 판단 (POST_DMA 단계 nextAction이면 POST_DMA)
  const nextAction = String(workflow?.nextAction || "").trim().toUpperCase();
  if (
    [
      "POST_DMA_INPUT",
      "POST_DMA_ASSIGNMENT",
      "POST_DMA_DISCLOSURE",
      "REPORT_DISCLOSURE_INPUT",
      "REPORT_DISCLOSURE_ROLLUP",
    ].includes(nextAction)
  ) {
    return "POST_DMA_DISCLOSURE";
  }

  // 5. 복합 상태 체크: TABLE 선정 + POST_DMA cycle + scope 존재
  const selectionSource = String(workflow?.selectionSource || "").trim().toUpperCase();
  const fallbackYn = workflow?.fallbackYn === true;
  const selectedCount = Number(workflow?.selectedSubIssueCount || 0);
  const postDmaCycleId = workflow?.postDmaCycleId;
  const postDmaScopeMetricCount = Number(workflow?.postDmaScopeMetricCount || 0);

  if (
    selectionSource === "TABLE" &&
    !fallbackYn &&
    selectedCount >= 5 &&
    postDmaCycleId &&
    postDmaScopeMetricCount > 0
  ) {
    return "POST_DMA_DISCLOSURE";
  }

  return "PRE_DMA_G0";
};

const resolveRollupContext = (cycleType) => {
  const normalized = String(cycleType || "").trim().toUpperCase();
  if (normalized === "POST_DMA_DISCLOSURE") {
    return {
      rollupPurposeCode: "REPORT_DISCLOSURE",
      metricScopeCode: "SELECTED_DISCLOSURE",
    };
  }
  return {
    rollupPurposeCode: "DMA_PRECHECK",
    metricScopeCode: "G0_02_FINANCIAL_BASIS",
  };
};

const formatApiDetail = (detail) => {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .join("\n");
  }
  if (detail && typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return String(detail || "");
};

const mergeAssignmentIntoItems = (items = [], assignments = []) => {
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

const getProfileStatusFromItems = (items = []) => {
  const editableItems = items.filter((item) => isEditableItem(item));
  if (editableItems.length === 0) return "NOT_STARTED";
  const completedCount = editableItems.filter((item) => hasAtomicValue(item)).length;
  if (completedCount === 0) return "NOT_STARTED";
  if (completedCount < editableItems.length) return "IN_PROGRESS";
  return "COMPLETED";
};

const OnBoard = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { selectedCompany, user } = useAuth();

  const [isApprovalProjectModalOpen, setIsApprovalProjectModalOpen] = useState(false);
  const [filteredProjects, setFilteredProjects] = useState([]);
  const approvalProjectsFromStore = useSelector((state) => state.report?.approval?.projects ?? []);

  const location = useLocation();
  const companyId = selectedCompany?.company_id ?? selectedCompany?.companyId;
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  // const reportingYearQuery = searchParams.get("reportingYear");
  const reportingYearQuery = useSelector((state) => state.report.currentYear);
  const cycleTypeQuery = searchParams.get("cycleType");
  const preferredCycleType = location.state?.preferredCycleType ?? null;
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : null;

  const viewMode = searchParams.get("mode") === "ROLLUP_RESPONSE" ? "ROLLUP_RESPONSE" : "MY_PROJECT";
  const batchIdQuery = searchParams.get("batchId");
  const rollupResponseBatchId = useMemo(() => {
    if (viewMode !== "ROLLUP_RESPONSE") return undefined;
    const parsed = Number(batchIdQuery);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
  }, [viewMode, batchIdQuery]);

  const rawViewerRole = selectedCompany?.role ?? selectedCompany?.role_name ?? user?.role ?? user?.role_name ?? "guest";
  const viewerRole = rawViewerRole;
  const canManageAssignments = isAssignmentManagerRole(viewerRole);
  const canManageRollup = isAssignmentManagerRole(viewerRole);
  const isEmployeeViewer = isEmployeeRole(viewerRole);
  const isConsultantViewer = isConsultantRole(viewerRole);
  const workflow = useSelector((state) => state.report.workflow.current);
  const rawMetrics = useSelector((state) => state.report.onboarding.metrics);
  const rawAssignments = useSelector((state) => state.report.onboarding.assignments);
  const activeBatchId = useSelector((state) => state.report.rollup.activeBatchId);
  const requests = useSelector((state) => state.report.rollup.requests);
  const selectedRequestDetail = useSelector((state) => state.report.rollup.selectedRequestDetail);
  const activeReportingYear = viewMode === "ROLLUP_RESPONSE" ? (selectedRequestDetail?.reportingYear || reportingYear) : reportingYear;
  const loadingWorkflow = useSelector((state) => state.report.loading.workflow);
  const loadingG0 = useSelector((state) => state.report.loading.onboarding);
  const assigningMetrics = useSelector((state) => state.report.loading.assignMetrics);
  const workflowErrorPayload = useSelector((state) => state.report.error.workflow);
  const g0ErrorPayload = useSelector((state) => state.report.error.onboarding);

  const displayWorkflow = workflow;
  const activeCycleType = useMemo(
    () => {
      if (viewMode === "ROLLUP_RESPONSE") return "ROLLUP_RESPONSE";
      return resolveOnboardingCycleType(displayWorkflow, cycleTypeQuery, preferredCycleType);
    },
    [viewMode, displayWorkflow, cycleTypeQuery, preferredCycleType]
  );
  const activeRollupContext = useMemo(
    () => resolveRollupContext(activeCycleType),
    [activeCycleType]
  );
  const modalRollupPurposeCode =
    activeCycleType === "POST_DMA_DISCLOSURE"
      ? "REPORT_DISCLOSURE"
      : activeRollupContext.rollupPurposeCode;
  const modalMetricScopeCode =
    activeCycleType === "POST_DMA_DISCLOSURE"
      ? "SELECTED_DISCLOSURE"
      : activeRollupContext.metricScopeCode;
  const expectedPostDmaCycleId = Number(displayWorkflow?.postDmaCycleId || 0) || null;
  const isConsolidatedRollupContext =
    viewMode === "MY_PROJECT" &&
    displayWorkflow?.reportBasisType === "CONSOLIDATED" &&
    (activeCycleType === "PRE_DMA_G0" || activeCycleType === "POST_DMA_DISCLOSURE");
  const shouldShowRollupPanel = canManageRollup && isConsolidatedRollupContext;
  const workflowRunId = displayWorkflow?.runId;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isBasisModalOpen, setIsBasisModalOpen] = useState(false);
  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const [activeSourceCycleId, setActiveSourceCycleId] = useState(null);

  // New States for UI-1 & UI-2
  const [selectedMetricIds, setSelectedMetricIds] = useState([]);
  const [isAssignmentModalOpen, setIsAssignmentModalOpen] = useState(false);
  const [assignmentMode, setAssignmentMode] = useState('single');
  const [assignmentTargetIds, setAssignmentTargetIds] = useState([]);

  const currentUserId = user?.id ?? user?.user_id ?? user?.userId;

  const g0Items = useMemo(() => {
    const flattened = mergeAssignmentIntoItems(
      flattenOnboardingItems(rawMetrics),
      rawAssignments
    ).map((item) => ({
      ...item,
      selfAssignedYn: isEmployeeViewer
        ? true
        : (
          item.assigneeUserId != null &&
          currentUserId != null &&
          Number(item.assigneeUserId) === Number(currentUserId)
        ),
    }));

    return flattened;
  }, [rawMetrics, rawAssignments, currentUserId, isEmployeeViewer]);



  const [selectedSubIssue, setSelectedSubIssue] = useState("");

  const filteredG0ItemsForUser = useMemo(() => {
    let items = g0Items;
    if (viewMode === "ROLLUP_RESPONSE" && isEmployeeViewer) {
      items = items.filter((item) => item.selfAssignedYn === true);
    }

    if (viewMode === "ROLLUP_RESPONSE" && rollupResponseBatchId) {
      const actionableIds = selectedRequestDetail?.actionableInputMetricIds || [];
      items = items.filter((item) => actionableIds.includes(item.metricId));
    }
    return items;
  }, [g0Items, viewMode, isEmployeeViewer, rollupResponseBatchId, selectedRequestDetail]);

  const uniqueSubIssues = useMemo(() => {
    const issues = new Set();
    filteredG0ItemsForUser.forEach((item) => {
      if (item.subIssueName) {
        issues.add(item.subIssueName);
      }
    });
    return Array.from(issues);
  }, [filteredG0ItemsForUser]);

  useEffect(() => {
    if (selectedSubIssue && !uniqueSubIssues.includes(selectedSubIssue)) {
      setSelectedSubIssue("");
    }
  }, [uniqueSubIssues, selectedSubIssue]);

  const activeSubIssue = selectedSubIssue || (uniqueSubIssues.length > 0 ? uniqueSubIssues[0] : "");

  const filteredG0Items = useMemo(() => {
    if (!activeSubIssue) return filteredG0ItemsForUser;
    return filteredG0ItemsForUser.filter((item) => item.subIssueName === activeSubIssue);
  }, [filteredG0ItemsForUser, activeSubIssue]);

  const g0ProfileStatus = useMemo(() => getProfileStatusFromItems(filteredG0ItemsForUser), [filteredG0ItemsForUser]);
  const hasPendingSubsidiaryRequest = useMemo(
    () => requests.some(isPendingSubsidiaryRequest),
    [requests]
  );
  const hasAnySubsidiaryRequest = useMemo(
    () => requests.length > 0,
    [requests]
  );
  const workflowError = workflowErrorPayload?.message || null;
  const g0Error = g0ErrorPayload?.message || null;

  const displayWorkflowError = workflowError;
  const displayG0Error = g0Error;
  const isRollupResponseReadOnly = useMemo(() => {
    const transferStatus = String(
      selectedRequestDetail?.transferStatus ||
      selectedRequestDetail?.sourceStatus?.transferStatus ||
      ""
    ).trim().toUpperCase();
    return transferStatus === "SENT" || transferStatus === "RECEIVED";
  }, [selectedRequestDetail]);

  useEffect(() => {
    setActiveSourceCycleId(null);
    dispatch(clearRollupTransientState());
  }, [dispatch, companyId, reportingYear, workflowRunId, activeCycleType]);

  const initializeOnboarding = useCallback(async () => {
    if (!companyId) {
      dispatch(resetReportState());
      setActiveSourceCycleId(null);
      return;
    }

    try {
      if (viewMode === "ROLLUP_RESPONSE") {
        setActiveSourceCycleId(null);
        await dispatch(fetchRollupRequests({ includeSentYn: true, allPurposesYn: true })).unwrap();

        if (!rollupResponseBatchId) {
          return;
        }

        const batchId = rollupResponseBatchId;
        dispatch(setActiveBatchId(batchId));
        const detailRes = await dispatch(fetchRollupRequestDetail({ batchId })).unwrap();
        const detail = detailRes?.data || detailRes;
        const transferStatus = String(
          detail?.transferStatus ||
          detail?.sourceStatus?.transferStatus ||
          ""
        ).trim().toUpperCase();
        const readOnlyYn = transferStatus === "SENT" || transferStatus === "RECEIVED";
        let responseYear = detail?.reportingYear || reportingYear;

        if (!readOnlyYn) {
          try {
            const ensuredRes = await dispatch(ensureRollupResponseWorkspace({ batchId })).unwrap();
            const ensured = ensuredRes?.data || ensuredRes;
            responseYear = ensured?.reportingYear || responseYear;
          } catch (ensureError) {
            console.warn("[ROLLUP_ENSURE] workspace ensure failed, treating as read-only:", ensureError?.message ?? ensureError);
          }
        }

        const metricId = searchParams.get("metricId");
        await dispatch(
          fetchOnboardingMetrics({ companyId, reportingYear: responseYear, cycleType: "ROLLUP_RESPONSE", metricId, batchId })
        ).unwrap();

        if (canManageAssignments) {
          await dispatch(
            fetchOnboardingAssignments({ companyId, reportingYear: responseYear, cycleType: "ROLLUP_RESPONSE", batchId })
          ).unwrap();
        }
        return;
      }

      if (reportingYear === null) return;

      const workflowRes = await dispatch(
        fetchCurrentWorkflow({ companyId, reportingYear })
      ).unwrap();
      const nextWorkflow = workflowRes?.data || workflowRes;

      if (isNoRunWorkflow(nextWorkflow)) {
        setActiveSourceCycleId(null);
        setIsBasisModalOpen(true);
        return;
      }

      const nextCycleType = resolveOnboardingCycleType(nextWorkflow, cycleTypeQuery, preferredCycleType);
      const nextRollupContext = resolveRollupContext(nextCycleType);
      const runId = nextWorkflow.runId;
      let sourceCycleId = null;
      let initializedScope = null;

      if (nextCycleType === "POST_DMA_DISCLOSURE") {
        try {
          const initializedRes = await dispatch(
            initializePostDmaDisclosureScope({ runId })
          ).unwrap();
          initializedScope = initializedRes?.data || initializedRes;
        } catch (scopeError) {
          console.warn("[POST_DMA_SCOPE] initializePostDmaDisclosureScope failed, continuing:", scopeError?.message ?? scopeError);
        }
      }

      const metricId = searchParams.get("metricId");
      const metricsRes = await dispatch(
        fetchOnboardingMetrics({ companyId, reportingYear, cycleType: nextCycleType, metricId })
      ).unwrap();
      const metricsPayload = metricsRes?.data || metricsRes;

      if (nextCycleType === "POST_DMA_DISCLOSURE") {
        const resolvedPostDmaCycleId = Number(
          metricsPayload?.cycleId ||
          initializedScope?.cycleId ||
          initializedScope?.data?.cycleId ||
          nextWorkflow?.postDmaCycleId ||
          0
        );
        sourceCycleId =
          Number.isFinite(resolvedPostDmaCycleId) && resolvedPostDmaCycleId > 0
            ? resolvedPostDmaCycleId
            : null;
        console.log("[POST_DMA_SOURCE_CYCLE]", {
          workflowPostDmaCycleId: nextWorkflow?.postDmaCycleId,
          initializedCycleId: initializedScope?.cycleId || initializedScope?.data?.cycleId,
          onboardingCycleId: metricsPayload?.cycleId,
          resolvedSourceCycleId: sourceCycleId,
        });
      }

      setActiveSourceCycleId(sourceCycleId ?? null);

      const requiresSourceCycle =
        nextRollupContext.rollupPurposeCode === "REPORT_DISCLOSURE";
      const canFetchActiveBatch =
        nextWorkflow?.reportBasisType === "CONSOLIDATED" &&
        (!requiresSourceCycle || Boolean(sourceCycleId));

      if (canFetchActiveBatch) {
        try {
          const activeRes = await dispatch(
            fetchActiveRollupBatch({
              runId,
              sourceCycleId,
              rollupPurposeCode: nextRollupContext.rollupPurposeCode,
              metricScopeCode: nextRollupContext.metricScopeCode,
            })
          ).unwrap();

          const activeData = activeRes?.data || activeRes;

          if (activeData?.batchId) {
            await dispatch(
              fetchRollupBatchStatus({ batchId: activeData.batchId })
            ).unwrap();

            await dispatch(
              fetchRollupBatchSources({ batchId: activeData.batchId })
            ).unwrap();
          }
        } catch (activeBatchError) {
          console.error(activeBatchError);
          dispatch(clearRollupTransientState());
        }
      } else {
        dispatch(clearRollupTransientState());
      }

      if (canManageAssignments) {
        await dispatch(
          fetchOnboardingAssignments({ companyId, reportingYear, cycleType: nextCycleType })
        ).unwrap();
      }
    } catch (error) {
      console.error(error);
    }
  }, [companyId, cycleTypeQuery, preferredCycleType, reportingYear, location.search, viewMode, rollupResponseBatchId, canManageAssignments]);

  useEffect(() => {
    dispatch(resetReportState());
    Promise.resolve().then(() => initializeOnboarding());
  }, [
    dispatch,
    initializeOnboarding,
    location.state?.workflowStartedAt,
  ]);

  useEffect(() => {
    const handleFocus = () => {
      initializeOnboarding();
    };
    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [initializeOnboarding]);

  const profileStats = calculateProfileStats(filteredG0ItemsForUser);
  const handleCtaClick = () => {
    if (!displayWorkflow || isNoRunWorkflow(displayWorkflow)) {
      setIsBasisModalOpen(true);
      return;
    }

    switch (displayWorkflow.nextAction) {
      case "START_DMA":
        showDefaultAlert("진행", "이중중대성평가를 시작합니다.", "success");
        navigate("/benchmk");
        break;
      case "REQUEST_ROLLUP":
        setIsSubReqModalOpen(true);
        break;
      case "WAIT_ROLLUP":
        showDefaultAlert("대기", "자회사 데이터 수집 및 롤업 완료를 기다리고 있습니다.", "info");
        break;
      default:
        showDefaultAlert("안내", workflow.message || "데이터 입력 상태를 확인해 주세요.", "info");
    }
  };

  const handleOpenSubsidiaryRequest = () => {
    if (activeCycleType === "POST_DMA_DISCLOSURE" && !activeSourceCycleId) {
      showDefaultAlert(
        "확인 필요",
        "POST-DMA 지표 범위 cycle을 확인하지 못했습니다. 새로고침 후 다시 시도하세요.",
        "warning"
      );
      return;
    }
    if (
      activeCycleType === "POST_DMA_DISCLOSURE" &&
      expectedPostDmaCycleId &&
      Number(activeSourceCycleId) !== Number(expectedPostDmaCycleId)
    ) {
      showDefaultAlert(
        "확인 필요",
        "현재 프로젝트의 POST-DMA cycle과 요청 cycle이 일치하지 않습니다. 새로고침 후 다시 시도하세요.",
        "warning"
      );
      return;
    }
    setIsSubReqModalOpen(true);
  };

  const handleOpenTransferModal = async () => {
    if (!rollupResponseBatchId) return;

    try {
      await dispatch(
        fetchRollupRequestDetail({
          batchId: rollupResponseBatchId,
        })
      ).unwrap();

      setIsSubTransferModalOpen(true);
    } catch (error) {
      showDefaultAlert(
        "오류",
        error?.message ||
        "전송 가능 상태를 확인하지 못했습니다.",
        "error"
      );
    }
  };


  const handleSaveAndSubmit = async (values, files, status) => {
    if (!selectedItem || !companyId || isNoRunWorkflow(workflow)) return;
    if (isRollupResponseReadOnly) {
      showDefaultAlert("알림", "전송 완료된 요청은 읽기 전용입니다.", "info");
      return;
    }

    try {
      const metricId = selectedItem.parent?.metricId || selectedItem.metrics?.[0]?.metricId;
      if (!metricId) {
        showDefaultAlert("오류", "저장할 지표 정보를 찾을 수 없습니다.", "error");
        return;
      }
      const payload = {
        companyId,
        reportingYear: activeReportingYear,
        cycleType: activeCycleType,
        ...(activeCycleType === "ROLLUP_RESPONSE" ? { batchId: rollupResponseBatchId } : {}),
        values: selectedItem.metrics
          .filter((item) => isEditableItem(item))
          .map((item) => {
            const atomicMetricId = getAtomicId(item);
            const rawValue = values[atomicMetricId] ?? "";
            const trimmed = String(rawValue).trim();
            const numericYn =
              resolveG0InputMode(item) === "MANUAL_NUMBER" &&
              trimmed !== "" &&
              /^-?\d+(\.\d+)?$/.test(trimmed);

            return {
              metricId: item.metricId,
              atomicMetricId,
              valueText: numericYn ? null : trimmed || null,
              valueNumeric: numericYn ? Number(trimmed) : null,
              unit: item.unit || null,
            };
          }),
      };

      await dispatch(saveOnboardingMetric({ metricId, payload, batchId: rollupResponseBatchId })).unwrap();

      if (status === "DRAFT") {
        showDefaultAlert("완료", "임시저장이 완료되었습니다.", "success");
        setIsModalOpen(false);
        await initializeOnboarding();
        return;
      }

      try {
        await dispatch(
          submitOnboardingApproval({
            payload: {
              companyId,
              reportingYear: activeReportingYear,
              metricId,
              cycleType: activeCycleType,
              ...(activeCycleType === "ROLLUP_RESPONSE" ? { batchId: rollupResponseBatchId } : {}),
            },
            batchId: rollupResponseBatchId,
          })
        ).unwrap();
        showDefaultAlert("완료", "승인 요청이 완료되었습니다.", "success");
        setIsModalOpen(false);
        await initializeOnboarding();
      } catch (submitError) {
        console.error(submitError);
        let detail = formatApiDetail(
          submitError?.detail ??
          submitError?.error?.detail ??
          submitError?.message ??
          submitError?.error?.message ??
          ""
        );

        if (
          detail.includes("Metric assignment is required") ||
          detail.includes("Metric assignment must be assigned") ||
          detail.includes("Only the assigned user can input")
        ) {
          detail = "이 지표의 입력 담당자로 지정되지 않았습니다. 담당자 지정 상태를 확인해 주세요.";
        }

        showDefaultAlert(
          "오류",
          `입력값은 저장되었지만 승인 요청에 실패했습니다.${detail ? `\n${detail}` : ""}`,
          "error"
        );
        await initializeOnboarding();
      }
    } catch (error) {
      console.error(error);
      let detail = formatApiDetail(
        error?.detail ??
        error?.error?.detail ??
        error?.message ??
        error?.error?.message ??
        ""
      );
      if (
        detail.includes("Metric assignment is required") ||
        detail.includes("Metric assignment must be assigned") ||
        detail.includes("Only the assigned user can input")
      ) {
        showDefaultAlert("오류", "이 지표의 입력 담당자로 지정되지 않았습니다. 담당자 지정 상태를 확인해 주세요.", "error");
      } else {
        showDefaultAlert("오류", detail || "처리 중 오류가 발생했습니다.", "error");
      }
    }
  };

  // Callbacks for Phase UI-1 & UI-2
  const handleSelectMetric = (metricId) => {
    if (isRollupResponseReadOnly) return;
    setSelectedMetricIds(prev =>
      prev.includes(metricId) ? prev.filter(id => id !== metricId) : [...prev, metricId]
    );
  };

  const handleToggleSelectAll = (allMetricIds) => {
    if (isRollupResponseReadOnly) return;
    if (selectedMetricIds.length === allMetricIds.length) {
      setSelectedMetricIds([]);
    } else {
      setSelectedMetricIds(allMetricIds);
    }
  };

  const handleBulkAssignRequested = () => {
    if (isRollupResponseReadOnly) {
      showDefaultAlert("알림", "전송 완료된 요청은 읽기 전용입니다.", "info");
      return;
    }
    if (selectedMetricIds.length === 0) {
      showDefaultAlert("안내", "담당자를 지정할 지표를 먼저 선택해주세요.", "info");
      return;
    }
    setAssignmentMode('bulk');
    setAssignmentTargetIds(selectedMetricIds);
    setIsAssignmentModalOpen(true);
  };

  const handleRowAssignRequested = (metricId) => {
    if (isRollupResponseReadOnly) {
      showDefaultAlert("알림", "전송 완료된 요청은 읽기 전용입니다.", "info");
      return;
    }
    setAssignmentMode('single');
    setAssignmentTargetIds([metricId]);
    setIsAssignmentModalOpen(true);
  };

  const handleOpenApprovalProjectModal = useCallback(async () => {
    if (companyId) {
      try {
        const res = await dispatch(fetchApprovalProjects({ companyId })).unwrap();
        let projects = res?.data?.items || res?.items || [];

        if (isEmployeeRole(viewerRole) && !isAssignmentManagerRole(viewerRole)) {
          const assignedProjects = [];
          for (const proj of projects) {
            try {
              const metricsRes = await dispatch(fetchOnboardingMetrics({
                companyId,
                reportingYear: proj.reportingYear,
                cycleType: "PRE_DMA_G0"
              })).unwrap();
              const metrics = metricsRes?.data?.items ?? metricsRes?.items ?? [];
              if (metrics.length > 0) {
                assignedProjects.push(proj);
              }
            } catch (e) {
              // ignore
            }
          }
          setFilteredProjects(assignedProjects);
        } else {
          setFilteredProjects(projects);
        }
      } catch (e) {
        console.error(e);
        setFilteredProjects([]);
      }
    } else {
      setFilteredProjects(approvalProjectsFromStore);
    }
    setIsApprovalProjectModalOpen(true);
  }, [companyId, dispatch, viewerRole, approvalProjectsFromStore]);

  const handleSubmitAssignment = async (payload) => {
    if (isRollupResponseReadOnly) {
      showDefaultAlert("알림", "전송 완료된 요청은 읽기 전용입니다.", "info");
      return;
    }

    const metricIds = payload?.metricIds || assignmentTargetIds;
    if (!companyId || metricIds.length === 0) {
      showDefaultAlert("오류", "담당자를 지정할 metric_id를 선택해 주세요.", "error");
      return;
    }

    try {
      const response = await dispatch(
        bulkAssignOnboardingMetrics({
          payload: {
            companyId,
            reportingYear: activeReportingYear,
            cycleType: activeCycleType,
            ...(activeCycleType === "ROLLUP_RESPONSE" ? { batchId: rollupResponseBatchId } : {}),
            metricIds,
            assigneeName: payload.assigneeName,
            assigneeEmail: payload.assigneeEmail,
            dueDate: payload.submissionDueDate || null,
            sendInviteYn: true,
          },
          batchId: rollupResponseBatchId,
        })
      ).unwrap();
      const result = response?.data || response;

      await dispatch(fetchOnboardingMetrics({ companyId, reportingYear: activeReportingYear, cycleType: activeCycleType, batchId: rollupResponseBatchId })).unwrap();
      await dispatch(fetchOnboardingAssignments({ companyId, reportingYear: activeReportingYear, cycleType: activeCycleType, batchId: rollupResponseBatchId })).unwrap();

      setSelectedMetricIds([]);
      setAssignmentTargetIds([]);
      setIsAssignmentModalOpen(false);

      if (result?.warning) {
        showDefaultAlert("완료", `담당자 지정은 완료됐지만 메일 큐 처리 경고가 있습니다. ${result.warning}`, "warning");
      } else if (result?.inviteCreatedYn && result?.mailQueuedYn) {
        showDefaultAlert("완료", "담당자 지정 및 초대 메일 발송 요청이 완료되었습니다.", "success");
      } else {
        showDefaultAlert("완료", "담당자 지정이 완료되었습니다.", "success");
      }
    } catch (error) {
      console.error(error);
      showDefaultAlert("오류", error?.message || "담당자 지정 중 오류가 발생했습니다.", "error");
    }
  };

  if (loadingWorkflow && !workflow) {
    return (
      <div id="ob1-page">
        <div className="ob1-state-container">
          <div className="ob1-spinner" />
          <p className="ob1-state-text">온보딩 데이터를 불러오고 있습니다...</p>
        </div>
      </div>
    );
  }

  return (
    <div id="ob1-page">
      <div className="ob1-header-card" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '16px 24px',
        marginBottom: '24px',
        boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
      }}>

        {/* 왼쪽 그룹: 제목 */}
        <div className="ob1-header-left" style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <PageHeader
            category="온보딩 단계"
            title="온보딩"
            iconClass={viewMode === "ROLLUP_RESPONSE" ? "bi-chat-left-text-fill" : "bi-diagram-3-fill"}
          />

          {/* 구분선 */}
          <div style={{ width: '1px', height: '48px', background: '#e2e8f0', flexShrink: 0 }} />

          {/* 현재 상태 + 프로젝트 변경 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '6px', flexShrink: 0 }}>
            {(() => {
              const statusInfo = getStatusInfo(g0ProfileStatus);
              const total = profileStats.totalCount || 1;
              const percent = Math.round((profileStats.completedCount / total) * 100);
              const r = 9;
              const circ = 2 * Math.PI * r;
              const dash = (percent / 100) * circ;
              return (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#f0fdf4', border: '1px solid #d1fae5', borderRadius: '20px', padding: '5px 12px' }}>
                    <svg width="20" height="20" viewBox="0 0 20 20" style={{ flexShrink: 0 }}>
                      <circle cx="10" cy="10" r={r} fill="none" stroke="#d1fae5" strokeWidth="2.5" />
                      <circle cx="10" cy="10" r={r} fill="none" stroke="#16a34a" strokeWidth="2.5"
                        strokeDasharray={`${dash} ${circ}`}
                        strokeLinecap="round"
                        transform="rotate(-90 10 10)"
                      />
                    </svg>
                    <span style={{ color: '#15803d', fontWeight: '600', fontSize: '13px' }}>진행률 {percent}% · {statusInfo.label}</span>
                  </div>
                  <button
                    type="button"
                    style={{ padding: '5px 12px', fontSize: '13px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', cursor: 'pointer', color: '#374151', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '5px', width: '100%', justifyContent: 'center' }}
                    onClick={handleOpenApprovalProjectModal}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                      <path d="M3 22v-6h6" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                    </svg>
                    프로젝트 변경
                  </button>
                </>
              );
            })()}
          </div>
        </div>

        {/* 오른쪽: StatCards + CTA */}
        <div className="ob1-stat-cards-wrap" style={{ display: 'flex', alignItems: 'center', gap: '16px', flexShrink: 0 }}>
          <OnboardingStatCards stats={profileStats} />
          {!isNoRunWorkflow(displayWorkflow) && viewMode === "MY_PROJECT" && !canManageRollup && (
            <OnboardingWorkflowCta
              variant="action"
              loadingWorkflow={loadingWorkflow}
              workflow={displayWorkflow}
              isNoRunWorkflow={isNoRunWorkflow}
              onBasisModalOpen={() => setIsBasisModalOpen(true)}
              onCtaClick={handleCtaClick}
            />
          )}
          {viewMode === "ROLLUP_RESPONSE" && rollupResponseBatchId && (
            <div className="ob1-cta-container" style={{ display: 'flex', gap: '8px' }}>
              <button
                className="ob1-btn-cta ob1-btn-secondary"
                style={{
                  background: '#f1f5f9',
                  color: '#334155',
                  border: '1px solid #cbd5e1',
                  ...(isRollupResponseReadOnly ? { opacity: 0.5, cursor: 'not-allowed' } : {}),
                }}
                disabled={isRollupResponseReadOnly}
                onClick={() => {
                  if (isRollupResponseReadOnly) return;
                  dispatch(selectApprovalProject({
                    runId: workflow?.runId ?? null,
                    reportingYear: activeReportingYear,
                    cycleType: "ROLLUP_RESPONSE",
                    batchId: rollupResponseBatchId,
                    readOnlyYn: isRollupResponseReadOnly,
                    currentStageLabel: "자회사 데이터 승인"
                  }));
                  navigate(`/managerData?cycleType=ROLLUP_RESPONSE&batchId=${rollupResponseBatchId}`, { state: { skipProjectModal: true } });
                }}
              >
                데이터 승인
              </button>
              <button
                className="ob1-btn-cta"
                onClick={handleOpenTransferModal}
                disabled={loadingWorkflow || isRollupResponseReadOnly}
              >
                데이터 전송
              </button>
            </div>
          )}
        </div>

      </div>

      {viewMode === "ROLLUP_RESPONSE" && !batchIdQuery ? (
        <RollupInboxPanel requests={requests} onRefresh={initializeOnboarding} />
      ) : viewMode === "ROLLUP_RESPONSE" && !rollupResponseBatchId ? (
        <div className="ob1-empty-state">
          <p className="ob1-empty-title">받은 요청함의 Batch 정보가 없습니다.</p>
          <p className="ob1-empty-desc">요청함에서 다시 진입해 주세요.</p>
        </div>
      ) : (
        <div className="ob1-content-layout">
          <div className="ob1-sidebar-panel">
            <div className="ob1-sidebar-title">SUB-ISSUE</div>
            <ul className="ob1-sidebar-menu">
              {uniqueSubIssues.map((issue) => (
                <li
                  key={issue}
                  className={`ob1-sidebar-menu-item ${selectedSubIssue === issue ? "active" : ""}`}
                  onClick={() => setSelectedSubIssue(issue)}
                >
                  {issue}
                </li>
              ))}
            </ul>
          </div>

          <div className="ob1-main-area">
            {displayWorkflowError && (
              <div className="ob1-inline-error">
                <span className="ob1-error-icon">!</span>
                <span>{displayWorkflowError}</span>
              </div>
            )}

            {isNoRunWorkflow(displayWorkflow) ? (
              <OnboardingWorkflowCta
                variant="noRun"
                loadingWorkflow={loadingWorkflow}
                workflow={displayWorkflow}
                isNoRunWorkflow={isNoRunWorkflow}
                onBasisModalOpen={() => setIsBasisModalOpen(true)}
                onCtaClick={handleCtaClick}
              />
            ) : (
              <>
                {shouldShowRollupPanel && (
                  <RollupSummaryPanel
                    batchId={activeBatchId}
                    sourceCycleId={activeSourceCycleId}
                    workflow={displayWorkflow}
                    onCtaClick={handleOpenSubsidiaryRequest}
                    onStartDma={handleCtaClick}
                    onCalculated={() => initializeOnboarding()}
                    rollupPurposeCode={activeRollupContext.rollupPurposeCode}
                    metricScopeCode={activeRollupContext.metricScopeCode}
                    onSendSource={handleOpenTransferModal}
                  />
                )}

                <OnboardingMetricTable
                  g0Error={displayG0Error}
                  g0Items={filteredG0Items}
                  loadingG0={loadingG0}
                  selectedMetricIds={selectedMetricIds}
                  onSelectMetric={handleSelectMetric}
                  onToggleSelectAll={handleToggleSelectAll}
                  onBulkAssignRequested={handleBulkAssignRequested}
                  onOpenMetric={(item, subMetrics) => {
                    setSelectedItem({
                      parent: item,
                      metrics: subMetrics,
                    });
                    setIsModalOpen(true);
                  }}
                  onRetry={initializeOnboarding}
                  viewerRole={viewerRole}
                  canManageAssignments={canManageAssignments}
                  isEmployeeViewer={isEmployeeViewer}
                  isConsultantViewer={isConsultantViewer}
                  readOnlyYn={isRollupResponseReadOnly}
                />
              </>
            )}
          </div>
        </div>
      )}

      <OnboardingModalShell
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricItem={selectedItem?.parent}
        subMetrics={selectedItem?.metrics || []}
        onSaveAndSubmit={handleSaveAndSubmit}
        viewerRole={viewerRole}
        canManageAssignments={canManageAssignments}
        isConsultantViewer={isConsultantViewer}
        readOnlyYn={isRollupResponseReadOnly}
        onOpenAssignment={() => handleRowAssignRequested(selectedItem?.parent?.metricId)}
      />



      <MetricAssignmentModal
        isOpen={isAssignmentModalOpen}
        mode={assignmentMode}
        selectedMetricIds={assignmentTargetIds}
        isSubmitting={assigningMetrics}
        onClose={() => setIsAssignmentModalOpen(false)}
        onSubmitAssignment={handleSubmitAssignment}
      />

      <SubsidiaryRequestModal
        isOpen={isSubReqModalOpen}
        onClose={() => setIsSubReqModalOpen(false)}
        runId={displayWorkflow?.runId}
        reportingYear={reportingYear}
        sourceCycleId={activeSourceCycleId}
        expectedPostDmaCycleId={expectedPostDmaCycleId}
        rollupPurposeCode={modalRollupPurposeCode}
        metricScopeCode={modalMetricScopeCode}
        onRequested={async (batchId) => {
          if (batchId) {
            dispatch(setActiveBatchId(batchId));
          }
          setIsSubReqModalOpen(false);
          await initializeOnboarding();
        }}
      />

      <SubsidiaryTransferModal
        isOpen={isSubTransferModalOpen}
        onClose={() => setIsSubTransferModalOpen(false)}
        reportingYear={activeReportingYear}
        onTransferred={async () => {
          await initializeOnboarding();
        }}
      />

      <ReportBasisSelectModal
        isOpen={isBasisModalOpen}
        onClose={() => setIsBasisModalOpen(false)}
        companyId={companyId}
        reportingYear={reportingYear}
      />

      <ApprovalProjectSelectModal
        isOpen={isApprovalProjectModalOpen}
        projects={filteredProjects}
        selectedRunId={workflow?.runId ?? null}
        onSelectProject={(project) => {
          setIsApprovalProjectModalOpen(false);
          navigate(`/onb?reportingYear=${project.reportingYear}`);
        }}
        onClose={() => setIsApprovalProjectModalOpen(false)}
      />

    </div>
  );
};

export default OnBoard;
