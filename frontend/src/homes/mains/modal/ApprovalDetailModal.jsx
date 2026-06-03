import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

export default function ApprovalDetailModal({
  isOpen,
  onClose,
  metricItem,
  viewerRole,
  hasConsultant = false,
  onReview,
  onApprove,
  onReject,
}) {
  const [rejectReason, setRejectReason] = useState('');
  
  useEffect(() => {
    if (isOpen) {
      setRejectReason('');
    }
  }, [isOpen]);

  if (!isOpen || !metricItem) return null;
  
  const isConsultant = viewerRole === '컨설턴트' || viewerRole === 'CONSULTANT';
  const isReviewed = metricItem.reviewStatus === 'REVIEWED';
  const canApprove = isConsultant ? false : (!hasConsultant || isReviewed);
  const metricId = metricItem.metricId || metricItem.id;
  
  return createPortal(
    <div className="ob-modal-overlay" onClick={onClose} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="ob-modal-shell ob-approval-modal" onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: '12px', width: '100%', maxWidth: '700px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)' }}>
        <div className="ob-modal-header" style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="ob-modal-title" style={{ fontSize: '1.1rem', margin: 0, color: '#1e293b' }}>데이터 상세 보기</h2>
          <button type="button" aria-label="승인 상세 모달 닫기" className="ob1-btn-close" onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b' }}>×</button>
        </div>
        
        <div className="ob-modal-body" style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
          <div style={{ marginBottom: '24px', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#475569', minWidth: '80px', fontSize: '0.9rem' }}>지표명</span>
              <span style={{ color: '#1e293b', fontSize: '0.9rem' }}>{metricItem.metricName || metricItem.checklistQuestion || '-'}</span>
            </div>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#475569', minWidth: '80px', fontSize: '0.9rem' }}>Metric ID</span>
              <span style={{ color: '#1e293b', fontSize: '0.9rem' }}>{metricItem.metricId || metricItem.id || '-'}</span>
            </div>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#475569', minWidth: '80px', fontSize: '0.9rem' }}>담당자</span>
              <span style={{ color: '#1e293b', fontSize: '0.9rem' }}>{metricItem.assigneeName || metricItem.userName || '미지정'}</span>
            </div>
            <div style={{ display: 'flex', gap: '16px' }}>
              <span style={{ fontWeight: 600, color: '#475569', minWidth: '80px', fontSize: '0.9rem' }}>제출일</span>
              <span style={{ color: '#1e293b', fontSize: '0.9rem' }}>{metricItem.submittedAt || '-'}</span>
            </div>
          </div>
          
          <div style={{ marginBottom: '24px', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left' }}>
              <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                <tr>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>입력 항목</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>입력값</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: '#475569' }}>단위</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '12px 16px', color: '#1e293b' }}>{metricItem.metricName || '주요 입력값'}</td>
                  <td style={{ padding: '12px 16px', color: '#1e293b', fontWeight: 600 }}>{metricItem.value ?? "-"}</td>
                  <td style={{ padding: '12px 16px', color: '#64748b' }}>{metricItem.unit ?? "-"}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <h4 style={{ fontSize: '0.95rem', marginBottom: '8px', color: '#1e293b' }}>증빙 자료</h4>
            <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px dashed #cbd5e1', fontSize: '0.85rem', color: '#64748b', textAlign: 'center' }}>
              첨부된 파일이 없습니다.
            </div>
          </div>

          <div style={{ marginBottom: '8px' }}>
            <h4 style={{ fontSize: '0.95rem', marginBottom: '8px', color: '#1e293b' }}>반려 사유 입력</h4>
            <textarea
              style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #cbd5e1', minHeight: '80px', resize: 'vertical', fontSize: '0.9rem', fontFamily: 'inherit' }}
              placeholder="반려 시 사유를 입력해 주세요."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </div>
        </div>
        
        <div className="ob-modal-footer" style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '8px', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px' }}>
          <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#fff', color: '#475569', cursor: 'pointer', fontWeight: 600 }}>닫기</button>
          
          <button 
            type="button" 
            className="ob-btn" 
            style={{ padding: '8px 16px', borderRadius: '6px', background: '#fff', border: '1px solid #fecaca', color: '#dc2626', cursor: rejectReason.trim() ? 'pointer' : 'not-allowed', fontWeight: 600, opacity: rejectReason.trim() ? 1 : 0.5 }}
            onClick={() => onReject?.({ metricId, commentText: rejectReason })}
            disabled={!rejectReason.trim()}
            title={!rejectReason.trim() ? "반려 사유를 입력해 주세요." : ""}
          >
            반려
          </button>
          
          {isConsultant ? (
            <button 
              type="button" 
              className="ob-btn ob-btn-primary" 
              style={{ padding: '8px 16px', borderRadius: '6px', background: '#2563eb', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
              onClick={() => onReview?.({ metricId, commentText: "" })}
            >
              검토 완료
            </button>
          ) : (
            <button 
              type="button" 
              className="ob-btn ob-btn-primary" 
              style={{ padding: '8px 16px', borderRadius: '6px', background: canApprove ? '#059669' : '#94a3b8', border: 'none', color: '#fff', cursor: canApprove ? 'pointer' : 'not-allowed', fontWeight: 600 }}
              onClick={() => onApprove?.({ metricId, commentText: "" })}
              disabled={!canApprove}
              title={!canApprove ? '컨설턴트 검토가 완료되어야 승인할 수 있습니다.' : ''}
            >
              최종 승인
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
