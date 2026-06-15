import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  calculateRollupBatch,
  fetchRollupBatchSources,
  fetchRollupBatchStatus,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import "@styles/onboarding1.css";
import "@styles/onboardingModal.css";

const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "이중중대성평가 사전 계산";
  return value || "-";
};

const readinessLabel = (status) => {
  const value = String(status || "").toUpperCase();
  if (value === "READY") return "전송 가능";
  if (value === "PARTIAL") return "입력 진행중";
  if (value === "NOT_STARTED") return "미입력";
  return status || "-";
};

const transferLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "received") return "수신 완료";
  if (value === "sent") return "전송 완료";
  if (value === "not_sent") return "미전송";
  return status || "-";
};

const approvalLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "approved") return "승인 완료";
  if (value === "reviewed") return "검토 완료";
  if (value === "rejected") return "반려";
  if (value === "pending" || value === "submitted") return "승인 대기";
  return status || "-";
};

const numberOrZero = (value) => Number(value || 0);

const RollupSummaryPanel = ({
  batchId,
  sourceCycleId,
  onCalculated,
  rollupPurposeCode = "DMA_PRECHECK",
  metricScopeCode = "G0_02_FINANCIAL_BASIS",
  onCalculate,
  workflow,
  onCtaClick,
  onSendSource,
}) => {
  const dispatch = useDispatch();
  const reduxStatusInfo = useSelector((state) => state.report.rollup.batchStatus);
  const batchSources = useSelector((state) => state.report.rollup.batchSources);
  const loadingStatus = useSelector((state) => state.report.loading.batchStatus);
  const loadingSources = useSelector((state) => state.report.loading.rollupBatchSources);
  const calculatingRedux = useSelector((state) => state.report.loading.calculateBatch);
  const statusError = useSelector((state) => state.report.error.batchStatus);
  const sourceError = useSelector((state) => state.report.error.rollupBatchSources);
  const [showManageModal, setShowManageModal] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);

  const statusInfo = useMemo(() => reduxStatusInfo, [reduxStatusInfo]);
  const canCreateRequest =
    workflow?.nextAction === "REQUEST_ROLLUP" ||
    (
      rollupPurposeCode === "REPORT_DISCLOSURE" &&
      metricScopeCode === "SELECTED_DISCLOSURE" &&
      sourceCycleId
    );

  const fetchRollupState = useCallback(async () => {
    if (!batchId) return;
    setError(null);
    try {
      await Promise.all([
        dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
        dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
      ]);
    } catch (err) {
      console.error(err);
      setError(err?.message || "데이터 취합 상태 조회에 실패했습니다.");
    }
  }, [batchId, dispatch]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active) fetchRollupState();
    });
    return () => {
      active = false;
    };
  }, [fetchRollupState]);

  if (!batchId && !canCreateRequest) return null;

  if (batchId && (loadingStatus || loadingSources) && !statusInfo) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-table-loading" style={{ padding: "16px", display: "flex", gap: "8px", alignItems: "center" }}>
          <div className="ob1-spinner" style={{ width: "20px", height: "20px" }} />
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#475569" }}>데이터 취합 상태를 불러오고 있습니다.</p>
        </div>
      </div>
    );
  }

  const activeError = error || statusError?.message || sourceError?.message;
  if (activeError) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-inline-error">
          <span className="ob1-error-icon">!</span>
          <span>{activeError}</span>
          <button type="button" className="ob1-btn-retry" onClick={fetchRollupState}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (batchId && !statusInfo) return null;

  const requestedCount = numberOrZero(statusInfo?.requestedCount);
  const sentCount = numberOrZero(statusInfo?.sentCount);
  const pendingCount = numberOrZero(statusInfo?.pendingCount);
  const calculateReadyYn = Boolean(statusInfo?.calculateReadyYn);
  const dmaReadyYn = Boolean(statusInfo?.dmaReadyYn);
  const reportReadyYn = Boolean(statusInfo?.reportReadyYn);
  const batchStatus = String(statusInfo?.batchStatus || "").toLowerCase();
  const isCalculated = batchStatus === "completed" || batchStatus === "calculated";
  const isCalculating = calculating || calculatingRedux;

  const handleCalc = async () => {
    if (onCalculate) {
      onCalculate(batchId);
      return;
    }

    if (isCalculated) return;

    if (!calculateReadyYn) {
      showDefaultAlert(
        "계산 대기",
        "자회사 데이터 전송 완료 후 계산할 수 있습니다.",
        "warning"
      );
      return;
    }

    setCalculating(true);
    try {
      await dispatch(calculateRollupBatch({ batchId })).unwrap();
      await Promise.all([
        dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
        dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
      ]);
      showDefaultAlert("성공", "데이터 취합이 완료되었습니다.", "success");
      onCalculated?.();
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "데이터 취합에 실패했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  let btnText = "자회사 데이터 대기";
  let btnClass = "";
  let btnDisabled = true;
  let btnAction = () => {};

  const nextAction = workflow?.nextAction;
  if (nextAction === "REQUEST_ROLLUP") {
    btnText = "자회사 데이터 요청하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = onCtaClick;
  } else if (nextAction === "WAIT_ROLLUP") {
    if (isCalculating) {
      btnText = "계산 중...";
      btnDisabled = true;
    } else if (isCalculated) {
      btnText = "데이터 취합 완료";
      btnClass = "calculated";
      btnDisabled = true;
    } else if (calculateReadyYn) {
      btnText = "데이터 취합 실행";
      btnClass = "primary";
      btnDisabled = false;
      btnAction = handleCalc;
    } else {
      btnText = "자회사 데이터 대기";
      btnDisabled = true;
    }
  } else if (nextAction === "START_DMA") {
    btnText = "이중중대성평가 진행하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = onCtaClick;
  } else {
    btnText = isCalculating ? "계산 중..." : isCalculated ? "데이터 취합 완료" : calculateReadyYn ? "데이터 취합 실행" : "자회사 데이터 대기";
    btnDisabled = isCalculating || (!calculateReadyYn && !isCalculated);
    if (isCalculated) btnClass = "calculated";
    else if (calculateReadyYn) btnClass = "primary";
    btnAction = handleCalc;
  }

  if (!batchId && canCreateRequest) {
    btnText = "자회사 데이터 요청하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = onCtaClick;
  } else if (batchId && isCalculated) {
    btnText = "데이터 취합 완료";
    btnClass = "calculated";
    btnDisabled = true;
  } else if (batchId && nextAction === "WAIT_ROLLUP" && calculateReadyYn) {
    btnText = isCalculating ? "계산 중..." : "데이터 취합 실행";
    btnClass = "primary";
    btnDisabled = isCalculating;
    btnAction = handleCalc;
  } else if (batchId && nextAction === "WAIT_ROLLUP") {
    btnText = "자회사 데이터 대기";
    btnClass = "";
    btnDisabled = true;
  }

  const finalStepLabel =
    rollupPurposeCode === "REPORT_DISCLOSURE"
      ? "보고서 생성 준비"
      : "이중중대성평가 준비";

  return (
    <div className="ob1-rollup-panel ob1-rollup-panel-v2" style={{ flexDirection: "column", alignItems: "stretch" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "16px", width: "100%" }}>
        <div className="ob1-rollup-info">
          <h3 className="ob1-rollup-title">자회사 데이터 취합</h3>

        </div>

        <div className="ob1-rollup-stepper" style={{ flex: 1, margin: "0 24px", justifyContent: "center" }}>
          <div className={`ob1-rollup-step ${batchId ? "completed" : "active"}`}>요청 생성</div>
          <div className={`ob1-rollup-step ${calculateReadyYn ? "completed" : batchId ? "active" : ""}`}>자회사 전송</div>
          <div className={`ob1-rollup-step ${isCalculated ? "completed" : calculateReadyYn ? "active" : ""}`}>데이터 취합</div>
          <div className={`ob1-rollup-step ${nextAction === "START_DMA" ? "active" : dmaReadyYn || reportReadyYn ? "completed" : ""}`}>
            {finalStepLabel}
          </div>
        </div>

        <div className="ob1-rollup-actions" style={{ display: "flex", alignItems: "center" }}>
          {batchId && (
            <button
              type="button"
              className="ob1-rollup-btn secondary"
              onClick={() => setShowManageModal(true)}
              style={{ marginRight: "8px" }}
            >
              요청 관리
            </button>
          )}
          <button
            type="button"
            className={`ob1-rollup-btn ${btnClass}`}
            onClick={btnAction}
            disabled={btnDisabled}
            title={btnDisabled && !isCalculating && !isCalculated && nextAction === "WAIT_ROLLUP" ? "자회사 데이터 전송 완료 후 진행할 수 있습니다." : ""}
          >
            {btnText}
          </button>
        </div>
      </div>

      {showManageModal && createPortal(
        <div className="ob-modal-overlay" onClick={() => setShowManageModal(false)}>
          <div className="ob-modal-shell" onClick={e => e.stopPropagation()} style={{ maxWidth: "900px", width: "90%" }}>
            <div className="ob-modal-header" style={{ padding: "20px 24px" }}>
              <h2 className="ob-modal-title" style={{ fontSize: "1.25rem" }}>자회사 데이터 취합 현황</h2>
              <button
                type="button"
                className="ob1-btn-close"
                onClick={() => setShowManageModal(false)}
                style={{ border: "none", background: "none", fontSize: "1.5rem", cursor: "pointer", color: "#64748b" }}
              >
                ×
              </button>
            </div>
            <div className="ob-modal-body" style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: "8px" }}>
                {[
                  ["요청", requestedCount],
                  ["전송", sentCount],
                  ["대기", pendingCount],
                  ["계산 가능", calculateReadyYn ? "Y" : "N"],
                  ["상태", statusInfo.batchStatus || "-"],
                ].map(([label, value]) => (
                  <div key={label} style={{ padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#f8fafc" }}>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: "4px" }}>{label}</div>
                    <div style={{ fontWeight: 700, color: "#0f172a" }}>{value}</div>
                  </div>
                ))}
              </div>

              {!calculateReadyYn && !isCalculated && (
                <div style={{ marginTop: "10px", fontSize: "0.82rem", color: "#64748b" }}>
                  자회사 데이터 전송 완료 후 계산할 수 있습니다.
                </div>
              )}

              <div style={{ marginTop: "24px", borderTop: "1px solid #e2e8f0", paddingTop: "16px", width: "100%" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <strong style={{ color: "#0f172a" }}>자회사 전송 현황</strong>
                  {(loadingSources || loadingStatus) && <span style={{ fontSize: "0.8rem", color: "#64748b" }}>갱신 중...</span>}
                </div>
                {batchSources.length === 0 ? (
                  <div style={{ padding: "18px", border: "1px dashed #cbd5e1", borderRadius: "8px", color: "#64748b", textAlign: "center" }}>
                    표시할 자회사 전송 현황이 없습니다.
                  </div>
                ) : (
                  <div className="ob1-table-container" style={{ maxHeight: "300px", overflow: "auto" }}>
                    <table className="ob1-table">
                      <thead>
                        <tr>
                          <th>자회사</th>
                          <th>준비 상태</th>
                          <th>승인 상태</th>
                          <th>전송 상태</th>
                          <th>승인 Atomic</th>
                          <th>누락</th>
                        </tr>
                      </thead>
                      <tbody>
                        {batchSources.map((source) => {
                          const required = source.requiredAtomicCount ?? source.requiredCount ?? 0;
                          const approved = source.currentApprovedAtomicCount ?? source.approvedAtomicCount ?? 0;
                          const missing = source.currentMissingAtomicCount ?? source.missingAtomicCount ?? source.missingAtomicMetricIds?.length ?? 0;
                          return (
                            <tr key={source.sourceCompanyId || source.companyId}>
                              <td>{source.sourceCompanyName || source.companyName || source.sourceCompanyId || source.companyId}</td>
                              <td>{readinessLabel(source.readinessStatus)}</td>
                              <td>{approvalLabel(source.approvalStatus)}</td>
                              <td>{transferLabel(source.transferStatus)}</td>
                              <td>{approved} / {required}</td>
                              <td>{missing}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default RollupSummaryPanel;
