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
