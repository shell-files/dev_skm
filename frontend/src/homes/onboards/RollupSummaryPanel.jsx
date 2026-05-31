import { useState, useEffect } from "react";
import { getStatus, calcBatch } from "@/apis/report";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const RollupSummaryPanel = ({ batchId, onCalculated }) => {
  const [statusInfo, setStatusInfo] = useState(null);
  const [calculating, setCalculating] = useState(false);

  useEffect(() => {
    if (!batchId) return;
    fetchStatus();
  }, [batchId]);

  const fetchStatus = async () => {
    try {
      const res = await getStatus(batchId);
      if (res?.data) {
        setStatusInfo(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch rollup status", e);
      // Fallback 제거
    }
  };

  const handleCalc = async () => {
    setCalculating(true);
    try {
      const res = await calcBatch(batchId);
      if (res?.status) {
        showDefaultAlert("성공", "연결 집계가 완료되었습니다.", "success");
        fetchStatus();
        onCalculated?.();
      } else {
        showDefaultAlert("오류", "계산에 실패했습니다.", "error");
      }
    } catch (e) {
      console.error(e);
      showDefaultAlert("오류", "연결 집계 중 오류가 발생했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  if (!statusInfo) return null;

  const total = statusInfo.requestedCount || 0;
  const completed = statusInfo.sentCount || 0;
  const pending = statusInfo.pendingCount || 0;
  const progressPercent = total === 0 ? 0 : Math.round((completed / total) * 100);
  const canCalculate = statusInfo.calculateReadyYn === true;
  const isCompleted = String(statusInfo.batchStatus || '').toLowerCase() === 'completed';

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '24px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#1e293b' }}>
          자회사 G0 데이터 연결 집계 현황
        </h3>
        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
          요청 대상 {total}개 / 수신 완료 {completed}개 / 대기 {pending}개 ({progressPercent}%)
        </span>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ width: '150px', height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ width: `${progressPercent}%`, height: '100%', background: '#3b82f6', transition: 'width 0.3s' }}></div>
        </div>
        <button 
          style={{ 
            padding: '8px 16px', 
            background: isCompleted ? '#10b981' : (canCalculate && !calculating ? '#1d4ed8' : '#94a3b8'), 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px',
            cursor: (isCompleted || !canCalculate || calculating) ? 'not-allowed' : 'pointer',
            opacity: (isCompleted || !canCalculate || calculating) ? 0.7 : 1
          }}
          onClick={handleCalc}
          disabled={isCompleted || !canCalculate || calculating}
        >
          {calculating ? "계산 중..." : isCompleted ? "계산 완료" : "연결 집계 실행"}
        </button>
      </div>
    </div>
  );
};

export default RollupSummaryPanel;
