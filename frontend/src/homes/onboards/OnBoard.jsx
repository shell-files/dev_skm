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
  fetchCurrentWorkflow,
  fetchOnboardingMetrics,
  fetchRollupRequests,
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

const getProfileStatusFromItems = (items = []) => {
  const editableItems = items.filter((item) => isEditableItem(item));
  if (editableItems.length === 0) return "NOT_STARTED";
  const completedCount = editableItems.filter((item) => hasAtomicValue(item)).length;
  if (completedCount === 0) return "NOT_STARTED";
  if (completedCount < editableItems.length) return "IN_PROGRESS";
  return "COMPLETED";
};

const OnboardingStatCards = ({ stats, g0ProfileStatus }) => {
  const statusInfo = getStatusInfo(g0ProfileStatus);

  return (
    <div className="ob1-cards">
      <div className="ob1-stat-card">
        <div className="ob1-stat-title">전체 데이터 입력 항목</div>
        <div className="ob1-stat-value">{stats.totalCount}</div>
      </div>
      <div className="ob1-stat-card">
        <div className="ob1-stat-title">입력 완료</div>
        <div className="ob1-stat-value success">{stats.completedCount}</div>
      </div>
      <div className="ob1-stat-card">
        <div className="ob1-stat-title">미입력</div>
        <div className="ob1-stat-value warning">{stats.notStartedCount}</div>
      </div>
      <div className="ob1-stat-card">
        <div className="ob1-stat-title">프로필 상태</div>
        <div className="ob1-stat-value">
          <span className={`ob1-status-pill ${statusInfo.cls}`}>
            {statusInfo.label}
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

  if (loadingG0) {
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
        <thead>
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
            <th style={{ width: "90px" }}>Metric ID</th>
            <th style={{ width: "auto" }}>지표명</th>
            <th style={{ width: "120px" }}>Sub-Issue</th>
            <th style={{ width: "170px" }}>담당자</th>
            <th style={{ width: "110px" }}>제출 기한</th>
            <th style={{ width: "90px" }}>입력 상태</th>
            <th style={{ width: "90px" }}>승인 상태</th>
            <th style={{ width: "180px" }}>관리</th>
          </tr>
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
              <tr key={item.metricId} className={isSelected ? "selected" : ""}>
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
                <td style={{ fontSize: "12px", color: "#64748b" }}>{item.subIssueName || item.sub_issue_name || item.subIssueCode || "-"}</td>
                
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
                        <button type="button" className="ob1-btn-input" style={{ borderColor: '#cbd5e1', color: '#475569' }} onClick={() => onRowAssignRequested(item.metricId)}>
                          {isAssigned ? '담당자 변경' : isInvitePending ? '재지정' : '담당자 지정'}
                        </button>
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
  const reportingYearQuery = new URLSearchParams(location.search).get("reportingYear");
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : DEFAULT_REPORTING_YEAR;

  // Preview States
  const [previewRole, setPreviewRole] = useState("ESG 담당자");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(ONBOARDING_SCENARIOS.UNASSIGNED);
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(APPROVAL_SCENARIOS.NO_CONSULTANT);
  const [previewRollupScenario, setPreviewRollupScenario] = useState(ROLLUP_SCENARIOS.PARENT_PENDING);

  const viewerRole = STEP12_UI_FIXTURE_ENABLED ? previewRole : (selectedCompany?.role ?? user?.role ?? "guest");

  const workflow = useSelector((state) => state.report.workflow.current);
  const rawMetrics = useSelector((state) => state.report.onboarding.metrics);
  const activeBatchId = useSelector((state) => state.report.rollup.activeBatchId);
  const requests = useSelector((state) => state.report.rollup.requests);
  const loadingWorkflow = useSelector((state) => state.report.loading.workflow);
  const loadingG0 = useSelector((state) => state.report.loading.onboarding);
  const workflowErrorPayload = useSelector((state) => state.report.error.workflow);
  const g0ErrorPayload = useSelector((state) => state.report.error.onboarding);
  
  const displayWorkflow = STEP12_UI_FIXTURE_ENABLED ? PREVIEW_WORKFLOW : workflow;
  
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
    const flattened = flattenOnboardingItems(rawMetrics);
    if (STEP12_UI_FIXTURE_ENABLED) {
      return mergeOnboardingFixtureRows(flattened, previewOnboardingScenario);
    }
    return flattened;
  }, [rawMetrics, previewOnboardingScenario]);

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

      if (nextWorkflow?.reportBasisType === "CONSOLIDATED") {
        await dispatch(fetchRollupRequests()).unwrap();
      }

      await dispatch(
        fetchOnboardingMetrics({ companyId, reportingYear, cycleType: "PRE_DMA_G0" })
      ).unwrap();
    } catch (error) {
      console.error(error);
    }
  }, [companyId, dispatch, reportingYear]);

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
        cycleType: "PRE_DMA_G0",
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
    if (selectedMetricIds.length === 0) return;
    setAssignmentMode('bulk');
    setAssignmentTargetIds(selectedMetricIds);
    setIsAssignmentModalOpen(true);
  };

  const handleRowAssignRequested = (metricId) => {
    setAssignmentMode('single');
    setAssignmentTargetIds([metricId]);
    setIsAssignmentModalOpen(true);
  };

  const handleSubmitAssignment = (payload) => {
    console.log("Assignment Payload:", payload);
    showDefaultAlert("안내", "담당자 지정 API 연결은 다음 단계에서 진행됩니다.", "info");
    setIsAssignmentModalOpen(false);
    setSelectedMetricIds([]);
  };

  const handleBulkUnassignRequested = () => {
    if (selectedMetricIds.length === 0) return;
    showDefaultAlert("안내", "담당자 해제 API 연결은 다음 단계에서 진행됩니다.", "info");
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
        <p className="ob1-desc">
          지속가능경영보고서 작성을 위한 기본 경영일반 데이터를 입력하고 확인합니다.<br />
          {displayWorkflow?.reportBasisType === "CONSOLIDATED" && "본사 및 자회사의 데이터를 통합 관리합니다."}
        </p>
      </div>

      <OnboardingStatCards stats={profileStats} g0ProfileStatus={g0ProfileStatus} />

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

              <div className="ob1-batch-bar" style={{ padding: '0 16px', marginTop: '16px' }}>
                <BatchActionBar 
                  selectedCount={selectedMetricIds.length}
                  actions={[
                    { label: '선택 지표 담당자 지정', onClick: handleBulkAssignRequested, className: 'submit' },
                    { label: '선택 지표 담당자 해제', onClick: handleBulkUnassignRequested, className: 'reject' },
                    { label: '선택 해제', onClick: () => setSelectedMetricIds([]), className: 'reject' }
                  ]}
                />
              </div>

              <OnboardingMetricTable
                g0Error={displayG0Error}
                g0Items={g0Items}
                loadingG0={STEP12_UI_FIXTURE_ENABLED ? false : loadingG0}
                selectedMetricIds={selectedMetricIds}
                onSelectMetric={handleSelectMetric}
                onToggleSelectAll={handleToggleSelectAll}
                onRowAssignRequested={handleRowAssignRequested}
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
