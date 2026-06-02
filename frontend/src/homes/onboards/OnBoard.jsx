import { useState, useEffect, useCallback } from "react";
import { useLocation } from "react-router";
import "@styles/onboarding1.css";
import { useAuth } from "@hooks/AuthContext.jsx";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import ReportBasisSelectModal from "@components/UI/ReportBasisSelectModal.jsx";
import OnboardingModalShell from "./modal/OnboardingModalShell";
import SubsidiaryRequestModal from "./modal/SubsidiaryRequestModal";
import SubsidiaryTransferModal from "./modal/SubsidiaryTransferModal";
import RollupSummaryPanel from "./RollupSummaryPanel";
import {
  calculateMetricStatus,
  calculateProfileStats,
  getAtomicId,
  getInputTypeBadge,
  getStatusInfo,
  hasAtomicValue,
  isEditableItem,
  resolveG0InputMode,
} from "./onboardingUtils";
import {
  DEFAULT_REPORTING_YEAR,
  getCurrent,
  getOnboardingMetrics,
  saveOnboardingMetricValues,
  listRequests,
} from "@/apis/report";

const isApiFailed = (res) =>
  res?.status === false || res?.success === false || !res?.data;

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
        <div className="ob1-stat-title">전체 G0 입력 항목</div>
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
  onTransferModalOpen,
}) => {
  if (variant === "noRun" || isNoRunWorkflow(workflow)) {
    return (
      <>
        <div className="ob1-empty-state">
          <div className="ob1-empty-icon">G0</div>
          <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다</p>
          <p className="ob1-empty-desc">
            G0 입력을 시작하려면 먼저 독립기준 또는 연결기준 보고서 워크플로우를 생성해 주세요.
          </p>
          <button type="button" className="ob1-btn-cta" onClick={onBasisModalOpen}>
            발행 기준 선택
          </button>
        </div>
        <div className="ob1-cta-container">
          <button className="ob1-btn-cta" onClick={onCtaClick} disabled={loadingWorkflow}>
            {loadingWorkflow ? "로딩중..." : "발행 기준 선택"}
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

        {activeBatchId && (
          <RollupSummaryPanel
            batchId={activeBatchId}
            onCalculated={onCalculated}
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
          ? "로딩중..."
          : !workflow
            ? "워크플로우 상태 확인 필요"
            : workflow.nextAction === "START_DMA"
              ? "이중중대성평가 진행하기"
              : workflow.nextAction === "REQUEST_ROLLUP"
                ? "자회사 데이터 요청하기"
                : workflow.nextAction === "WAIT_ROLLUP"
                  ? "롤업 대기"
                  : "G0 입력 상태 확인"}
      </button>
    </div>
  );
};

const OnboardingMetricTable = ({
  g0Error,
  g0Items,
  loadingG0,
  onOpenMetric,
  onRetry,
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
        <p>G0 프로필 데이터를 불러오고 있습니다...</p>
      </div>
    );
  }

  if (g0Items.length === 0) {
    return (
      <div className="ob1-empty-state">
        <div className="ob1-empty-icon">G0</div>
        <p className="ob1-empty-title">G0 지표가 없습니다</p>
        <p className="ob1-empty-desc">보고서 워크플로우를 먼저 시작해 주세요.</p>
      </div>
    );
  }

  return (
    <div className="ob1-table-container">
      <table className="ob1-table">
        <thead>
          <tr>
            <th style={{ width: "12%" }}>Metric ID</th>
            <th style={{ width: "15%" }}>Atomic ID</th>
            <th style={{ width: "35%" }}>지표명</th>
            <th style={{ width: "10%" }}>입력 유형</th>
            <th style={{ width: "10%" }}>단위</th>
            <th style={{ width: "10%" }}>상태</th>
            <th style={{ width: "8%" }}>데이터 입력</th>
          </tr>
        </thead>
        <tbody>
          {groupByMetric(g0Items).map((item) => {
            const subMetrics = g0Items.filter((sub) => sub.metricId === item.metricId);
            const statusInfo = calculateMetricStatus(subMetrics);
            const typeBadge = getInputTypeBadge(
              subMetrics.find((sub) => isEditableItem(sub)) || subMetrics[0] || item
            );
            const atomicId = getAtomicId(item);

            return (
              <tr key={item.metricId}>
                <td>{item.metricId}</td>
                <td>{subMetrics.length > 1 ? `(${subMetrics.length}개 항목)` : atomicId || "-"}</td>
                <td className="ob1-td-name">{item.metricName || item.atomicName || "-"}</td>
                <td>
                  <span className={`ob1-type-badge ${typeBadge.cls || ""}`}>
                    {typeBadge.label}
                  </span>
                </td>
                <td>{item.unit || "-"}</td>
                <td>
                  <span className={`ob1-status-pill ${statusInfo.cls}`}>
                    {statusInfo.label}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className="ob1-btn-input"
                    onClick={() => onOpenMetric(item, subMetrics)}
                  >
                    입력
                  </button>
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
  const { selectedCompany } = useAuth();
  const location = useLocation();
  const companyId = selectedCompany?.company_id ?? selectedCompany?.companyId;
  const reportingYearQuery = new URLSearchParams(location.search).get("reportingYear");
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : DEFAULT_REPORTING_YEAR;

  const [workflow, setWorkflow] = useState(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);
  const [workflowError, setWorkflowError] = useState(null);
  const [g0Items, setG0Items] = useState([]);
  const [g0ProfileStatus, setG0ProfileStatus] = useState(null);
  const [loadingG0, setLoadingG0] = useState(true);
  const [g0Error, setG0Error] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isBasisModalOpen, setIsBasisModalOpen] = useState(false);
  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [hasPendingSubsidiaryRequest, setHasPendingSubsidiaryRequest] = useState(false);

  const refreshPendingSubsidiaryRequests = useCallback(async (nextWorkflow) => {
    if (
      !companyId ||
      !nextWorkflow ||
      isNoRunWorkflow(nextWorkflow) ||
      nextWorkflow.reportBasisType !== "CONSOLIDATED"
    ) {
      setHasPendingSubsidiaryRequest(false);
      return;
    }

    try {
      const res = await listRequests();
      const items = Array.isArray(res?.data?.items)
        ? res.data.items
        : Array.isArray(res?.data)
          ? res.data
          : Array.isArray(res?.items)
            ? res.items
            : [];
      setHasPendingSubsidiaryRequest(items.some(isPendingSubsidiaryRequest));
    } catch (error) {
      console.error("Failed to refresh subsidiary request state", error);
      setHasPendingSubsidiaryRequest(false);
    }
  }, [companyId]);

  const initializeOnboarding = useCallback(async () => {
    if (!companyId) {
      setWorkflow(null);
      setG0Items([]);
      setG0ProfileStatus(null);
      setWorkflowError("회사를 먼저 선택해 주세요.");
      setG0Error(null);
      setLoadingWorkflow(false);
      setLoadingG0(false);
      setHasPendingSubsidiaryRequest(false);
      return;
    }

    setLoadingWorkflow(true);
    setLoadingG0(true);
    setWorkflowError(null);
    setG0Error(null);

    try {
      const workflowRes = await getCurrent(companyId, reportingYear);
      if (isApiFailed(workflowRes)) {
        setWorkflow(null);
        setG0Items([]);
        setG0ProfileStatus(null);
        setHasPendingSubsidiaryRequest(false);
        setWorkflowError(workflowRes?.error?.message || "보고서 워크플로우 조회에 실패했습니다.");
        return;
      }

      const nextWorkflow = workflowRes.data;
      setWorkflow(nextWorkflow);

      if (isNoRunWorkflow(nextWorkflow)) {
        setG0Items([]);
        setG0ProfileStatus("NOT_STARTED");
        setHasPendingSubsidiaryRequest(false);
        setIsBasisModalOpen(true);
        return;
      }

      await refreshPendingSubsidiaryRequests(nextWorkflow);

      const profileRes = await getOnboardingMetrics(companyId, reportingYear, "PRE_DMA_G0");
      if (isApiFailed(profileRes)) {
        setG0Items([]);
        setG0ProfileStatus(null);
        setG0Error(profileRes?.error?.message || profileRes?.detail || "G0 프로필 조회에 실패했습니다.");
        return;
      }

      const flattenedItems = flattenOnboardingItems(profileRes.data.items || []);
      setG0Items(flattenedItems);
      setG0ProfileStatus(getProfileStatusFromItems(flattenedItems));
    } catch (error) {
      console.error(error);
      setWorkflow(null);
      setG0Items([]);
      setG0ProfileStatus(null);
      setWorkflowError("온보딩 데이터를 불러오는 중 오류가 발생했습니다.");
    } finally {
      setLoadingWorkflow(false);
      setLoadingG0(false);
    }
  }, [companyId, refreshPendingSubsidiaryRequests, reportingYear]);

  useEffect(() => {
    initializeOnboarding();
  }, [initializeOnboarding, location.state?.workflowStartedAt]);

  const profileStats = calculateProfileStats(g0Items);
  const basisLabel =
    workflow?.reportBasisType === "CONSOLIDATED"
      ? "연결기준"
      : workflow?.reportBasisType === "ENTITY"
        ? "독립기준"
        : "미확정";

  const handleCtaClick = () => {
    if (!workflow || isNoRunWorkflow(workflow)) {
      setIsBasisModalOpen(true);
      return;
    }

    switch (workflow.nextAction) {
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
        showDefaultAlert("안내", workflow.message || "G0 입력 상태를 확인해 주세요.", "info");
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

      const res = await saveOnboardingMetricValues(metricId, payload);
      if (isApiFailed(res)) {
        showDefaultAlert("오류", res?.error?.message || res?.detail || "저장에 실패했습니다.", "error");
        return;
      }

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

  if (loadingWorkflow && loadingG0) {
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
          지속가능경영보고서 작성을 위한 기본 경영일반(G0) 지표를 입력하고 확인합니다.<br />
          {workflow?.reportBasisType === "CONSOLIDATED" && "본사 및 자회사의 데이터를 통합 관리합니다."}
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
          {workflowError && (
            <div className="ob1-inline-error">
              <span className="ob1-error-icon">!</span>
              <span>{workflowError}</span>
            </div>
          )}

          {isNoRunWorkflow(workflow) ? (
            <OnboardingWorkflowCta
              variant="noRun"
              loadingWorkflow={loadingWorkflow}
              workflow={workflow}
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
                workflow={workflow}
                isNoRunWorkflow={isNoRunWorkflow}
                onCalculated={() => {
                  initializeOnboarding();
                }}
                onCtaClick={handleCtaClick}
                onTransferModalOpen={() => setIsSubTransferModalOpen(true)}
              />

              <OnboardingMetricTable
                g0Error={g0Error}
                g0Items={g0Items}
                loadingG0={loadingG0}
                onRetry={initializeOnboarding}
                onOpenMetric={(item, subMetrics) => {
                  setSelectedItem({
                    parent: item,
                    metrics: subMetrics,
                  });
                  setIsModalOpen(true);
                }}
              />

              <OnboardingWorkflowCta
                loadingWorkflow={loadingWorkflow}
                workflow={workflow}
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
      />

      <SubsidiaryRequestModal
        isOpen={isSubReqModalOpen}
        onClose={() => setIsSubReqModalOpen(false)}
        runId={workflow?.runId}
        onRequested={async (batch) => {
          setActiveBatchId(batch.batchId);
          setIsSubReqModalOpen(false);
          await initializeOnboarding();
        }}
      />

      <SubsidiaryTransferModal
        isOpen={isSubTransferModalOpen}
        onClose={() => setIsSubTransferModalOpen(false)}
        onTransferred={async (batchId) => {
          setActiveBatchId(batchId);
          await initializeOnboarding();
          console.log("전송 완료된 배치", batchId);
        }}
      />

      <ReportBasisSelectModal
        isOpen={isBasisModalOpen}
        onClose={() => setIsBasisModalOpen(false)}
        companyId={companyId}
        reportingYear={reportingYear}
      />
    </div>
  );
};

export default OnBoard;
