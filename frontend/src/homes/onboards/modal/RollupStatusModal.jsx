<<<<<<< HEAD
/**
 * RollupStatusModal.jsx
 * 레이어: Component (onboards/modal)
 * 역할: 자회사 데이터 취합 현황을 모달 형태로 표시하는 래퍼 — 내부에서 RollupSummaryPanel을 렌더링
 *
 * Props:
 *   isOpen — 모달 표시 여부
 *   onClose — 모달 닫기 핸들러
 *   activeBatchId — 조회할 롤업 배치 ID
 *   onCalculated — 데이터 취합 완료 후 콜백
 *   rollupPurposeCode — 롤업 목적 코드
 *   metricScopeCode — 지표 범위 코드
 *   rollupScenario — 롤업 시나리오 정보
 *   onSendSource — 데이터 전송 핸들러
 *
 * 의존 컴포넌트:
 *   RollupSummaryPanel — 자회사 데이터 취합 현황 패널
 */
=======
>>>>>>> origin/skm_test
import React from 'react';
import { createPortal } from 'react-dom';
import RollupSummaryPanel from '../RollupSummaryPanel';
import '@styles/onboardingModal.css';

export default function RollupStatusModal({
  isOpen,
  onClose,
  activeBatchId,
  onCalculated,
  rollupPurposeCode,
  metricScopeCode,
  rollupScenario,
  onSendSource,
}) {
  if (!isOpen) return null;

  return createPortal(
    <div className="ob-modal-overlay" onClick={onClose}>
      <div 
        className="ob-modal-shell" 
        onClick={e => e.stopPropagation()} 
        style={{ maxWidth: '800px', width: '90%' }}
      >
        <div className="ob-modal-header" style={{ padding: '20px 24px' }}>
          <h2 className="ob-modal-title" style={{ fontSize: '1.25rem' }}>자회사 데이터 취합 현황</h2>
          <button 
            type="button" 
            aria-label="모달 닫기" 
            className="ob1-btn-close" 
            onClick={onClose} 
            style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b' }}
          >
            ×
          </button>
        </div>
        
        <div className="ob-modal-body" style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
          <RollupSummaryPanel
            batchId={activeBatchId}
            onCalculated={onCalculated}
            rollupPurposeCode={rollupPurposeCode}
            metricScopeCode={metricScopeCode}
            rollupScenario={rollupScenario}
            onSendSource={onSendSource}
          />
        </div>
      </div>
    </div>,
    document.body
  );
}
