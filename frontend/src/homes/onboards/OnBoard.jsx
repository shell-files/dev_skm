import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import "@styles/onboarding1.css";
import { useAuth } from "@hooks/AuthContext.jsx";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
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

/* ─── 응답 실패 판정 유틸 ─── */
const isApiFailed = (res) =>
  res?.status === false || res?.success === false || !res?.data;

/* ─── inputFormat → 유형 badge (G0 DTO에 inputFormat이 있을 때만 표시) ─── */
const STRUCTURED_LOOKUP_IDS = new Set(["G0-05__QL0002", "G0-06__QL0001"]);
const EDITABLE_INPUT_MODES = new Set(["MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE"]);

const resolveG0InputMode = (item = {}) => {
  if (item.inputMode) return item.inputMode;

  const atomicMetricId = item.atomicMetricId || "";
  const dataValueType = String(item.dataValueType || "").trim().toUpperCase();

  if (
    item.editableYn === false ||
    item.atomicDataRole === "DERIVED" ||
    item.rollupRole === "consolidated_result" ||
    /^G0-02__G\d+/.test(atomicMetricId) ||
    atomicMetricId === "G0-03__G0001"
  ) {
    return "ROLLUP_READONLY";
  }

  if (STRUCTURED_LOOKUP_IDS.has(atomicMetricId)) {
    return "STRUCTURED_LOOKUP";
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

const getInputTypeBadge = (item) => {
  const mode = resolveG0InputMode(item);
  if (mode) {
    switch (mode) {
      case "MANUAL_NUMBER":
        return { label: "숫자 입력", cls: "direct" };
      case "MANUAL_TEXTAREA":
        return { label: "서술 입력", cls: "narrative" };
      case "YEAR_RANGE":
        return { label: "기간 입력", cls: "direct" };
      case "STRUCTURED_LOOKUP":
        return { label: "범위 설정", cls: "reference" };
      case "ROLLUP_READONLY":
        return { label: "자동 집계", cls: "reference" };
      default:
        return { label: mode, cls: "" };
    }
  }

  const fmt = item.inputFormat;
  if (!fmt) return { label: "-", cls: "" };

  switch (fmt) {
    case "number":
    case "int":
    case "decimal":
    case "currency":
    case "%":
    case "YYYY":
      return { label: "정량 직접입력", cls: "direct" };
    case "text":
    case "string":
      return { label: "서술형", cls: "narrative" };
    case "boolean":
    case "Y/N":
    case "json/table":
    case "multi-select":
      return { label: "참조형", cls: "reference" };
    default:
      return { label: fmt, cls: "" };
  }
};

/* ─── 상태 badge ─── */
const getStatusInfo = (status) => {
  switch (status) {
    case "DRAFT":
    case "IN_PROGRESS":
      return { label: "입력 진행중", cls: "draft" };
    case "SUBMITTED":
    case "APPROVED":
    case "COMPLETED":
      return { label: "입력 완료", cls: "approved" };
    case "NOT_STARTED":
    default:
      return { label: "미입력", cls: "not-started" };
  }
};

const OnBoard = () => {
  const navigate = useNavigate(); 
  const { selectedCompany } = useAuth();
  const companyId =
    selectedCompany?.company_id ?? selectedCompany?.companyId;

  /* ─── workflow state ─── */
  const [workflow, setWorkflow] = useState(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);
  const [workflowError, setWorkflowError] = useState(null);

  /* ─── G0 profile state ─── */
  const [g0Items, setG0Items] = useState([]);
  const [g0ProfileStatus, setG0ProfileStatus] = useState(null);
  const [loadingG0, setLoadingG0] = useState(true);
  const [g0Error, setG0Error] = useState(null);

  /* ─── modal state ─── */
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  /* ─── rollup modal state ─── */
  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState(null);

  /* ─── workflow 조회 ─── */
  const fetchWorkflow = useCallback(async () => {
    if (!companyId) {
      setWorkflow(null);
      setLoadingWorkflow(false);
      return;
    }

    setLoadingWorkflow(true);
    setWorkflowError(null);
    try {
      const res = await getCurrent(companyId, DEFAULT_REPORTING_YEAR);
      console.log(res)
      const isFailed =
        res?.status === false ||
        res?.success === false ||
        !res?.data;

      if (isFailed) {
        setWorkflow(null);
        setWorkflowError(res?.error?.message || "보고서 워크플로우 조회에 실패했습니다.");
        return;
      }

      setWorkflow(res.data);
    } catch (error) {
      console.error(error);
      setWorkflow(null);
      setWorkflowError("보고서 워크플로우 조회에 실패했습니다.");
    } finally {
      setLoadingWorkflow(false);
    }
  }, [companyId]);


  /* ─── G0 profile 조회 ─── */
  const fetchG0Profile = useCallback(async () => {
    if (!companyId) {
      setG0Items([]);
      setLoadingG0(false);
      return;
    }

    setLoadingG0(true);
    setG0Error(null);
    try {
      const res = await getG0Profile(companyId, DEFAULT_REPORTING_YEAR);
      if (isApiFailed(res)) {
        setG0Items([]);
        setG0Error(res?.error?.message || res?.detail || "G0 프로필 조회에 실패했습니다.");
        return;
      }
      setG0Items(res.data.items || []);
      setG0ProfileStatus(res.data.g0ProfileStatus || "NOT_STARTED");
    } catch (error) {
      console.error(error);
      setG0Items([]);
      setG0Error("G0 프로필 조회에 실패했습니다.");
    } finally {
      setLoadingG0(false);
    }
  }, [companyId]);

  const fetchG0Status = useCallback(async () => {
    if (!companyId) return;
    try {
      const res = await getG0ProfileStatus(companyId, DEFAULT_REPORTING_YEAR);
      if (!isApiFailed(res)) {
        setG0ProfileStatus(res.data.g0ProfileStatus || "NOT_STARTED");
      }
    } catch (error) {
      console.error("G0 status fetch failed", error);
    }
  }, [companyId]);

  useEffect(() => {
    fetchWorkflow();
    fetchG0Profile();
    console.log("run()");
  }, [fetchWorkflow, fetchG0Profile]);

  /* ─── 통계 계산 ─── */
  const totalCount = g0Items.length;
  let completedCount = 0;
  let notStartedCount = 0;

  g0Items.forEach((item) => {
    if (!isEditableItem(item)) return;
    const hasValue =
      (item.valueText !== null && item.valueText !== undefined && item.valueText !== "") ||
      (item.valueNumeric !== null && item.valueNumeric !== undefined);
    if (hasValue) completedCount += 1;
    else notStartedCount += 1;
  });

  /* ─── CTA 핸들러 ─── */
  const handleCtaClick = () => {
    if (!workflow) return;

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

  /* ─── modal 저장/제출 ─── */
  const handleSaveAndSubmit = async (values, files, status) => {
    if (!selectedItem || !companyId) return;

    try {
      const payload = {
        reportingYear: DEFAULT_REPORTING_YEAR,
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
        showDefaultAlert("오류", res?.error?.message || "저장에 실패했습니다.", "error");
        return;
      }

      showDefaultAlert(
        "완료",
        status === "DRAFT" ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.",
        "success"
      );
      setIsModalOpen(false);

      /* 저장 후 profile/status 재조회 */
      await fetchG0Profile();
      await fetchG0Status();
    } catch (error) {
      console.error(error);
      showDefaultAlert("오류", "처리 중 오류가 발생했습니다.", "error");
    }
  };

  /* ─── 그룹별 sub metrics ─── */
  const getSubMetrics = (metricId) => {
    return g0Items.filter((item) => item.metricId === metricId);
  };

  // Group items by metricId for the main table display
  const groupedG0Items = [];
  const metricIdSet = new Set();
  g0Items.forEach(item => {
    if (!metricIdSet.has(item.metricId)) {
      metricIdSet.add(item.metricId);
      groupedG0Items.push(item);
    }
  });

  const basisLabel =
    workflow?.reportBasisType === "CONSOLIDATED" ? "연결기준" : workflow?.reportBasisType === "ENTITY" ? "독립기준" : "미확정";

  /* ─── 로딩 상태 ─── */
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

  /* ─── 에러 상태 ─── */
  if (workflowError && g0Error) {
    return (
      <div id="ob1-page">
        <div className="ob1-state-container">
          <div className="ob1-error-banner">
            <span className="ob1-error-icon">⚠</span>
            <div>
              <p className="ob1-error-title">데이터 로드 실패</p>
              <p className="ob1-error-detail">{workflowError || g0Error}</p>
            </div>
          </div>
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

      {/* ─── 상단 통계 카드 ─── */}
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

      {/* ─── 메인 레이아웃 ─── */}
      <div className="ob1-content-layout">
        <div className="ob1-sidebar-panel">
          <div className="ob1-sidebar-title">할당 항목</div>
          <ul className="ob1-sidebar-menu">
            <li className="ob1-sidebar-menu-item active">
              1. 경영일반 - G0
            </li>
          </ul>
        </div>

        <div className="ob1-main-area">
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '16px 24px 0 24px' }}>
            <button
              className="ob1-btn-input"
              onClick={() => setIsSubTransferModalOpen(true)}
              style={{ padding: '8px 16px', background: '#f8fafc', color: '#1e293b', border: '1px solid #cbd5e1' }}
            >
              지주사 요청 확인 및 전송
            </button>
          </div>

          {activeBatchId && (
            <RollupSummaryPanel
              batchId={activeBatchId}
              onCalculated={() => {
                fetchG0Profile();
                fetchG0Status();
                fetchWorkflow();
              }}
            />
          )}

          {/* ─── G0 에러 배너 ─── */}
          {g0Error && (
            <div className="ob1-inline-error">
              <span className="ob1-error-icon">⚠</span>
              <span>{g0Error}</span>
              <button type="button" className="ob1-btn-retry" onClick={fetchG0Profile}>
                다시 시도
              </button>
            </div>
          )}

          {/* ─── G0 로딩 ─── */}
          {loadingG0 && !g0Error && (
            <div className="ob1-table-loading">
              <div className="ob1-spinner" />
              <p>G0 프로필 데이터를 불러오고 있습니다...</p>
            </div>
          )}

          {/* ─── G0 빈 상태 ─── */}
          {!loadingG0 && !g0Error && g0Items.length === 0 && (
            <div className="ob1-empty-state">
              <div className="ob1-empty-icon">📋</div>
              <p className="ob1-empty-title">G0 지표가 없습니다</p>
              <p className="ob1-empty-desc">
                아직 G0 프로필 데이터가 등록되지 않았습니다.<br />
                보고서 워크플로우를 먼저 시작해 주세요.
              </p>
            </div>
          )}

          {/* ─── G0 테이블 ─── */}
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
                    
                    // Determine status based on subMetrics
                    let allCompleted = true;
                    let anyCompleted = false;
                    const statusTargets = subMetrics.filter((sub) => isEditableItem(sub));
                    
                    statusTargets.forEach(sub => {
                      const hasValue = (sub.valueText !== null && sub.valueText !== undefined && sub.valueText !== "") ||
                                       (sub.valueNumeric !== null && sub.valueNumeric !== undefined);
                      if (hasValue) anyCompleted = true;
                      else allCompleted = false;
                    });
                    
                    const statusInfo = statusTargets.length === 0
                      ? { label: "조회/설정", cls: "draft" }
                      : allCompleted && statusTargets.length > 0
                      ? { label: "입력 완료", cls: "approved" }
                      : anyCompleted 
                        ? { label: "진행중", cls: "draft" }
                        : { label: "미입력", cls: "not-started" };

                    // Find if any sub metric has a distinct input format
                    const typeBadge = getInputTypeBadge(
                      subMetrics.find((sub) => isEditableItem(sub)) || subMetrics[0] || item
                    );

                    return (
                      <tr key={item.metricId}>
                        <td>{item.metricId}</td>
                        <td>{subMetrics.length > 1 ? `(${subMetrics.length}개 항목)` : (item.atomicMetricId || "-")}</td>
                        <td className="ob1-td-name">
                          {item.metricName || item.atomicName || "-"}
                        </td>
                        <td>
                          {typeBadge.cls ? (
                            <span className={`ob1-type-badge ${typeBadge.cls}`}>
                              {typeBadge.label}
                            </span>
                          ) : (
                            <span className="ob1-type-badge">{typeBadge.label}</span>
                          )}
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

          {/* ─── CTA ─── */}
          <div className="ob1-cta-container">
            <button
              className="ob1-btn-cta"
              onClick={handleCtaClick}
              disabled={loadingWorkflow || !workflow}
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
        </div>
      </div>

      {/* ─── Modals ─── */}
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
    </div>
  );
};

export default OnBoard;
