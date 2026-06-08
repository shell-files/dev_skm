import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import '@styles/onboardingModal.css';
import { getAtomicId, isEditableItem, resolveG0InputMode } from '../onboardingUtils';

/**
 * OnboardingModalShell
 *
 * G0 공통 입력 modal shell.
 * - key: atomicMetricId (issueId fallback 제거)
 * - inputMode / editableYn 기준으로 입력, lookup, read-only renderer를 분기
 * - rollup/derived 값은 수기 입력하지 않음
 */
export default function OnboardingModalShell({
  isOpen,
  onClose,
  metricItem,
  subMetrics,
  onSaveAndSubmit,
  submitLabel,
  onOpenAssignment,
  onSubmitRequest,
  canManageAssignments,
  isConsultantViewer,
}) {
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});

  useEffect(() => {
    if (!metricItem || !subMetrics) return;
    const initialValues = {};
    const initialFiles = {};

    subMetrics.forEach((sub) => {
      const id = getAtomicId(sub);
      if (!id) return;
      initialValues[id] = sub.valueText || (sub.valueNumeric != null ? String(sub.valueNumeric) : '') || '';
      initialFiles[id] = null;
    });

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAtomicValues(initialValues);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAtomicFiles(initialFiles);
  }, [metricItem, subMetrics]);

  /* ─── Status helpers ─── */
  const getStatusText = (status) => {
    switch (status) {
      case 'DRAFT':
      case 'IN_PROGRESS':
        return '작성중';
      case 'SUBMITTED':
        return '검토요청';
      case 'APPROVED':
      case 'COMPLETED':
        return '완료';
      default:
        return '미입력';
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'DRAFT':
      case 'IN_PROGRESS':
        return 'draft';
      case 'SUBMITTED':
        return 'submitted';
      case 'APPROVED':
      case 'COMPLETED':
        return 'approved';
      default:
        return 'not-started';
    }
  };

  /* ─── Input handlers ─── */
  const handleInputChange = (atomicMetricId, value) => {
    setAtomicValues((prev) => ({ ...prev, [atomicMetricId]: value }));
  };

  const handleFileChange = (atomicMetricId, file) => {
    setAtomicFiles((prev) => ({ ...prev, [atomicMetricId]: file }));
  };

  const editableMetrics = (subMetrics || []).filter((sub) => isEditableItem(sub));
  const saveDisabled = editableMetrics.length === 0;

  const handleSaveDraft = () => {
    if (saveDisabled) return;
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'DRAFT');
  };

  const handleSubmit = () => {
    onSubmitRequest ? onSubmitRequest(atomicValues, atomicFiles) : onSaveAndSubmit?.(atomicValues, atomicFiles, 'SUBMITTED');
  };

  const getDisplayValue = (sub) => {
    if (sub.valueNumeric !== null && sub.valueNumeric !== undefined) {
      return `${sub.valueNumeric}${sub.unit ? ` ${sub.unit}` : ''}`;
    }
    if (sub.valueText !== null && sub.valueText !== undefined && String(sub.valueText).trim() !== '') {
      return String(sub.valueText);
    }
    return '집계 전';
  };

  const renderReadOnlyValue = (sub, message) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <strong style={{ color: '#0f172a' }}>{getDisplayValue(sub)}</strong>
      <span style={{ color: '#64748b', fontSize: '0.78rem', lineHeight: 1.35 }}>
        {message}
      </span>
    </div>
  );

  const renderInputField = (sub, id) => {
    const inputMode = resolveG0InputMode(sub);
    const value = atomicValues[id] || '';

    if (isConsultantViewer) {
      return renderReadOnlyValue({ ...sub, valueText: value }, '읽기 전용입니다.');
    }

    if (inputMode === 'MANUAL_NUMBER') {
      return (
        <input
          type="number"
          className="ob-table-input"
          value={value}
          onChange={(event) => handleInputChange(id, event.target.value)}
          placeholder="숫자 입력"
        />
      );
    }

    if (inputMode === 'MANUAL_TEXTAREA') {
      return (
        <textarea
          className="ob-table-input"
          value={value}
          onChange={(event) => handleInputChange(id, event.target.value)}
          placeholder="내용 입력"
          rows={3}
          style={{ resize: 'vertical', minHeight: '72px' }}
        />
      );
    }

    if (inputMode === 'YEAR_RANGE') {
      const parts = value.includes('~') ? value.split('~').map(s => s.trim()) : [];
      let startStr = parts[0] || '';
      let endStr = parts[1] || '';
      if (!value.includes('~') && value.trim().length === 4) {
        startStr = `${value.trim()}-01-01`;
        endStr = `${value.trim()}-12-31`;
      }

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>시작일</span>
            <input
              type="date"
              className="ob-table-input"
              value={startStr}
              onChange={(e) => handleInputChange(id, `${e.target.value} ~ ${endStr}`)}
            />
            <span style={{ color: '#64748b' }}>~</span>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>종료일</span>
            <input
              type="date"
              className="ob-table-input"
              value={endStr}
              onChange={(e) => handleInputChange(id, `${startStr} ~ ${e.target.value}`)}
            />
          </div>
        </div>
      );
    }

    if (inputMode === 'STRUCTURED_LOOKUP') {
      const placeholder = id === 'G0-05__QL0002' 
        ? "공시 대상 자회사 또는 법인명을 한 줄에 하나씩 입력해 주세요." 
        : id === 'G0-06__QL0001'
        ? "연결 범위에 포함할 자회사 또는 법인명을 한 줄에 하나씩 입력해 주세요."
        : "목록을 한 줄에 하나씩 입력해 주세요.";

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <textarea
            className="ob-table-input"
            value={value}
            onChange={(event) => handleInputChange(id, event.target.value)}
            placeholder={placeholder}
            rows={3}
            style={{ resize: 'vertical', minHeight: '72px' }}
          />
          <span style={{ color: '#64748b', fontSize: '0.78rem' }}>
            회사 관계 관리 기능 연결 후 선택형 입력으로 전환됩니다.
          </span>
        </div>
      );
    }

    if (inputMode === 'ROLLUP_READONLY') {
      return renderReadOnlyValue(
        sub,
        '자회사 데이터 수집 및 롤업 계산 완료 후 자동 반영됩니다.'
      );
    }

    return renderReadOnlyValue(sub, '현재 입력 정책을 확인할 수 없습니다.');
  };

  /* ─── Render: Header ─── */
  const renderHeader = () => (
    <div className="ob-modal-header">
      <div>
        <h2 className="ob-modal-title">
          <span className="ob-modal-tag">{metricItem.metricId}</span>
          {metricItem.metricName || metricItem.atomicName || '-'}
        </h2>
      </div>
      <div className="ob-header-badges">
        <span className={`ob-status-badge ${getStatusClass(metricItem.status)}`}>
          {getStatusText(metricItem.status)}
        </span>
      </div>
    </div>
  );

  /* ─── Render: Context summary ─── */
  const renderContextSummary = () => (
    <div className="ob-info-summary-box">
      <div className="ob-info-item">
        <span className="ob-info-label">Metric ID</span>
        <span className="ob-info-val">{metricItem.metricId}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">단위</span>
        <span className="ob-info-val">{metricItem.unit || '-'}</span>
      </div>
      <div className="ob-info-item" style={{ flex: 1 }}>
        <span className="ob-info-label">지표 설명</span>
        <span className="ob-info-val" style={{ fontSize: '0.85rem' }}>
          {metricItem.metricName || metricItem.atomicName || '입력 가이드 및 설명을 표시합니다.'}
        </span>
      </div>
    </div>
  );

  const renderAssignmentCard = () => {
    if (!metricItem) return null;
    
    const assigneeName = metricItem.assigneeName;
    const assigneeEmail = metricItem.assigneeEmail;
    const assignmentStatus = metricItem.assignmentStatus;
    const inviteStatus = metricItem.inviteStatus;
    const selfAssignedYn = metricItem.selfAssignedYn;
    const dueDate = metricItem.submissionDueDate;

    const isAssigned = assignmentStatus === 'ASSIGNED';
    const isInvitePending = inviteStatus === 'PENDING';
    const isOverdue = dueDate && dueDate < new Date().toISOString().slice(0, 10);

    return (
      <div className="ob-side-card ob-assignment-card">
        <h4>담당자</h4>
        {isConsultantViewer ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, color: '#1e293b' }}>{assigneeName || '미지정'}</span>
            <span className="ob-assignment-card-status">읽기 전용 검토 화면</span>
          </div>
        ) : selfAssignedYn ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, color: '#1e293b' }}>{assigneeName}</span>
            <span className="ob-assignment-card-status">본인 입력</span>
          </div>
        ) : isInvitePending ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, color: '#1e293b' }}>{assigneeName}</span>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>{assigneeEmail}</span>
            <span className="ob-assignment-card-status pending">회원가입 초대 대기</span>
          </div>
        ) : isAssigned ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, color: '#1e293b' }}>{assigneeName}</span>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>{assigneeEmail}</span>
            <span className="ob-assignment-card-status assigned">지정 완료</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ color: '#94a3b8' }}>지정되지 않음</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px', padding: '12px', background: '#f8fafc', borderRadius: '6px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>제출 기한</span>
          {dueDate ? (
            <span style={{ color: isOverdue ? '#ef4444' : '#1e293b', fontWeight: 600 }}>
              {dueDate} {isOverdue && <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>(초과)</span>}
            </span>
          ) : (
            <span style={{ color: '#94a3b8' }}>미설정</span>
          )}
        </div>

        {canManageAssignments && (
          <button 
            type="button" 
            className="ob-assignment-card-btn"
            onClick={onOpenAssignment}
          >
            {isAssigned || isInvitePending ? '담당자 변경' : '담당자 지정'}
          </button>
        )}
      </div>
    );
  };

  /* ─── Render: Generic G0 Input (운영 유형 binding 보류) ─── */
  const renderGenericG0Input = () => {
    if (!subMetrics || subMetrics.length === 0) {
      return (
        <div className="ob-input-panel-section">
          <div className="ob1-empty-state" style={{ padding: '32px' }}>
            <p className="ob1-empty-title">입력 항목 없음</p>
            <p className="ob1-empty-desc">이 지표에 등록된 입력 항목이 없습니다.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="ob-input-panel-section">
        <h3 className="ob-section-title">G0 데이터 입력</h3>
        <table className="ob-input-table">
          <thead>
            <tr>
              <th style={{ width: '20%' }}>Atomic ID</th>
              <th style={{ width: '35%' }}>항목명</th>
              <th style={{ width: '30%' }}>입력 (Value)</th>
              <th style={{ width: '15%' }}>단위</th>
            </tr>
          </thead>
          <tbody>
            {subMetrics.map((sub) => {
              const id = getAtomicId(sub);
              if (!id) return null;

              return (
                <tr key={id}>
                  <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{id}</td>
                  <td style={{ fontWeight: '400', color: '#1e293b' }}>
                    {sub.atomicName || sub.metricName || '-'}
                  </td>
                  <td>
                    {renderInputField(sub, id)}
                  </td>
                  <td style={{ color: '#475569' }}>{sub.unit || '-'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  /* ─── Render: Evidence (right panel) ─── */
  const renderEvidenceSection = () => {
    const uploadedFiles = Object.entries(atomicFiles)
      .filter(([, file]) => file !== null)
      .map(([id, file]) => ({ id, name: file.name }));

    return (
      <div className="ob-side-card">
        <h4>증빙 자료 (Evidence)</h4>
        <div className="ob-file-upload-btn" onClick={() => {}} style={{ opacity: 0.5, cursor: "not-allowed" }} title="증빙 API 연결 후 활성화">
          + 파일 업로드 또는 링크 추가 (준비중)
        </div>

        {uploadedFiles.length > 0 && (
          <div className="ob-evidence-list">
            {uploadedFiles.map((file) => (
              <div key={file.id} className="ob-evidence-item">
                <span>{file.name}</span>
                <button
                  type="button"
                  style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#ef4444' }}
                  onClick={() => handleFileChange(file.id, null)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        {uploadedFiles.length === 0 && (
          <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8', textAlign: 'center' }}>
            등록된 증빙 자료가 없습니다.
          </div>
        )}
      </div>
    );
  };

  /* ─── Render: Validation (right panel) ─── */
  const renderValidationSection = () => {
    const validations = subMetrics
      .filter((sub) => getAtomicId(sub) && isEditableItem(sub))
      .map((sub) => {
        const id = getAtomicId(sub);
        const value = atomicValues[id];
        return {
          id,
          label: sub.atomicName || sub.metricName || id,
          isPass: value !== undefined && value !== null && value.toString().trim() !== '',
          isRequired: sub.requiredYn !== false,
        };
      });
    const requiredValidations = validations.filter((v) => v.isRequired);
    const allPass = requiredValidations.length > 0 && requiredValidations.every((item) => item.isPass);
    const hasValidationTargets = requiredValidations.length > 0;

    return (
      <div className="ob-side-card">
        <h4>필수값 검증</h4>
        <div style={{ marginBottom: '16px' }}>
          {validations.map((item) => (
            <div key={item.id} className={`ob-validation-item ${item.isPass ? 'pass' : 'fail'}`}>
              <span>{item.isPass ? '✓' : '!'}</span>
              <span style={{ color: '#334155' }}>
                {item.label}
                {item.isRequired && <span style={{ color: '#ef4444', marginLeft: '4px' }}>*</span>}
              </span>
            </div>
          ))}
        </div>
        <div
          style={{
            padding: '12px',
            background: !hasValidationTargets ? '#f1f5f9' : allPass ? '#dcfce7' : '#fee2e2',
            borderRadius: '6px',
            fontSize: '0.85rem',
            color: !hasValidationTargets ? '#475569' : allPass ? '#166534' : '#991b1b',
            fontWeight: '600',
            textAlign: 'center',
          }}
        >
          {!hasValidationTargets ? '수기 입력 검증 대상이 없습니다.' : allPass ? '모든 필수 데이터 입력이 완료되었습니다.' : '필수 입력 항목이 누락되었습니다.'}
        </div>
      </div>
    );
  };

  /* ─── Render: Footer ─── */
  const renderFooterActions = () => {
    if (isConsultantViewer) {
      return (
        <div className="ob-modal-footer">
          <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>
            닫기
          </button>
        </div>
      );
    }

    return (
      <div className="ob-modal-footer">
        <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>
          취소
        </button>
        <button
          type="button"
          className="ob-btn ob-btn-primary"
          onClick={handleSaveDraft}
          disabled={saveDisabled}
          title={saveDisabled ? '수기 입력 가능한 항목이 없습니다.' : undefined}
          style={saveDisabled ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
        >
          임시저장
        </button>
        <button 
          type="button" 
          className="ob-btn ob-btn-primary" 
          onClick={handleSubmit}
          disabled={saveDisabled}
        >
          {submitLabel || '승인 요청'}
        </button>
      </div>
    );
  };

  if (!isOpen || !metricItem || !subMetrics) return null;

  return createPortal(
    <div className="ob-modal-overlay" onClick={onClose}>
      <div className="ob-modal-shell" onClick={(event) => event.stopPropagation()}>
        {renderHeader()}

        <div className="ob-modal-body-layout">
          <div className="ob-modal-left-panel">
            {renderContextSummary()}
            {renderGenericG0Input()}
          </div>

          <div className="ob-modal-right-panel">
            {renderAssignmentCard()}
            {renderEvidenceSection()}
            {renderValidationSection()}
          </div>
        </div>

        {renderFooterActions()}
      </div>
    </div>,
    document.body
  );
}

