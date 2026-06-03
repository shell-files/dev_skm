import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import '@styles/onboardingModal.css';

export default function MetricAssignmentModal({
  isOpen,
  mode = 'single',
  selectedMetricIds = [],
  currentAssignment = {},
  isSubmitting = false,
  previewResult = null,
  onClose,
  onSubmit,
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [dueDate, setDueDate] = useState('');

  useEffect(() => {
    if (isOpen) {
      setName(currentAssignment?.assigneeName || '');
      setEmail(currentAssignment?.assigneeEmail || '');
      setDueDate(currentAssignment?.submissionDueDate || '');
    }
  }, [isOpen, currentAssignment]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit?.({
      metricIds: selectedMetricIds,
      assigneeName: name,
      assigneeEmail: email,
      submissionDueDate: dueDate,
    });
  };

  const renderPreview = () => {
    if (!previewResult) return null;
    return (
      <div className="ob-assignment-preview">
        {previewResult.mailType === 'EXISTING' ? (
          <div className="ob-assignment-success">
            담당자 지정이 완료되었습니다.<br />
            기존 계정으로 담당자 지정 알림 메일을 발송했습니다.
          </div>
        ) : (
          <div className="ob-assignment-success">
            담당자 지정이 완료되었습니다.<br />
            미가입 사용자에게 회원가입 초대 메일을 발송했습니다.
          </div>
        )}
      </div>
    );
  };

  return createPortal(
    <div className="ob-modal-overlay" onClick={onClose}>
      <div className="ob-modal-shell ob-assignment-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="ob-modal-header" style={{ padding: '20px 24px' }}>
          <h2 className="ob-modal-title" style={{ fontSize: '1.1rem' }}>담당자 지정</h2>
          <button type="button" className="ob1-btn-close" onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b' }}>×</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div className="ob-modal-body" style={{ padding: '20px 24px', flex: 1, overflowY: 'auto' }}>
            <p className="ob-assignment-info" style={{ color: '#475569', fontSize: '0.9rem', marginBottom: '20px' }}>
              선택한 지표의 입력 담당자를 지정합니다.<br />
              담당자 계정 유무에 따라 지정 알림 또는 회원가입 초대 메일이 발송됩니다.
            </p>

            <div style={{ marginBottom: '20px', padding: '12px', background: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px' }}>대상 지표</div>
              {mode === 'single' ? (
                <div style={{ fontWeight: 600, color: '#1e293b' }}>{selectedMetricIds[0]}</div>
              ) : (
                <>
                  <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>선택한 {selectedMetricIds.length}개 metric_id</div>
                  <div style={{ maxHeight: '100px', overflowY: 'auto', fontSize: '0.85rem', color: '#475569', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {selectedMetricIds.map(id => <div key={id}>{id}</div>)}
                  </div>
                </>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>담당자 이름</label>
                <input type="text" className="ob-table-input ob-assignment-field" value={name} onChange={e => setName(e.target.value)} placeholder="예: 최수아" required />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>담당자 이메일</label>
                <input type="email" className="ob-table-input ob-assignment-field" value={email} onChange={e => setEmail(e.target.value)} placeholder="sua@company.com" required />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>제출 기한</label>
                <input type="date" className="ob-table-input ob-assignment-field" value={dueDate} onChange={e => setDueDate(e.target.value)} />
              </div>
            </div>

            <div style={{ marginTop: '20px', fontSize: '0.85rem', color: '#64748b', background: '#f1f5f9', padding: '12px', borderRadius: '6px' }}>
              기존 계정이 확인되면 담당자 지정 알림 메일이 발송됩니다.<br />
              미가입자는 회원가입 초대 메일을 받습니다.
            </div>

            {renderPreview()}
          </div>

          <div className="ob-modal-footer" style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', background: '#f8fafc' }}>
            <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose} disabled={isSubmitting}>취소</button>
            <button type="submit" className="ob-btn ob-btn-primary" disabled={isSubmitting}>
              {isSubmitting ? '처리 중...' : '담당자 지정 및 메일 발송'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
