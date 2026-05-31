import { useState, useEffect } from "react";
import { getBatchStatus, calcBatch } from "@/apis/report";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import "@styles/onboarding1.css";

/**
 * RollupSummaryPanel
 *
 * Backend DTO fields:
 *   requestedCount, sentCount, pendingCount,
 *   calculateReadyYn, dmaReadyYn, batchStatus
 *
 * calculateReadyYn=false → 계산 버튼 비활성화
 */
const RollupSummaryPanel = ({ batchId, onCalculated }) => {
  const [statusInfo, setStatusInfo] = useState(null);
  const [calculating, setCalculating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!batchId) return;
    fetchStatus();
  }, [batchId]);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getBatchStatus(batchId);
      const isFailed =
        res?.status === false || res?.success === false || !res?.data;

      if (isFailed) {
        setStatusInfo(null);
        setError(res?.error?.message || "배치 상태 조회에 실패했습니다.");
        return;
      }
      setStatusInfo(res.data);
    } catch (err) {
      console.error(err);
      setStatusInfo(null);
      setError("배치 상태 조회에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleCalc = async () => {
    if (!statusInfo?.calculateReadyYn) {
      showDefaultAlert(
        "계산 불가",
        "모든 자회사 데이터가 수집되지 않아 계산할 수 없습니다.",
        "warning"
      );
      return;
    }

    setCalculating(true);
    try {
      const res = await calcBatch(batchId);
      const isFailed =
        res?.status === false || res?.success === false;

      if (!isFailed) {
        showDefaultAlert("성공", "롤업 계산이 완료되었습니다.", "success");
        fetchStatus();
        onCalculated?.();
      } else {
        showDefaultAlert("오류", res?.error?.message || "계산에 실패했습니다.", "error");
      }
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", "계산에 실패했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  /* loading */
  if (loading) {
    return (
      <div className="ob1-rollup-panel">
        <div className="ob1-table-loading" style={{ padding: "16px" }}>
          <div className="ob1-spinner" style={{ width: "20px", height: "20px" }} />
          <p style={{ margin: 0, fontSize: "0.85rem" }}>롤업 현황 조회 중...</p>
        </div>
      </div>
    );
  }

  /* error */
  if (error) {
    return (
      <div className="ob1-rollup-panel">
        <div className="ob1-inline-error">
          <span className="ob1-error-icon">⚠</span>
          <span>{error}</span>
          <button type="button" className="ob1-btn-retry" onClick={fetchStatus}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!statusInfo) return null;

  const { requestedCount = 0, sentCount = 0, pendingCount = 0, calculateReadyYn, dmaReadyYn, batchStatus } = statusInfo;
  const progressPercent = requestedCount > 0 ? Math.round((sentCount / requestedCount) * 100) : 0;
  const isCalculated = String(batchStatus || "").toLowerCase() === "completed";

  return (
    <div className="ob1-rollup-panel">
      <div className="ob1-rollup-info">
        <h3 className="ob1-rollup-title">자회사 G0 데이터 롤업 현황</h3>
        <span className="ob1-rollup-detail">
          전송 완료: {sentCount} / {requestedCount} 개사
          {pendingCount > 0 && ` (대기: ${pendingCount})`}
        </span>
        {dmaReadyYn === true && (
          <span className="ob1-rollup-badge ready">DMA 준비 완료</span>
        )}
        {dmaReadyYn === false && (
          <span className="ob1-rollup-badge not-ready">DMA 미준비</span>
        )}
      </div>

      <div className="ob1-rollup-actions">
        <div className="ob1-rollup-progress-bar">
          <div
            className="ob1-rollup-progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="ob1-rollup-percent">{progressPercent}%</span>
        <button
          className={`ob1-rollup-btn ${isCalculated ? "calculated" : ""}`}
          onClick={handleCalc}
          disabled={calculating || !calculateReadyYn || isCalculated}
          title={!calculateReadyYn ? "모든 자회사 데이터가 수집되어야 계산 가능합니다" : ""}
        >
          {calculating
            ? "계산 중..."
            : isCalculated
              ? "계산 완료"
              : "롤업 계산 실행"}
        </button>
      </div>
    </div>
  );
};

export default RollupSummaryPanel;
