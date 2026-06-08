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
import RollupInboxPanel from "./RollupInboxPanel";
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
  submitOnboardingApproval,
} from "@stores/reportSlice";

const normalizeViewerRole = (role) => String(role || "").trim().toUpperCase();

const isAssignmentManagerRole = (role) => {
  const normalized = normalizeViewerRole(role);
  return ["ADMIN", "ESG", "관리자", "ESG담당자", "ESG 담당자"].includes(normalized);
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
      issueDomain: metric.issueDomain,
      subIssueId: metric.subIssueId,
      subIssueCode: metric.subIssueCode,
      subIssueName: metric.subIssueName,
      scopeSourceType: metric.scopeSourceType,
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

const OnboardingStatCards = ({ stats }) => {
  const total = stats.totalCount || 1;
  const completed = stats.completedCount || 0;
  const inProgress = stats.inProgressCount || 0;
  const notStarted = stats.notStartedCount || 0;

  const getPercent = (count) => Math.round((count / total) * 100);

  return (
    <div style={{ display: 'flex', gap: '24px', background: '#ffffff', padding: '12px 24px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingRight: '24px' }}>
        <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', marginBottom: '4px' }}>전체 지표</span>
        <span style={{ fontSize: '1.25rem', color: '#0f172a', fontWeight: '700' }}>{stats.totalCount || 0}</span>
      </div>
      <div style={{ width: '1px', background: '#e2e8f0' }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>입력 완료</span>
          <span style={{ color: '#16a34a', fontWeight: '700' }}>{completed}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(completed)}%`, background: '#16a34a' }} />
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>진행 중</span>
          <span style={{ color: '#f97316', fontWeight: '700' }}>{inProgress}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(inProgress)}%`, background: '#f97316' }} />
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>미입력</span>
          <span style={{ color: '#94a3b8', fontWeight: '700' }}>{notStarted}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(notStarted)}%`, background: '#94a3b8' }} />
        </div>
      </div>
    </div>
  );
};

const OnboardingWorkflowCta = ({
  loadingWorkflow,
  variant = "action",
  workflow,
  isNoRunWorkflow,
  onBasisModalOpen,
  onCtaClick,
}) => {
  const isWaitingRollup = workflow?.nextAction === "WAIT_ROLLUP";

  if (variant === "noRun" || isNoRunWorkflow(workflow)) {
    return (
      <>
        <div className="ob1-empty-state">
          <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다.</p>
          <p className="ob1-empty-desc">
          보고서 워크플로우를 생성해 주세요.
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



  return (
    <div className="ob1-cta-container">
      <button
        className="ob1-btn-cta"
        onClick={isWaitingRollup ? undefined : onCtaClick}
        disabled={loadingWorkflow || isWaitingRollup}
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
                  ? "자회사 데이터 대기"
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
  onBulkAssignRequested,
  onOpenMetric,
  onRetry,
  viewerRole,
  canManageAssignments,
  isConsultantViewer,
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
          {canManageAssignments && <col style={{ width: "4%" }} />}
          <col style={{ width: "8%" }} />
          <col style={{ width: "28%" }} />
          <col style={{ width: "12%" }} />
          <col style={{ width: "14%" }} />
          <col style={{ width: "13%" }} />
          <col style={{ width: "13%" }} />
          <col style={{ width: "8%" }} />
        </colgroup>
        <thead className={selectedMetricIds.length > 0 && canManageAssignments ? "ob1-thead-selected" : ""}>
          {selectedMetricIds.length > 0 && canManageAssignments ? (
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
              {canManageAssignments && (
                <th style={{ width: "4%" }}>
                  <input
                    type="checkbox"
                    className="ob1-checkbox"
                    aria-label="전체 선택"
                    checked={isAllSelected}
                    onChange={() => onToggleSelectAll(groupedItems.map(i => i.metricId))}
                  />
                </th>
              )}
              <th style={{ width: "8%" }}>Data ID</th>
              <th style={{ width: "28%" }}>입력 데이터 설명</th>
              <th style={{ width: "12%" }}>담당자</th>
              <th style={{ width: "14%" }}>제출 기한</th>
              <th style={{ width: "13%" }}>입력 상태</th>
              <th style={{ width: "13%" }}>승인 상태</th>
              <th style={{ width: "8%" }}>관리</th>
            </tr>
          )}
        </thead>
        <tbody>
          {groupedItems.map((item) => {
            const subMetrics = g0Items.filter((sub) => sub.metricId === item.metricId);
            const statusInfo = calculateMetricStatus(subMetrics);

            const formatInputStatus = (rawStatus, fallbackStatusInfo) => {
              if (!rawStatus) return { label: fallbackStatusInfo.label, cls: fallbackStatusInfo.cls || 'not-started' };
              const normalized = String(rawStatus).toLowerCase().trim();
              switch (normalized) {
                case 'approved': return { label: '입력 완료', cls: 'approved' };
                case 'submitted': return { label: '제출 완료', cls: 'submitted' };
                case 'rejected': return { label: '반려', cls: 'rejected' };
                case 'in_progress':
                case 'partial': return { label: '작성중', cls: 'draft' };
                case 'not_started': return { label: '미입력', cls: 'not-started' };
                case '입력 완료': return { label: '입력 완료', cls: 'approved' };
                case '제출완료': return { label: '제출 완료', cls: 'submitted' };
                case '작성중': return { label: '작성중', cls: 'draft' };
                default: return { label: rawStatus, cls: 'not-started' };
              }
            };

            const formatApprovalStatus = (rawStatus) => {
              if (!rawStatus) return { label: '미제출', cls: 'not-started' };
              const normalized = String(rawStatus).toLowerCase().trim();
              switch (normalized) {
                case 'approved': return { label: '승인 완료', cls: 'approved' };
                case 'submitted':
                case 'pending': return { label: '승인 대기', cls: 'draft' };
                case 'reviewed': return { label: '검토 완료', cls: 'reviewed' };
                case 'rejected': return { label: '반려', cls: 'rejected' };
                case '미제출': return { label: '미제출', cls: 'not-started' };
                case '승인대기':
                case '검토대기': return { label: '승인 대기', cls: 'draft' };
                case '검토완료': return { label: '검토 완료', cls: 'reviewed' };
                case '승인완료': return { label: '승인 완료', cls: 'approved' };
                case '반려': return { label: '반려', cls: 'rejected' };
                default: return { label: rawStatus, cls: 'not-started' };
              }
            };

            const inputStatus = formatInputStatus(item.inputStatus, statusInfo);
            const approvalStatus = formatApprovalStatus(item.approvalStatus);

            const isSelected = selectedMetricIds.includes(item.metricId);
            const isEsgManager = viewerRole === 'ESG 담당자' || viewerRole === '관리자' || viewerRole === 'ESG' || viewerRole === 'ADMIN';
            const isAssigned = item.assignmentStatus === 'ASSIGNED' || item.assignmentStatus === 'assigned';
            const isInvitePending = item.inviteStatus === 'PENDING';
            const isSelfAssigned = item.selfAssignedYn === true;
            const isAssignedToOther = isAssigned && !isSelfAssigned;

            // Mock Date validation for UI-only
            const todayStr = new Date().toISOString().slice(0, 10);
            const isOverdue = item.submissionDueDate && item.submissionDueDate < todayStr;

            return (
              <tr key={item.metricId} className={isSelected ? "selected ob1-row-selected" : ""}>
                {canManageAssignments && (
                  <td>
                    <input
                      type="checkbox"
                      className="ob1-checkbox"
                      aria-label={`${item.metricId} 선택`}
                      checked={isSelected}
                      onChange={() => onSelectMetric(item.metricId)}
                    />
                  </td>
                )}
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
                  <span className={`ob1-status-pill ${inputStatus.cls}`}>
                    {inputStatus.label}
                  </span>
                </td>

                <td>
                  <span className={`ob1-status-pill ${approvalStatus.cls}`}>
                    {approvalStatus.label}
                  </span>
                </td>

                <td>
                  <div className="ob1-td-actions" style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                    {isConsultantViewer ? (
                      <button type="button" className="ob1-btn-input" onClick={() => onOpenMetric(item, subMetrics)}>상세 보기</button>
                    ) : (
                      <>
                        <button 
                          type="button" 
                          className="ob1-btn-input" 
                          onClick={() => {
                            if (isEsgManager && isAssignedToOther) {
                              if (!window.confirm("이 지표는 다른 담당자에게 할당되어 있습니다. 그래도 수정하시겠습니까?")) {
                                return;
                              }
                            }
                            onOpenMetric(item, subMetrics);
                          }}
                          disabled={!isEsgManager && (!isAssigned || !isSelfAssigned)}
                        >
                          입력
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
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const reportingYearQuery = searchParams.get("reportingYear");
  const cycleTypeQuery = searchParams.get("cycleType");
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : DEFAULT_REPORTING_YEAR;

  const viewMode = searchParams.get("mode") === "ROLLUP_RESPONSE" ? "ROLLUP_RESPONSE" : "MY_PROJECT";
  const batchIdQuery = searchParams.get("batchId");

  // Preview States
  const [previewRole, setPreviewRole] = useState("ESG 담당자");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(ONBOARDING_SCENARIOS.UNASSIGNED);
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(APPROVAL_SCENARIOS.NO_CONSULTANT);
  const [previewRollupScenario, setPreviewRollupScenario] = useState(ROLLUP_SCENARIOS.PARENT_PENDING);

  const rawViewerRole = STEP12_UI_FIXTURE_ENABLED ? previewRole : (selectedCompany?.role ?? selectedCompany?.role_name ?? user?.role ?? user?.role_name ?? "guest");
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
  const loadingWorkflow = useSelector((state) => state.report.loading.workflow);
  const loadingG0 = useSelector((state) => state.report.loading.onboarding);
  const assigningMetrics = useSelector((state) => state.report.loading.assignMetrics);
  const workflowErrorPayload = useSelector((state) => state.report.error.workflow);
  const g0ErrorPayload = useSelector((state) => state.report.error.onboarding);

  const displayWorkflow = STEP12_UI_FIXTURE_ENABLED ? PREVIEW_WORKFLOW : workflow;
  const activeCycleType = useMemo(
    () => {
      if (viewMode === "ROLLUP_RESPONSE") return "ROLLUP_RESPONSE";
      return resolveOnboardingCycleType(displayWorkflow, cycleTypeQuery);
    },
    [viewMode, displayWorkflow, cycleTypeQuery]
  );
  const activeRollupContext = useMemo(
    () => resolveRollupContext(activeCycleType),
    [activeCycleType]
  );

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

  const g0Items = useMemo(() => {
    const flattened = mergeAssignmentIntoItems(flattenOnboardingItems(rawMetrics), rawAssignments);
    if (STEP12_UI_FIXTURE_ENABLED) {
      return mergeOnboardingFixtureRows(flattened, previewOnboardingScenario);
    }
    return flattened;
  }, [rawMetrics, rawAssignments, previewOnboardingScenario]);



  const [selectedSubIssue, setSelectedSubIssue] = useState("");

  const filteredG0ItemsForUser = useMemo(() => {
    let items = g0Items;
    if (viewMode === "ROLLUP_RESPONSE" && isEmployeeViewer) {
      items = g0Items.filter((item) => item.assignmentStatus === "ASSIGNED" || item.assignmentStatus === "assigned" || item.selfAssignedYn === true);
    }
    
    if (viewMode === "ROLLUP_RESPONSE" && requests && requests.length > 0 && batchIdQuery) {
      const batchId = parseInt(batchIdQuery, 10);
      const activeReq = requests.find(r => r.batchId === batchId) || {};
      const actionableIds = activeReq.actionableInputMetricIds || [];
      if (actionableIds.length > 0) {
        items = items.filter((item) => actionableIds.includes(item.metricId));
      }
    }
    return items;
  }, [g0Items, viewMode, isEmployeeViewer, requests, batchIdQuery]);

  const uniqueSubIssues = useMemo(() => {
    const issues = new Set();
    filteredG0ItemsForUser.forEach((item) => {
      if (item.subIssueName) {
        issues.add(item.subIssueName);
      }
    });
    return Array.from(issues);
  }, [filteredG0ItemsForUser]);

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

  const displayWorkflowError = STEP12_UI_FIXTURE_ENABLED ? null : workflowError;
  const displayG0Error = STEP12_UI_FIXTURE_ENABLED ? null : g0Error;

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
        
        if (!batchIdQuery) {
          return;
        }

        const batchId = parseInt(batchIdQuery, 10);
        await dispatch(fetchRollupRequestDetail({ batchId })).unwrap();
        const ensuredRes = await dispatch(ensureRollupResponseWorkspace({ batchId })).unwrap();
        
        const ensured = ensuredRes?.data || ensuredRes;
        const responseYear = ensured?.reportingYear || reportingYear;

        const metricId = searchParams.get("metricId");
        await dispatch(
          fetchOnboardingMetrics({ companyId, reportingYear: responseYear, cycleType: "ROLLUP_RESPONSE", metricId })
        ).unwrap();
        
        if (canManageAssignments) {
          await dispatch(
            fetchOnboardingAssignments({ companyId, reportingYear: responseYear, cycleType: "ROLLUP_RESPONSE" })
          ).unwrap();
        }
        return;
      }

      const workflowRes = await dispatch(
        fetchCurrentWorkflow({ companyId, reportingYear })
      ).unwrap();
      const nextWorkflow = workflowRes?.data || workflowRes;

      if (isNoRunWorkflow(nextWorkflow)) {
        setActiveSourceCycleId(null);
        setIsBasisModalOpen(true);
        return;
      }

      const nextCycleType = resolveOnboardingCycleType(nextWorkflow, cycleTypeQuery);
      const nextRollupContext = resolveRollupContext(nextCycleType);
      const runId = nextWorkflow.runId;
      let sourceCycleId;

      if (nextCycleType === "POST_DMA_DISCLOSURE") {
        const initializedRes = await dispatch(
          initializePostDmaDisclosureScope({ runId })
        ).unwrap();

        const initializedScope = initializedRes?.data || initializedRes;
        sourceCycleId = initializedScope?.cycleId;
      }
      setActiveSourceCycleId(sourceCycleId ?? null);

      if (nextWorkflow?.reportBasisType === "CONSOLIDATED") {
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
      }

      const metricId = searchParams.get("metricId");
      
      await dispatch(
        fetchOnboardingMetrics({ companyId, reportingYear, cycleType: nextCycleType, metricId })
      ).unwrap();
      if (canManageAssignments) {
        await dispatch(
          fetchOnboardingAssignments({ companyId, reportingYear, cycleType: nextCycleType })
        ).unwrap();
      }
    } catch (error) {
      console.error(error);
    }
  }, [companyId, cycleTypeQuery, dispatch, reportingYear, location.search, viewMode]);

  useEffect(() => {
    dispatch(resetReportState());
    Promise.resolve().then(() => initializeOnboarding());
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

      if (status === "DRAFT") {
        showDefaultAlert("완료", "임시저장이 완료되었습니다.", "success");
        setIsModalOpen(false);
        await initializeOnboarding();
        return;
      }

      try {
        await dispatch(
          submitOnboardingApproval({
            companyId,
            reportingYear,
            metricId,
            cycleType: activeCycleType,
          })
        ).unwrap();
        showDefaultAlert("완료", "승인 요청이 완료되었습니다.", "success");
        setIsModalOpen(false);
        await initializeOnboarding();
      } catch (submitError) {
        console.error(submitError);
        let detail =
          submitError?.message || submitError?.detail || submitError?.error?.message || "";
          
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
      let detail = error?.message || error?.detail || error?.error?.message || "";
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h1 className="ob1-title" style={{ margin: 0, fontSize: '1.25rem' }}>온보딩 [{viewMode === "ROLLUP_RESPONSE" ? "요청 대응" : basisLabel}]</h1>
          {(() => {
            const statusInfo = getStatusInfo(g0ProfileStatus);
            const total = profileStats.totalCount || 1;
            const percent = Math.round((profileStats.completedCount / total) * 100);
            return (
              <span className={`ob1-status-pill ${statusInfo.cls}`} style={{ fontSize: '14px', padding: '6px 12px' }}>
                진행률 {percent}% · {statusInfo.label}
              </span>
            );
          })()}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
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
          {viewMode === "ROLLUP_RESPONSE" && batchIdQuery && (
            <div className="ob1-cta-container">
              <button
                className="ob1-btn-cta"
                onClick={() => setIsSubTransferModalOpen(true)}
                disabled={loadingWorkflow}
              >
                데이터 전송
              </button>
            </div>
          )}
        </div>
      </div>
      
      {viewMode === "ROLLUP_RESPONSE" && !batchIdQuery ? (
        <RollupInboxPanel requests={requests} />
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
              {canManageRollup && viewMode === "MY_PROJECT" && (
                <>
                  <RollupSummaryPanel
                    batchId={activeBatchId}
                    workflow={displayWorkflow}
                    onCtaClick={handleCtaClick}
                    onCalculated={() => initializeOnboarding()}
                    rollupPurposeCode={activeRollupContext.rollupPurposeCode}
                    metricScopeCode={activeRollupContext.metricScopeCode}
                    rollupScenario={previewRollupScenario}
                    onSendSource={() => setIsSubTransferModalOpen(true)}
                  />

                </>
              )}

              <OnboardingMetricTable
                g0Error={displayG0Error}
                g0Items={filteredG0Items}
                loadingG0={STEP12_UI_FIXTURE_ENABLED ? false : loadingG0}
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
        reportingYear={reportingYear}
        sourceCycleId={activeSourceCycleId}
        rollupPurposeCode={activeRollupContext.rollupPurposeCode}
        metricScopeCode={activeRollupContext.metricScopeCode}
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
        reportingYear={reportingYear}
        onTransferred={async () => {
          await initializeOnboarding();
        }}
        onNavigateToInput={({ url, viewMode: newViewMode }) => {
          setIsSubTransferModalOpen(false);
          if (newViewMode) {
            setViewMode(newViewMode);
          } else if (url) {
            navigate(url);
          }
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
