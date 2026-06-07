import { useState, useEffect, useCallback, useMemo } from "react";
import { useLocation, useNavigate } from "react-router";
import { useDispatch, useSelector } from "react-redux";
import "@styles/onboarding1.css";
import { useAuth } from "@hooks/AuthContext.jsx";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import ReportBasisSelectModal from "@components/UI/ReportBasisSelectModal.jsx";
import OnboardingModalShell from "./modal/OnboardingModalShell";
import SubsidiaryRequestModal from "./modal/SubsidiaryRequestModal";
import SubsidiaryTransferModal from "./modal/SubsidiaryTransferModal";
import RollupSummaryPanel from "./RollupSummaryPanel";
import BatchActionBar from "@components/UI/BatchActionBar";
import MetricAssignmentModal from "./modal/MetricAssignmentModal";
import UiPreviewPanel from "@/dev/step12UiPreview/UiPreviewPanel";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import {
  mergeOnboardingFixtureRows,
  ONBOARDING_SCENARIOS,
  APPROVAL_SCENARIOS,
  ROLLUP_SCENARIOS,
  PREVIEW_WORKFLOW
} from "@/dev/step12UiPreview/fixtures";
import {
  calculateMetricStatus,
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
  bulkUnassignOnboardingMetrics,
  fetchOnboardingAssignments,
  fetchCurrentWorkflow,
  fetchOnboardingMetrics,
  fetchRollupRequests,
  fetchActiveRollupBatch,
  fetchRollupBatchStatus,
  fetchRollupBatchSources,
  initializePostDmaDisclosureScope,
  resetReportState,
  saveOnboardingMetric,
  setActiveBatchId,
} from "@stores/reportSlice";

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

const groupByMetric = (items = []) => {
  const grouped = [];
  const seen = new Set();
  items.forEach((item) => {
    if (!seen.has(item.metricId)) {
      seen.add(item.metricId);
      grouped.push(item);
    }
  });
  return grouped;
};

const flattenOnboardingItems = (metrics = []) =>
  metrics.flatMap((metric) =>
    (metric.atomicItems || []).map((atomic) => ({
      ...atomic,
      metricId: atomic.metricId || metric.metricId,
      metricName: atomic.metricName || metric.metricName,
      approvalPolicyCode: metric.approvalPolicyCode,
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

const resolveOnboardingCycleType = (workflow, requestedCycleType) => {
  const requested = String(requestedCycleType || "").trim().toUpperCase();
  if (requested === "POST_DMA_DISCLOSURE") return "POST_DMA_DISCLOSURE";
  if (requested === "PRE_DMA_G0") return "PRE_DMA_G0";

  const workflowValue = String(
    workflow?.cycleType ||
    workflow?.onboardingCycleType ||
    workflow?.currentCycleType ||
    ""
  ).trim().toUpperCase();
  return workflowValue === "POST_DMA_DISCLOSURE" ? "POST_DMA_DISCLOSURE" : "PRE_DMA_G0";
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

const DonutChart = ({ percent, color, emptyColor = "#f1f5f9" }) => {
  const safePercent = isNaN(percent) ? 0 : Math.max(0, Math.min(100, percent));
  return (
    <div style={{
      width: '40px', height: '40px', borderRadius: '50%',
      background: `conic-gradient(${color} ${safePercent}%, ${emptyColor} 0)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#fff' }}></div>
    </div>
  );
};

const OnboardingStatCards = ({ stats, g0ProfileStatus }) => {
  const statusInfo = getStatusInfo(g0ProfileStatus);
  const total = stats.totalCount || 1;
  const completedPercent = (stats.completedCount / total) * 100;
  const notStartedPercent = (stats.notStartedCount / total) * 100;

  return (
    <div className="ob1-cards">
      <div className="ob1-stat-card">
        <div className="ob1-stat-title">전체 데이터 입력 항목</div>
        <div className="ob1-stat-value">{stats.totalCount}</div>
      </div>
      <div className="ob1-stat-card" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div className="ob1-stat-title">입력 완료</div>
          <div className="ob1-stat-value success">{stats.completedCount}</div>
        </div>
        <DonutChart percent={completedPercent} color="#10b981" />
      </div>
      <div className="ob1-stat-card" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div className="ob1-stat-title">미입력</div>
          <div className="ob1-stat-value warning">{stats.notStartedCount}</div>
        </div>
        <DonutChart percent={notStartedPercent} color="#f97316" />
      </div>
      <div className="ob1-stat-card" style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0' }}>
        <div className="ob1-stat-title">프로필 상태</div>
        <div className="ob1-stat-value">
          <span className={`ob1-status-pill ${statusInfo.cls}`}>
            프로필 상태: {statusInfo.label}
          </span>
        </div>
      </div>
    </div>
  );
};

const OnboardingWorkflowCta = ({
  activeBatchId,
  hasPendingSubsidiaryRequest,
  loadingWorkflow,
  variant = "action",
  workflow,
  isNoRunWorkflow,
  onBasisModalOpen,
  onCalculated,
  onCtaClick,
  onReqModalOpen,
  onTransferModalOpen,
  rollupScenario,
}) => {
  if (variant === "noRun" || isNoRunWorkflow(workflow)) {
    return (
      <>
        <div className="ob1-empty-state">
          <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다.</p>
          <p className="ob1-empty-desc">
          먼저 보고서 워크플로우를 생성해 주세요.
          </p>
          <button type="button" className="ob1-btn-cta" onClick={onBasisModalOpen}>
            보고서 발행 기준 선택
          </button>
        </div>
        <div className="ob1-cta-container">
          <button className="ob1-btn-cta" onClick={onCtaClick} disabled={loadingWorkflow}>
            {loadingWorkflow ? "로딩 중..." : "발행 기준 선택"}
          </button>
        </div>
      </>
    );
  }

  if (variant === "top") {
    return (
      <>
        {hasPendingSubsidiaryRequest && (
          <div style={{ display: "flex", justifyContent: "flex-end", padding: "16px 24px 0 24px" }}>
            <button
              className="ob1-btn-input"
              onClick={onTransferModalOpen}
              style={{ padding: "8px 16px", background: "#f8fafc", color: "#1e293b", border: "1px solid #cbd5e1" }}
            >
              지주사 요청 확인 및 전송
            </button>
          </div>
        )}

        {(activeBatchId || STEP12_UI_FIXTURE_ENABLED) && (
          <RollupSummaryPanel
            batchId={activeBatchId}
            onCalculated={onCalculated}
            rollupScenario={rollupScenario}
            onManageRequests={() => onReqModalOpen?.()}
            onSendSource={() => onTransferModalOpen?.()}
          />
        )}
      </>
    );
  }

  return (
    <div className="ob1-cta-container">
      <button
        className="ob1-btn-cta"
        onClick={onCtaClick}
        disabled={loadingWorkflow}
      >
        {loadingWorkflow
          ? "로딩 중..."
          : !workflow
            ? "워크플로우 상태 확인 필요"
            : workflow.nextAction === "START_DMA"
              ? "이중중대성평가 진행하기"
              : workflow.nextAction === "REQUEST_ROLLUP"
                ? "자회사 데이터 요청하기"
                : workflow.nextAction === "WAIT_ROLLUP"
                  ? "롤업 대기"
                  : "입력 상태 확인"}
      </button>
    </div>
  );
};

const OnboardingMetricTable = ({
  g0Error,
  g0Items,
  loadingG0,
  selectedMetricIds,
  onSelectMetric,
  onToggleSelectAll,
  onRowAssignRequested,
  onBulkAssignRequested,
  onOpenMetric,
  onRetry,
  viewerRole,
}) => {
  if (g0Error) {
    return (
      <div className="ob1-inline-error">
        <span className="ob1-error-icon">!</span>
        <span>{g0Error}</span>
        <button type="button" className="ob1-btn-retry" onClick={onRetry}>
          다시 시도
        </button>
      </div>
    );
  }

  if (loadingG0 && g0Items.length === 0) {
    return (
      <div className="ob1-table-loading">
        <div className="ob1-spinner" />
        <p>경영일반 데이터를 불러오고 있습니다...</p>
      </div>
    );
  }

  if (g0Items.length === 0) {
    return (
      <div className="ob1-empty-state">
        <p className="ob1-empty-title">할당된 데이터가 없습니다.</p>
        <p className="ob1-empty-desc">보고서 워크플로우를 먼저 시작해 주세요.</p>
      </div>
    );
  }

  const groupedItems = groupByMetric(g0Items);
  const isAllSelected = groupedItems.length > 0 && selectedMetricIds.length === groupedItems.length;

  return (
    <div className="ob1-table-container">
      <table className="ob1-table">
        <colgroup>
          <col style={{ width: "44px" }} />
          <col style={{ width: "90px" }} />
          <col style={{ width: "auto" }} />
          <col style={{ width: "150px" }} />
          <col style={{ width: "110px" }} />
          <col style={{ width: "130px" }} />
          <col style={{ width: "110px" }} />
          <col style={{ width: "140px" }} />
        </colgroup>
        <thead className={selectedMetricIds.length > 0 ? "ob1-thead-selected" : ""}>
          {selectedMetricIds.length > 0 ? (
            <tr style={{ backgroundColor: "#e0e7ff" }}>
              <th style={{ width: "44px" }}>
                <input
                  type="checkbox"
                  className="ob1-checkbox"
                  checked={isAllSelected}
                  onChange={() => onToggleSelectAll(groupedItems.map(i => i.metricId))}
                />
              </th>
              <th colSpan="7">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: '#1e293b', fontSize: '14px' }}>
                    {selectedMetricIds.length}개 항목 선택됨
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="ob1-btn-batch-assign-header"
                      onClick={onBulkAssignRequested}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                      담당자 일괄 지정
                    </button>
                    <button
                      type="button"
                      className="ob1-btn-batch-cancel-header"
                      onClick={() => onToggleSelectAll([])}
                    >
                      ✕ 일괄 선택 해제
                    </button>
                  </div>
                </div>
              </th>
            </tr>
          ) : (
            <tr>
              <th style={{ width: "44px" }}>
                <input
                  type="checkbox"
                  className="ob1-checkbox"
                  aria-label="전체 선택"
                  checked={isAllSelected}
                  onChange={() => onToggleSelectAll(groupedItems.map(i => i.metricId))}
                />
              </th>
              <th>Metric ID</th>
              <th>입력 데이터 설명</th>
              <th>담당자</th>
              <th>제출 기한</th>
              <th>입력 상태</th>
              <th>승인 상태</th>
              <th>관리</th>
            </tr>
          )}
        </thead>
        <tbody>
          {groupedItems.map((item) => {
            const subMetrics = g0Items.filter((sub) => sub.metricId === item.metricId);
            const statusInfo = calculateMetricStatus(subMetrics);

            const inputStatusLabel = item.inputStatus || statusInfo.label;
            const inputStatusCls = inputStatusLabel === '작성중' ? 'draft' : inputStatusLabel === '제출완료' ? 'submitted' : inputStatusLabel === '입력 완료' ? 'approved' : 'not-started';

            const approvalStatusLabel = item.approvalStatus || '미제출';
            let approvalStatusCls = 'not-started';
            if (approvalStatusLabel === '검토대기') approvalStatusCls = 'draft';
            else if (approvalStatusLabel === '검토완료') approvalStatusCls = 'reviewed';
            else if (approvalStatusLabel === '승인완료') approvalStatusCls = 'approved';
            else if (approvalStatusLabel === '반려') approvalStatusCls = 'rejected';

            const isSelected = selectedMetricIds.includes(item.metricId);
            const isConsultant = viewerRole === '컨설턴트' || viewerRole === 'CONSULTANT';
            const isAssigned = item.assignmentStatus === 'ASSIGNED';
            const isInvitePending = item.inviteStatus === 'PENDING';
            const isSelfAssigned = item.selfAssignedYn === true;

            // Mock Date validation for UI-only
            const todayStr = new Date().toISOString().slice(0, 10);
            const isOverdue = item.submissionDueDate && item.submissionDueDate < todayStr;

            return (
              <tr key={item.metricId} className={isSelected ? "selected ob1-row-selected" : ""}>
                <td>
                  <input
                    type="checkbox"
                    className="ob1-checkbox"
                    aria-label={`${item.metricId} 선택`}
                    checked={isSelected}
                    onChange={() => onSelectMetric(item.metricId)}
                  />
                </td>
                <td>{item.metricId}</td>
                <td className="ob1-td-name">{item.metricName || item.atomicName || "-"}</td>

                <td>
                  <div className="ob1-assignee-cell">
                    {isSelfAssigned ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-status">본인 입력</span></>
                    ) : isInvitePending ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-email">{item.assigneeEmail}</span><span className="ob1-assignee-status pending">초대 대기</span></>
                    ) : isAssigned ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-email">{item.assigneeEmail}</span></>
                    ) : (
                      <span className="ob1-assignee-status unassigned">미지정</span>
                    )}
                  </div>
                </td>

                <td>
                  {item.submissionDueDate ? (
                    <div style={{ color: isOverdue ? '#ef4444' : '#334155', fontWeight: isOverdue ? 600 : 400 }}>
                      {item.submissionDueDate}
                      {isOverdue && <div style={{ fontSize: '0.75rem', marginTop: '2px' }}>기한 초과</div>}
                    </div>
                  ) : (
                    <span style={{ color: '#94a3b8' }}>미설정</span>
                  )}
                </td>

                <td>
                  <span className={`ob1-status-pill ${inputStatusCls}`}>
                    {inputStatusLabel}
                  </span>
                </td>

                <td>
                  <span className={`ob1-status-pill ${approvalStatusCls}`}>
                    {approvalStatusLabel}
                  </span>
                </td>

                <td>
                  <div className="ob1-td-actions" style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                    {isConsultant ? (
                      <button type="button" className="ob1-btn-input" onClick={() => onOpenMetric(item, subMetrics)}>상세 보기</button>
                    ) : (
                      <>
                        <button type="button" className="ob1-btn-input" onClick={() => onOpenMetric(item, subMetrics)}>입력</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const OnBoard = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { selectedCompany, user } = useAuth();
  const location = useLocation();
  const companyId = selectedCompany?.company_id ?? selectedCompany?.companyId;
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const reportingYearQuery = searchParams.get("reportingYear");
  const cycleTypeQuery = searchParams.get("cycleType");
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : DEFAULT_REPORTING_YEAR;

  // Preview States
  const [previewRole, setPreviewRole] = useState("ESG 담당자");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(ONBOARDING_SCENARIOS.UNASSIGNED);
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(APPROVAL_SCENARIOS.NO_CONSULTANT);
  const [previewRollupScenario, setPreviewRollupScenario] = useState(ROLLUP_SCENARIOS.PARENT_PENDING);

  const viewerRole = STEP12_UI_FIXTURE_ENABLED ? previewRole : (selectedCompany?.role ?? user?.role ?? "guest");

  const workflow = useSelector((state) => state.report.workflow.current);
  const rawMetrics = useSelector((state) => state.report.onboarding.metrics);
  const rawAssignments = useSelector((state) => state.report.onboarding.assignments);
  const activeBatchId = useSelector((state) => state.report.rollup.activeBatchId);
  const requests = useSelector((state) => state.report.rollup.requests);
  const loadingWorkflow = useSelector((state) => state.report.loading.workflow);
  const loadingG0 = useSelector((state) => state.report.loading.onboarding);
  const assigningMetrics = useSelector((state) => state.report.loading.assignMetrics);
  const workflowErrorPayload = useSelector((state) => state.report.error.workflow);
  const g0ErrorPayload = useSelector((state) => state.report.error.onboarding);

  const displayWorkflow = STEP12_UI_FIXTURE_ENABLED ? PREVIEW_WORKFLOW : workflow;
  const activeCycleType = useMemo(
    () => resolveOnboardingCycleType(displayWorkflow, cycleTypeQuery),
    [displayWorkflow, cycleTypeQuery]
  );

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isBasisModalOpen, setIsBasisModalOpen] = useState(false);
  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);

  // New States for UI-1 & UI-2
  const [selectedMetricIds, setSelectedMetricIds] = useState([]);
  const [isAssignmentModalOpen, setIsAssignmentModalOpen] = useState(false);
  const [assignmentMode, setAssignmentMode] = useState('single');
  const [assignmentTargetIds, setAssignmentTargetIds] = useState([]);

  const g0Items = useMemo(() => {
    const flattened = mergeAssignmentIntoItems(flattenOnboardingItems(rawMetrics), rawAssignments);
    if (STEP12_UI_FIXTURE_ENABLED) {
      return mergeOnboardingFixtureRows(flattened, previewOnboardingScenario);
    }
    return flattened;
  }, [rawMetrics, rawAssignments, previewOnboardingScenario]);

  const g0ProfileStatus = useMemo(() => getProfileStatusFromItems(g0Items), [g0Items]);
  const hasPendingSubsidiaryRequest = useMemo(
    () => requests.some(isPendingSubsidiaryRequest),
    [requests]
  );
  const workflowError = workflowErrorPayload?.message || null;
  const g0Error = g0ErrorPayload?.message || null;

  const displayWorkflowError = STEP12_UI_FIXTURE_ENABLED ? null : workflowError;
  const displayG0Error = STEP12_UI_FIXTURE_ENABLED ? null : g0Error;

  const initializeOnboarding = useCallback(async () => {
    if (!companyId) {
      dispatch(resetReportState());
      return;
    }

    try {
      const workflowRes = await dispatch(
        fetchCurrentWorkflow({ companyId, reportingYear })
      ).unwrap();
      const nextWorkflow = workflowRes?.data || workflowRes;

      if (isNoRunWorkflow(nextWorkflow)) {
        setIsBasisModalOpen(true);
        return;
      }

      const nextCycleType = resolveOnboardingCycleType(nextWorkflow, cycleTypeQuery);
      const runId = nextWorkflow.runId;
      let sourceCycleId;

      if (nextCycleType === "POST_DMA_DISCLOSURE") {
        const initializedRes = await dispatch(
          initializePostDmaDisclosureScope({ runId })
        ).unwrap();

        const initializedScope = initializedRes?.data || initializedRes;
        sourceCycleId = initializedScope?.cycleId;
      }

      if (nextWorkflow?.reportBasisType === "CONSOLIDATED") {
        const activeRes = await dispatch(
          fetchActiveRollupBatch({
            runId,
            sourceCycleId,
            rollupPurposeCode:
              nextCycleType === "POST_DMA_DISCLOSURE"
                ? "REPORT_DISCLOSURE"
                : "DMA_PRECHECK",
            metricScopeCode:
              nextCycleType === "POST_DMA_DISCLOSURE"
                ? "SELECTED_DISCLOSURE"
                : "G0_02_FINANCIAL_BASIS",
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
      }

      await dispatch(fetchRollupRequests({ includeSentYn: true, allPurposesYn: true })).unwrap();

      const metricId = new URLSearchParams(location.search).get("metricId");
      
      await dispatch(
        fetchOnboardingMetrics({ companyId, reportingYear, cycleType: nextCycleType, metricId })
      ).unwrap();
      await dispatch(
        fetchOnboardingAssignments({ companyId, reportingYear, cycleType: nextCycleType })
      ).unwrap();
    } catch (error) {
      console.error(error);
    }
  }, [companyId, cycleTypeQuery, dispatch, reportingYear, location.search]);

  useEffect(() => {
    dispatch(resetReportState());
    initializeOnboarding();
  }, [
    dispatch,
    initializeOnboarding,
    location.state?.workflowStartedAt,
  ]);

  const profileStats = calculateProfileStats(g0Items);
  const basisLabel =
    displayWorkflow?.reportBasisType === "CONSOLIDATED"
      ? "연결기준"
      : displayWorkflow?.reportBasisType === "ENTITY"
        ? "별도기준"
        : "미확정";

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

  const handleSaveAndSubmit = async (values, files, status) => {
    if (!selectedItem || !companyId || isNoRunWorkflow(workflow)) return;

    try {
      const metricId = selectedItem.parent?.metricId || selectedItem.metrics?.[0]?.metricId;
      if (!metricId) {
        showDefaultAlert("오류", "저장할 지표 정보를 찾을 수 없습니다.", "error");
        return;
      }
      const payload = {
        companyId,
        reportingYear,
        cycleType: activeCycleType,
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

      await dispatch(saveOnboardingMetric({ metricId, payload })).unwrap();

      showDefaultAlert(
        "완료",
        status === "DRAFT" ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.",
        "success"
      );
      setIsModalOpen(false);
      await initializeOnboarding();
    } catch (error) {
      console.error(error);
      showDefaultAlert("오류", "처리 중 오류가 발생했습니다.", "error");
    }
  };

  // Callbacks for Phase UI-1 & UI-2
  const handleSelectMetric = (metricId) => {
    setSelectedMetricIds(prev =>
      prev.includes(metricId) ? prev.filter(id => id !== metricId) : [...prev, metricId]
    );
  };

  const handleToggleSelectAll = (allMetricIds) => {
    if (selectedMetricIds.length === allMetricIds.length) {
      setSelectedMetricIds([]);
    } else {
      setSelectedMetricIds(allMetricIds);
    }
  };

  const handleBulkAssignRequested = () => {
    if (selectedMetricIds.length === 0) {
      showDefaultAlert("안내", "담당자를 지정할 지표를 먼저 선택해주세요.", "info");
      return;
    }
    setAssignmentMode('bulk');
    setAssignmentTargetIds(selectedMetricIds);
    setIsAssignmentModalOpen(true);
  };

  const handleRowAssignRequested = (metricId) => {
    setAssignmentMode('single');
    setAssignmentTargetIds([metricId]);
    setIsAssignmentModalOpen(true);
  };

  const handleSubmitAssignment = async (payload) => {
    if (STEP12_UI_FIXTURE_ENABLED) {
      showDefaultAlert("안내", "프리뷰 모드에서는 담당자 지정 API를 호출하지 않습니다.", "info");
      setIsAssignmentModalOpen(false);
      setSelectedMetricIds([]);
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
          companyId,
          reportingYear,
          cycleType: activeCycleType,
          metricIds,
          assigneeName: payload.assigneeName,
          assigneeEmail: payload.assigneeEmail,
          dueDate: payload.submissionDueDate || null,
          sendInviteYn: true,
        })
      ).unwrap();
      const result = response?.data || response;

      await dispatch(fetchOnboardingMetrics({ companyId, reportingYear, cycleType: activeCycleType })).unwrap();
      await dispatch(fetchOnboardingAssignments({ companyId, reportingYear, cycleType: activeCycleType })).unwrap();

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

  const handleBulkUnassignRequested = async () => {
    if (selectedMetricIds.length === 0) return;
    if (STEP12_UI_FIXTURE_ENABLED) {
      showDefaultAlert("안내", "프리뷰 모드에서는 담당자 해제 API를 호출하지 않습니다.", "info");
      return;
    }

    try {
      await dispatch(
        bulkUnassignOnboardingMetrics({
          companyId,
          reportingYear,
          cycleType: activeCycleType,
          metricIds: selectedMetricIds,
        })
      ).unwrap();

      await dispatch(fetchOnboardingMetrics({ companyId, reportingYear, cycleType: activeCycleType })).unwrap();
      await dispatch(fetchOnboardingAssignments({ companyId, reportingYear, cycleType: activeCycleType })).unwrap();

      setSelectedMetricIds([]);
      showDefaultAlert("완료", "선택한 지표의 담당자 지정이 해제되었습니다.", "success");
    } catch (error) {
      console.error(error);
      showDefaultAlert("오류", error?.message || "담당자 해제 중 오류가 발생했습니다.", "error");
    }
  };

  if (!STEP12_UI_FIXTURE_ENABLED && loadingWorkflow && !workflow) {
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
      <div className="ob1-header">
        <h1 className="ob1-title">온보딩 [{basisLabel}]</h1>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <OnboardingStatCards
          stats={profileStats}
          g0ProfileStatus={g0ProfileStatus}
        />
      </div>
      <div className="ob1-content-layout">
        <div className="ob1-sidebar-panel">
          <div className="ob1-sidebar-title">할당 항목</div>
          <ul className="ob1-sidebar-menu">
            <li className="ob1-sidebar-menu-item active">1. 경영일반 - G0</li>
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
              <OnboardingWorkflowCta
                variant="top"
                activeBatchId={activeBatchId}
                hasPendingSubsidiaryRequest={hasPendingSubsidiaryRequest}
                loadingWorkflow={loadingWorkflow}
                workflow={displayWorkflow}
                isNoRunWorkflow={isNoRunWorkflow}
                onCalculated={() => initializeOnboarding()}
                onCtaClick={handleCtaClick}
                onReqModalOpen={() => setIsSubReqModalOpen(true)}
                onTransferModalOpen={() => setIsSubTransferModalOpen(true)}
                rollupScenario={previewRollupScenario}
              />

              <OnboardingMetricTable
                g0Error={displayG0Error}
                g0Items={g0Items}
                loadingG0={STEP12_UI_FIXTURE_ENABLED ? false : loadingG0}
                selectedMetricIds={selectedMetricIds}
                onSelectMetric={handleSelectMetric}
                onToggleSelectAll={handleToggleSelectAll}
                onRowAssignRequested={handleRowAssignRequested}
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
              />
              <OnboardingWorkflowCta
                loadingWorkflow={loadingWorkflow}
                workflow={displayWorkflow}
                isNoRunWorkflow={isNoRunWorkflow}
                onCtaClick={handleCtaClick}
              />
            </>
          )}
        </div>
      </div>

      <OnboardingModalShell
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricItem={selectedItem?.parent}
        subMetrics={selectedItem?.metrics || []}
        onSaveAndSubmit={handleSaveAndSubmit}
        viewerRole={viewerRole}
        onOpenAssignment={() => handleRowAssignRequested(selectedItem?.parent?.metricId)}
      />

      <MetricAssignmentModal
        isOpen={isAssignmentModalOpen}
        mode={assignmentMode}
        selectedMetricIds={assignmentTargetIds}
        isSubmitting={!STEP12_UI_FIXTURE_ENABLED && assigningMetrics}
        onClose={() => setIsAssignmentModalOpen(false)}
        onSubmitAssignment={handleSubmitAssignment}
      />

      <SubsidiaryRequestModal
        isOpen={isSubReqModalOpen}
        onClose={() => setIsSubReqModalOpen(false)}
        runId={workflow?.runId}
        onRequested={async (batch) => {
          dispatch(setActiveBatchId(batch.batchId));
          setIsSubReqModalOpen(false);
          await initializeOnboarding();
        }}
      />

      <SubsidiaryTransferModal
        isOpen={isSubTransferModalOpen}
        onClose={() => setIsSubTransferModalOpen(false)}
        onTransferred={async (batchId) => {
          dispatch(setActiveBatchId(batchId));
          await initializeOnboarding();
        }}
      />

      <ReportBasisSelectModal
        isOpen={isBasisModalOpen}
        onClose={() => setIsBasisModalOpen(false)}
        companyId={companyId}
        reportingYear={reportingYear}
      />

      <UiPreviewPanel
        role={previewRole}
        onboardingScenario={previewOnboardingScenario}
        approvalScenario={previewApprovalScenario}
        rollupScenario={previewRollupScenario}
        onRoleChange={setPreviewRole}
        onOnboardingScenarioChange={setPreviewOnboardingScenario}
        onApprovalScenarioChange={setPreviewApprovalScenario}
        onRollupScenarioChange={setPreviewRollupScenario}
      />
    </div>
  );
};

export default OnBoard;
