import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  calculateRollupBatch,
  fetchRollupBatchSources,
  fetchRollupBatchStatus,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import "@styles/onboarding1.css";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import { getFixtureRollupStatus } from "@/dev/step12UiPreview/fixtures";

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
  onCalculated,
  rollupScenario,
  rollupPurposeCode = "DMA_PRECHECK",
  metricScopeCode = "G0_02_FINANCIAL_BASIS",
  onCalculate,
}) => {
  const dispatch = useDispatch();
  const reduxStatusInfo = useSelector((state) => state.report.rollup.batchStatus);
  const batchSources = useSelector((state) => state.report.rollup.batchSources);
  const loadingStatus = useSelector((state) => state.report.loading.batchStatus);
  const loadingSources = useSelector((state) => state.report.loading.rollupBatchSources);
  const calculatingRedux = useSelector((state) => state.report.loading.calculateBatch);
  const statusError = useSelector((state) => state.report.error.batchStatus);
  const sourceError = useSelector((state) => state.report.error.rollupBatchSources);
  const [showSources, setShowSources] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);

  const statusInfo = useMemo(() => {
    if (STEP12_UI_FIXTURE_ENABLED && getFixtureRollupStatus(rollupScenario)) {
      return getFixtureRollupStatus(rollupScenario);
    }
    return reduxStatusInfo;
  }, [reduxStatusInfo, rollupScenario]);

  const fetchRollupState = useCallback(async () => {
    if (!batchId || STEP12_UI_FIXTURE_ENABLED) return;
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

  if (!batchId && !STEP12_UI_FIXTURE_ENABLED) return null;

  if ((loadingStatus || loadingSources) && !statusInfo && !STEP12_UI_FIXTURE_ENABLED) {
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
  if (activeError && !STEP12_UI_FIXTURE_ENABLED) {
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

  if (!statusInfo) return null;

  const requestedCount = numberOrZero(statusInfo.requestedCount);
  const sentCount = numberOrZero(statusInfo.sentCount);
  const pendingCount = numberOrZero(statusInfo.pendingCount);
  const calculateReadyYn = Boolean(statusInfo.calculateReadyYn);
  const dmaReadyYn = Boolean(statusInfo.dmaReadyYn);
  const reportReadyYn = Boolean(statusInfo.reportReadyYn);
  const batchStatus = String(statusInfo.batchStatus || "").toLowerCase();
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
      if (!STEP12_UI_FIXTURE_ENABLED) {
        await dispatch(calculateRollupBatch({ batchId })).unwrap();
        await Promise.all([
          dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
          dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
        ]);
      } else {
        await new Promise((resolve) => setTimeout(resolve, 600));
      }
      showDefaultAlert("성공", "데이터 취합이 완료되었습니다.", "success");
      onCalculated?.();
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "데이터 취합에 실패했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="ob1-rollup-panel ob1-rollup-panel-v2" style={{ flexDirection: "column", alignItems: "stretch" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "16px", width: "100%" }}>
        <div className="ob1-rollup-info">
          <h3 className="ob1-rollup-title">자회사 데이터 취합</h3>
          <span className="ob1-rollup-detail">
            Batch #{statusInfo.batchId || batchId} · {purposeLabel(statusInfo.rollupPurposeCode || rollupPurposeCode)}
            {metricScopeCode ? ` · ${statusInfo.metricScopeCode || metricScopeCode}` : ""}
          </span>
        </div>

        <div className="ob1-rollup-stepper" style={{ flex: 1, margin: "0 24px", justifyContent: "center" }}>
          <div className="ob1-rollup-step completed">요청 생성</div>
          <div className={`ob1-rollup-step ${calculateReadyYn ? "completed" : "active"}`}>자회사 전송</div>
          <div className={`ob1-rollup-step ${isCalculated ? "completed" : calculateReadyYn ? "active" : ""}`}>데이터 취합</div>
          <div className={`ob1-rollup-step ${dmaReadyYn || reportReadyYn ? "completed" : ""}`}>
            {rollupPurposeCode === "REPORT_DISCLOSURE" ? "보고서 준비" : "이중중대성평가 준비"}
          </div>
        </div>

        <div className="ob1-rollup-actions" style={{ display: "flex", alignItems: "center" }}>
          <button
            type="button"
            className="ob1-rollup-btn secondary"
            onClick={() => setShowSources((prev) => !prev)}
            style={{ marginRight: "8px" }}
          >
            요청 관리
          </button>
          <button
            type="button"
            className={`ob1-rollup-btn ${isCalculated ? "calculated" : calculateReadyYn ? "primary" : ""}`}
            onClick={handleCalc}
            disabled={isCalculating || !calculateReadyYn || isCalculated}
            title={!calculateReadyYn ? "자회사 데이터 전송 완료 후 계산할 수 있습니다." : ""}
          >
            {isCalculating ? "계산 중..." : isCalculated ? "데이터 취합 완료" : calculateReadyYn ? "데이터 취합 실행" : "자회사 데이터 대기"}
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: "8px", marginTop: "14px" }}>
        {[
          ["요청", requestedCount],
          ["전송", sentCount],
          ["대기", pendingCount],
          ["계산 가능", calculateReadyYn ? "Y" : "N"],
          ["상태", statusInfo.batchStatus || "-"],
        ].map(([label, value]) => (
          <div key={label} style={{ padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#fff" }}>
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

      {showSources && (
        <div style={{ marginTop: "16px", borderTop: "1px solid #e2e8f0", paddingTop: "12px", width: "100%" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <strong style={{ color: "#0f172a" }}>자회사 전송 현황</strong>
            {(loadingSources || loadingStatus) && <span style={{ fontSize: "0.8rem", color: "#64748b" }}>갱신 중...</span>}
          </div>
          {batchSources.length === 0 ? (
            <div style={{ padding: "18px", border: "1px dashed #cbd5e1", borderRadius: "8px", color: "#64748b", textAlign: "center" }}>
              표시할 자회사 전송 현황이 없습니다.
            </div>
          ) : (
            <div className="ob1-table-container" style={{ maxHeight: "260px", overflow: "auto" }}>
              <table className="ob1-table">
                <thead>
                  <tr>
                    <th>자회사</th>
                    <th>준비 상태</th>
                    <th>승인 상태</th>
                    <th>전송 상태</th>
                    <th>승인 Atomic</th>
                    <th>누락</th>
                    <th>전송/수신</th>
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
                        <td>
                          <div style={{ display: "flex", flexDirection: "column", gap: "2px", fontSize: "0.78rem" }}>
                            <span>전송: {source.sentAt || "-"}</span>
                            <span>수신: {source.receivedAt || "-"}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RollupSummaryPanel;
