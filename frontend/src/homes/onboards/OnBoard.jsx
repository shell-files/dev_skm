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
          <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다.</p>
          <p className="ob1-empty-desc">
            G0 입력을 시작하려면 먼저 별도 또는 연결 기준 보고서 워크플로우를 생성해 주세요.
          </p>
          <button type="button" className="ob1-btn-cta" onClick={onBasisModalOpen}>
            발행 기준 선택
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
          ? "로딩 중..."
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
          ?ㅼ떆 ?쒕룄
        </button>
      </div>
    );
  }

  if (loadingG0) {
    return (
      <div className="ob1-table-loading">
        <div className="ob1-spinner" />
        <p>G0 ?꾨줈???곗씠?곕? 遺덈윭?ㅺ퀬 ?덉뒿?덈떎...</p>
      </div>
    );
  }

  if (g0Items.length === 0) {
    return (
      <div className="ob1-empty-state">
        <div className="ob1-empty-icon">G0</div>
        <p className="ob1-empty-title">G0 吏?쒓? ?놁뒿?덈떎</p>
        <p className="ob1-empty-desc">蹂닿퀬???뚰겕?뚮줈?곕? 癒쇱? ?쒖옉??二쇱꽭??</p>
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
            <th style={{ width: "35%" }}>吏?쒕챸</th>
            <th style={{ width: "10%" }}>?낅젰 ?좏삎</th>
            <th style={{ width: "10%" }}>?⑥쐞</th>
            <th style={{ width: "10%" }}>?곹깭</th>
            <th style={{ width: "8%" }}>?곗씠???낅젰</th>
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
                <td>{subMetrics.length > 1 ? `(${subMetrics.length}媛???ぉ)` : atomicId || "-"}</td>
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
                    ?낅젰
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
  const dispatch = useDispatch();
  const { selectedCompany } = useAuth();
  const location = useLocation();
  const companyId = selectedCompany?.company_id ?? selectedCompany?.companyId;
  const reportingYearQuery = new URLSearchParams(location.search).get("reportingYear");
  const reportingYear = reportingYearQuery ? parseInt(reportingYearQuery, 10) : DEFAULT_REPORTING_YEAR;

  const workflow = useSelector((state) => state.report.workflow.current);
  const rawMetrics = useSelector((state) => state.report.onboarding.metrics);
  const activeBatchId = useSelector((state) => state.report.rollup.activeBatchId);
  const requests = useSelector((state) => state.report.rollup.requests);
  const loadingWorkflow = useSelector((state) => state.report.loading.workflow);
  const loadingG0 = useSelector((state) => state.report.loading.onboarding);
  const workflowErrorPayload = useSelector((state) => state.report.error.workflow);
  const g0ErrorPayload = useSelector((state) => state.report.error.onboarding);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isBasisModalOpen, setIsBasisModalOpen] = useState(false);
  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const g0Items = useMemo(() => flattenOnboardingItems(rawMetrics), [rawMetrics]);
  const g0ProfileStatus = useMemo(() => getProfileStatusFromItems(g0Items), [g0Items]);
  const hasPendingSubsidiaryRequest = useMemo(
    () => requests.some(isPendingSubsidiaryRequest),
    [requests]
  );
  const workflowError = workflowErrorPayload?.message || null;
  const g0Error = g0ErrorPayload?.message || null;

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
    initializeOnboarding();
  }, [initializeOnboarding, location.state?.workflowStartedAt]);

  const profileStats = calculateProfileStats(g0Items);
  const basisLabel =
    workflow?.reportBasisType === "CONSOLIDATED"
      ? "연결기준"
      : workflow?.reportBasisType === "ENTITY"
        ? "별도기준"
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
          <div className="ob1-sidebar-title">?좊떦 ??ぉ</div>
          <ul className="ob1-sidebar-menu">
            <li className="ob1-sidebar-menu-item active">1. 寃쎌쁺?쇰컲 - G0</li>
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
          console.log("?꾩넚 ?꾨즺??諛곗튂", batchId);
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

