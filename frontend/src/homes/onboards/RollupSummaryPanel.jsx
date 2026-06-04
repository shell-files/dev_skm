import { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  calculateRollupBatch,
  fetchRollupBatchStatus,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import "@styles/onboarding1.css";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import { getFixtureRollupStatus } from "@/dev/step12UiPreview/fixtures";

const RollupSummaryPanel = ({ batchId, onCalculated, rollupScenario, onManageRequests, onSendSource, onCalculate }) => {
  const dispatch = useDispatch();
  const reduxStatusInfo = useSelector((state) => state.report.rollup.batchStatus);
  const loading = useSelector((state) => state.report.loading.batchStatus);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!batchId) return;
    fetchStatus();
  }, [batchId]);

  const fetchStatus = async () => {
    setError(null);
    try {
      await dispatch(fetchRollupBatchStatus({ batchId })).unwrap();
    } catch (err) {
      console.error(err);
      setError(err?.message || "배치 상태 조회에 실패했습니다.");
    }
  };

  const handleCalc = async () => {
    if (onCalculate) {
      onCalculate(batchId);
      return;
    }

    const activeStatus = STEP12_UI_FIXTURE_ENABLED && getFixtureRollupStatus(rollupScenario) 
      ? getFixtureRollupStatus(rollupScenario) 
      : reduxStatusInfo;
      
    if (!activeStatus?.calculateReadyYn) {
      showDefaultAlert(
        "계산 불가",
        "모든 자회사 데이터가 수집되지 않아 계산할 수 없습니다.",
        "warning"
      );
      return;
    }

    setCalculating(true);
    try {
      if (!STEP12_UI_FIXTURE_ENABLED) {
        await dispatch(calculateRollupBatch({ batchId })).unwrap();
      } else {
        await new Promise(r => setTimeout(r, 1000));
      }
      showDefaultAlert("성공", "롤업 계산이 완료되었습니다.", "success");
      fetchStatus();
      onCalculated?.();
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "계산에 실패했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  const handleManageRequests = () => {
    if (onManageRequests) {
      onManageRequests();
      return;
    }
  
    if (STEP12_UI_FIXTURE_ENABLED) {
      showDefaultAlert(
        "관리",
        "자회사 요청 관리 모달이 호출됩니다.",
        "info"
      );
    }
  };

  const handleSendSource = () => {
    if (onSendSource) {
      onSendSource(batchId);
      return;
    }
  
    if (STEP12_UI_FIXTURE_ENABLED) {
      showDefaultAlert(
        "전송",
        "지주사 전송 기능은 Backend 연결 시 구현됩니다.",
        "info"
      );
    }
  };

  const statusInfo = STEP12_UI_FIXTURE_ENABLED && getFixtureRollupStatus(rollupScenario) 
    ? getFixtureRollupStatus(rollupScenario) 
    : reduxStatusInfo;

  if (loading && !STEP12_UI_FIXTURE_ENABLED) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-table-loading" style={{ padding: "16px", display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div className="ob1-spinner" style={{ width: "20px", height: "20px" }} />
          <p style={{ margin: 0, fontSize: "0.85rem", color: '#475569' }}>진행 중인 롤업 배치를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error && !STEP12_UI_FIXTURE_ENABLED) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-inline-error">
          <span className="ob1-error-icon">!</span>
          <span>{error}</span>
          <button type="button" className="ob1-btn-retry" onClick={fetchStatus}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!statusInfo) return null;

  const { persona, parentCompanyName, reportingYear, sendReadyYn, missingAtomicMetricIds, requestedCount = 0, sentCount = 0, pendingCount = 0, calculateReadyYn, dmaReadyYn, batchStatus } = statusInfo;
  const isCalculated = String(batchStatus || "").toLowerCase() === "completed";

  if (persona === 'SUBSIDIARY') {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-rollup-info">
          <h3 className="ob1-rollup-title">지주사 데이터 전송</h3>
          <span className="ob1-rollup-detail">요청: {parentCompanyName || 'SKM 지주사'} | 보고연도: {reportingYear || 2026}</span>
        </div>
        
        <div className="ob1-rollup-stepper" style={{ flex: 1, margin: '0 24px', justifyContent: 'center' }}>
          <div className="ob1-rollup-step completed">요청 수신</div>
          <div className={`ob1-rollup-step ${sendReadyYn ? 'completed' : 'active'}`}>데이터 입력</div>
          <div className={`ob1-rollup-step ${!sendReadyYn ? '' : 'active'}`}>승인 대기</div>
          <div className="ob1-rollup-step">전송 완료</div>
        </div>

        <div className="ob1-rollup-actions" style={{ display: 'flex', alignItems: 'center' }}>
          {!sendReadyYn && missingAtomicMetricIds?.length > 0 && (
             <span style={{ fontSize: '0.75rem', color: '#ef4444', marginRight: '12px', fontWeight: 600 }}>누락: {missingAtomicMetricIds.length}건</span>
          )}
          <button
            className={`ob1-rollup-btn ${sendReadyYn ? 'primary' : ''}`}
            onClick={handleSendSource}
            disabled={!sendReadyYn}
            title={!sendReadyYn ? "필수값이 누락되어 전송할 수 없습니다." : ""}
          >
            지주사에 전송
          </button>
        </div>
      </div>
    );
  }

  const progressPercent = requestedCount > 0 ? Math.round((sentCount / requestedCount) * 100) : 0;
  
  return (
    <div className="ob1-rollup-panel ob1-rollup-panel-v2">
      <div className="ob1-rollup-info">
        <h3 className="ob1-rollup-title">자회사 데이터 롤업</h3>
        <span className="ob1-rollup-detail">수집 현황: {sentCount} / {requestedCount}개사 완료</span>
      </div>

      <div className="ob1-rollup-stepper" style={{ flex: 1, margin: '0 24px', justifyContent: 'center' }}>
        <div className="ob1-rollup-step completed">수집 시작</div>
        <div className={`ob1-rollup-step ${calculateReadyYn ? 'completed' : 'active'}`}>전송 대기</div>
        <div className={`ob1-rollup-step ${isCalculated ? 'completed' : (calculateReadyYn ? 'active' : '')}`}>롤업 계산</div>
        <div className={`ob1-rollup-step ${dmaReadyYn ? 'completed' : ''}`}>DMA 준비</div>
      </div>

      <div className="ob1-rollup-actions" style={{ display: 'flex', alignItems: 'center' }}>
        <button
          className="ob1-rollup-btn secondary"
          onClick={handleManageRequests}
          style={{ marginRight: '8px' }}
        >
          요청 관리
        </button>
        <button
          className={`ob1-rollup-btn ${isCalculated ? "calculated" : (calculateReadyYn ? "primary" : "")}`}
          onClick={handleCalc}
          disabled={calculating || !calculateReadyYn || isCalculated}
          title={!calculateReadyYn ? "모든 자회사 데이터가 수집되어야 계산 가능합니다." : ""}
        >
          {calculating ? "계산 중..." : isCalculated ? "계산 완료" : "롤업 계산 실행"}
        </button>
      </div>
    </div>
  );
};

export default RollupSummaryPanel;
