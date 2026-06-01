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
  DEFAULT_REPORTING_YEAR,
  getCurrent,
  getG0Profile,
  saveG0Profile,
  getG0ProfileStatus,
} from "@/apis/report";

const STRUCTURED_LOOKUP_IDS = new Set(["G0-05__QL0002", "G0-06__QL0001"]);
const EDITABLE_INPUT_MODES = new Set(["MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE"]);

const isApiFailed = (res) =>
  res?.status === false || res?.success === false || !res?.data;

const isNoRunWorkflow = (workflow) => workflow?.workflowStep === "NO_RUN";

const resolveG0InputMode = (item = {}) => {
  const atomicMetricId = item.atomicMetricId || "";
  const dataValueType = String(item.dataValueType || "").trim().toUpperCase();

  if (
    item.atomicDataRole === "DERIVED" ||
    item.rollupRole === "consolidated_result" ||
    /^G0-02__G\d+/.test(atomicMetricId) ||
    atomicMetricId === "G0-03__G0001"
  ) {
    return "ROLLUP_READONLY";
  }

  if (
    STRUCTURED_LOOKUP_IDS.has(atomicMetricId) ||
    item.inputMode === "STRUCTURED_LOOKUP"
  ) {
    return "STRUCTURED_LOOKUP";
  }

  if (item.editableYn === false) {
    return "ROLLUP_READONLY";
  }

  if (item.inputMode) {
    return item.inputMode;
  }

  if (atomicMetricId === "G0-05__QL0001") {
    return "YEAR_RANGE";
  }

  if (
    /^G0-02__Q\d+/.test(atomicMetricId) ||
    /^G0-03__Q\d+/.test(atomicMetricId) ||
    dataValueType === "QUANT" ||
    dataValueType === "NUMBER" ||
    dataValueType === "NUMERIC" ||
    item.dataValueType === "정량"
  ) {
    return "MANUAL_NUMBER";
  }

  return "MANUAL_TEXTAREA";
};

const isEditableItem = (item) => EDITABLE_INPUT_MODES.has(resolveG0InputMode(item));

const getInputTypeBadge = (item = {}) => {
  switch (resolveG0InputMode(item)) {
    case "MANUAL_NUMBER":
      return { label: "숫자 입력", cls: "direct" };
    case "MANUAL_TEXTAREA":
      return { label: "서술 입력", cls: "narrative" };
    case "YEAR_RANGE":
      return { label: "기간 입력", cls: "direct" };
    case "STRUCTURED_LOOKUP":
      return { label: "범위 설정", cls: "reference" };
    case "ROLLUP_READONLY":
      return { label: "자동 산출", cls: "reference" };
    default:
      return { label: resolveG0InputMode(item) || "-", cls: "" };
  }
};

const hasValue = (item) =>
  (item.valueText !== null && item.valueText !== undefined && item.valueText !== "") ||
  (item.valueNumeric !== null && item.valueNumeric !== undefined);

const groupByMetric = (items) => {
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

const OnBoard = () => {
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

  const initializeOnboarding = useCallback(async () => {
    if (!companyId) {
      setWorkflow(null);
      setG0Items([]);
      setG0ProfileStatus(null);
      setWorkflowError("회사를 먼저 선택해 주세요.");
      setG0Error(null);
      setLoadingWorkflow(false);
      setLoadingG0(false);
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
        setWorkflowError(workflowRes?.error?.message || "보고서 워크플로우 조회에 실패했습니다.");
        return;
      }

      const nextWorkflow = workflowRes.data;
      setWorkflow(nextWorkflow);

      if (isNoRunWorkflow(nextWorkflow)) {
        setG0Items([]);
        setG0ProfileStatus("NOT_STARTED");
        setIsBasisModalOpen(true);
        return;
      }

      const profileRes = await getG0Profile(companyId, reportingYear);
      if (isApiFailed(profileRes)) {
        setG0Items([]);
        setG0ProfileStatus(null);
        setG0Error(profileRes?.error?.message || profileRes?.detail || "G0 프로필 조회에 실패했습니다.");
        return;
      }

      setG0Items(profileRes.data.items || []);
      setG0ProfileStatus(profileRes.data.g0ProfileStatus || "NOT_STARTED");
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
  }, [companyId, reportingYear]);

  useEffect(() => {
    initializeOnboarding();
  }, [initializeOnboarding, location.state?.workflowStartedAt]);

  const fetchG0Status = useCallback(async () => {
    if (!companyId || isNoRunWorkflow(workflow)) return;
    try {
      const res = await getG0ProfileStatus(companyId, reportingYear);
      if (!isApiFailed(res)) {
        setG0ProfileStatus(res.data.g0ProfileStatus || "NOT_STARTED");
      }
    } catch (error) {
      console.error("G0 status fetch failed", error);
    }
  }, [companyId, reportingYear, workflow]);

  const editableItems = g0Items.filter((item) => isEditableItem(item));
  const totalCount = g0Items.length;
  const completedCount = editableItems.filter((item) => hasValue(item)).length;
  const notStartedCount = Math.max(0, editableItems.length - completedCount);
  const groupedG0Items = groupByMetric(g0Items);
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
      const payload = {
        reportingYear,
        items: selectedItem.metrics
          .filter((item) => isEditableItem(item))
          .map((item) => {
            const rawValue = values[item.atomicMetricId] ?? "";
            const trimmed = String(rawValue).trim();
            const numericYn =
              resolveG0InputMode(item) === "MANUAL_NUMBER" &&
              trimmed !== "" &&
              /^-?\d+(\.\d+)?$/.test(trimmed);

            return {
              metricId: item.metricId,
              atomicMetricId: item.atomicMetricId,
              valueText: numericYn ? null : trimmed || null,
              valueNumeric: numericYn ? Number(trimmed) : null,
              unit: item.unit || null,
            };
          }),
      };

      const res = await saveG0Profile(companyId, payload);
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
      await fetchG0Status();
    } catch (error) {
      console.error(error);
      showDefaultAlert("오류", "처리 중 오류가 발생했습니다.", "error");
    }
  };

  const getSubMetrics = (metricId) => g0Items.filter((item) => item.metricId === metricId);

  const renderNoRunState = () => (
    <div className="ob1-empty-state">
      <div className="ob1-empty-icon">G0</div>
      <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다</p>
      <p className="ob1-empty-desc">
        G0 입력을 시작하려면 먼저 독립기준 또는 연결기준 보고서 워크플로우를 생성해 주세요.
      </p>
      <button type="button" className="ob1-btn-cta" onClick={() => setIsBasisModalOpen(true)}>
        발행 기준 선택
      </button>
    </div>
  );

  const renderMetricStatus = (subMetrics) => {
    const statusTargets = subMetrics.filter((sub) => isEditableItem(sub));
    if (statusTargets.length === 0) {
      const modes = new Set(subMetrics.map((sub) => resolveG0InputMode(sub)));
      if (modes.has("ROLLUP_READONLY")) return { label: "자동 산출", cls: "draft" };
      if (modes.has("STRUCTURED_LOOKUP")) return { label: "범위 설정 필요", cls: "draft" };
      return { label: "조회 전용", cls: "draft" };
    }

    const completed = statusTargets.filter((sub) => hasValue(sub)).length;
    if (completed === 0) return { label: "미입력", cls: "not-started" };
    if (completed < statusTargets.length) return { label: "진행중", cls: "draft" };
    return { label: "입력 완료", cls: "approved" };
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

      <div className="ob1-cards">
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">전체 G0 입력 항목</div>
          <div className="ob1-stat-value">{totalCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">입력 완료</div>
          <div className="ob1-stat-value success">{completedCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">미입력</div>
          <div className="ob1-stat-value warning">{notStartedCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">프로필 상태</div>
          <div className="ob1-stat-value">
            <span className={`ob1-status-pill ${g0ProfileStatus === "COMPLETED" ? "approved" : "not-started"}`}>
              {g0ProfileStatus === "COMPLETED" ? "완료" : g0ProfileStatus === "IN_PROGRESS" ? "진행중" : "미시작"}
            </span>
          </div>
        </div>
      </div>

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
            renderNoRunState()
          ) : (
            <>
              <div style={{ display: "flex", justifyContent: "flex-end", padding: "16px 24px 0 24px" }}>
                <button
                  className="ob1-btn-input"
                  onClick={() => setIsSubTransferModalOpen(true)}
                  style={{ padding: "8px 16px", background: "#f8fafc", color: "#1e293b", border: "1px solid #cbd5e1" }}
                >
                  지주사 요청 확인 및 전송
                </button>
              </div>

              {activeBatchId && (
                <RollupSummaryPanel
                  batchId={activeBatchId}
                  onCalculated={() => {
                    initializeOnboarding();
                  }}
                />
              )}

              {g0Error && (
                <div className="ob1-inline-error">
                  <span className="ob1-error-icon">!</span>
                  <span>{g0Error}</span>
                  <button type="button" className="ob1-btn-retry" onClick={initializeOnboarding}>
                    다시 시도
                  </button>
                </div>
              )}

              {loadingG0 && !g0Error && (
                <div className="ob1-table-loading">
                  <div className="ob1-spinner" />
                  <p>G0 프로필 데이터를 불러오고 있습니다...</p>
                </div>
              )}

              {!loadingG0 && !g0Error && g0Items.length === 0 && (
                <div className="ob1-empty-state">
                  <div className="ob1-empty-icon">G0</div>
                  <p className="ob1-empty-title">G0 지표가 없습니다</p>
                  <p className="ob1-empty-desc">보고서 워크플로우를 먼저 시작해 주세요.</p>
                </div>
              )}

              {!loadingG0 && !g0Error && g0Items.length > 0 && (
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
                      {groupedG0Items.map((item) => {
                        const subMetrics = getSubMetrics(item.metricId);
                        const statusInfo = renderMetricStatus(subMetrics);
                        const typeBadge = getInputTypeBadge(
                          subMetrics.find((sub) => isEditableItem(sub)) || subMetrics[0] || item
                        );

                        return (
                          <tr key={item.metricId}>
                            <td>{item.metricId}</td>
                            <td>{subMetrics.length > 1 ? `(${subMetrics.length}개 항목)` : item.atomicMetricId || "-"}</td>
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
                                onClick={() => {
                                  setSelectedItem({
                                    parent: item,
                                    metrics: subMetrics,
                                  });
                                  setIsModalOpen(true);
                                }}
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
              )}
            </>
          )}

          <div className="ob1-cta-container">
            <button
              className="ob1-btn-cta"
              onClick={handleCtaClick}
              disabled={loadingWorkflow}
            >
              {loadingWorkflow
                ? "로딩중..."
                : isNoRunWorkflow(workflow)
                  ? "발행 기준 선택"
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
        onRequested={(batch) => {
          setActiveBatchId(batch.batchId);
          setIsSubReqModalOpen(false);
        }}
      />

      <SubsidiaryTransferModal
        isOpen={isSubTransferModalOpen}
        onClose={() => setIsSubTransferModalOpen(false)}
        onTransferred={(batchId) => {
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
