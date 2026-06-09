import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import '@styles/onboardingModal.css';
import { getAtomicId, isEditableItem, resolveG0InputMode } from '../onboardingUtils';
import TextEditorModal from './TextEditorModal';

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
  readOnlyYn = false,
}) {
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});
  const [expandedGroups, setExpandedGroups] = useState({ ROLLUP: true, INPUT: true, REFERENCE: true, CALCULATED: true });
  const [editingTextId, setEditingTextId] = useState(null);

  const toggleGroup = (key) => {
    setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }));
  };

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
    if (readOnlyYn) return;
    setAtomicValues((prev) => ({ ...prev, [atomicMetricId]: value }));
  };

  const handleFileChange = (atomicMetricId, file) => {
    if (readOnlyYn) return;
    setAtomicFiles((prev) => ({ ...prev, [atomicMetricId]: file }));
  };

  const isYearRangeValid = (value) => {
    const [startDate, endDate] = String(value || '').split('~').map((part) => part.trim());
    return Boolean(startDate && endDate && endDate >= startDate);
  };

  const editableMetrics = (subMetrics || []).filter((sub) => isEditableItem(sub));
  const hasInvalidYearRange = editableMetrics.some((sub) => {
    if (resolveG0InputMode(sub) === 'YEAR_RANGE') {
      const val = atomicValues[getAtomicId(sub)] || '';
      return !isYearRangeValid(val);
    }
    return false;
  });

  const saveDisabled = readOnlyYn || editableMetrics.length === 0 || hasInvalidYearRange;

  const handleSaveDraft = () => {
    if (saveDisabled) return;
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'DRAFT');
  };

  const handleSubmit = () => {
    if (saveDisabled) return;
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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
      <strong style={{ color: '#0f172a' }}>{getDisplayValue(sub)}</strong>
      {message && (
        <span style={{ color: '#64748b', fontSize: '0.78rem', lineHeight: 1.35, textAlign: 'center' }}>
          {message}
        </span>
      )}
    </div>
  );

  const renderInputField = (sub, id, isCalculated = false) => {
    const inputMode = resolveG0InputMode(sub);
    const value = atomicValues[id] || '';

    if (readOnlyYn || isConsultantViewer) {
      return renderReadOnlyValue({ ...sub, valueText: value }, null);
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

    if (inputMode === 'YEAR_RANGE') {
      const parts = value.includes('~') ? value.split('~').map(s => s.trim()) : [];
      let startStr = parts[0] || '';
      let endStr = parts[1] || '';
      if (!value.includes('~') && value.trim().length === 4) {
        startStr = `${value.trim()}-01-01`;
        endStr = `${value.trim()}-12-31`;
      }

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: '#64748b', width: '40px' }}>시작일</span>
            <input
              type="date"
              className="ob-table-input"
              style={{ flex: 1, padding: '6px 8px' }}
              value={startStr}
              onChange={(e) => handleInputChange(id, `${e.target.value} ~ ${endStr}`)}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: '#64748b', width: '40px' }}>종료일</span>
            <input
              type="date"
              className="ob-table-input"
              style={{ flex: 1, padding: '6px 8px' }}
              value={endStr}
              onChange={(e) => handleInputChange(id, `${startStr} ~ ${e.target.value}`)}
            />
          </div>
        </div>
      );
    }

    if (inputMode === 'MANUAL_TEXTAREA' || inputMode === 'STRUCTURED_LOOKUP') {
      const isStructured = inputMode === 'STRUCTURED_LOOKUP';
      const placeholder = isStructured 
        ? (id === 'G0-05__QL0002' ? "공시 대상 자회사 또는 법인명을 한 줄에 하나씩 입력해 주세요." : id === 'G0-06__QL0001' ? "연결 범위에 포함할 자회사 또는 법인명을 한 줄에 하나씩 입력해 주세요." : "목록을 한 줄에 하나씩 입력해 주세요.")
        : "내용 입력";

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {value ? (
            <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem', color: '#334155', maxHeight: '80px', overflowY: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
              {value}
            </div>
          ) : (
            <button 
              type="button"
              onClick={() => setEditingTextId(id)}
              style={{ width: '100%', textAlign: 'left', padding: '6px 12px', background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '4px', color: '#94a3b8', fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s' }}
              onMouseEnter={(e) => { e.target.style.background = '#f1f5f9'; e.target.style.borderColor = '#94a3b8'; e.target.style.color = '#64748b'; }}
              onMouseLeave={(e) => { e.target.style.background = '#f8fafc'; e.target.style.borderColor = '#cbd5e1'; e.target.style.color = '#94a3b8'; }}
            >
              상세 내용을 입력해주세요
            </button>
          )}
          {isStructured && (
            <span style={{ color: '#64748b', fontSize: '0.78rem', marginTop: '4px' }}>
              회사 관계 관리 기능 연결 후 선택형 입력으로 전환됩니다.
            </span>
          )}
        </div>
      );
    }

    if (inputMode === 'ROLLUP_READONLY') {
      return renderReadOnlyValue(
        sub,
        isCalculated ? '입력된 데이터를 바탕으로 자동 계산됩니다.' : null
      );
    }

    return renderReadOnlyValue(sub, isCalculated ? '입력된 데이터를 바탕으로 자동 계산됩니다.' : null);
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
    <div className="ob-info-summary-box" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 3fr', gap: '24px' }}>
      <div className="ob-info-item">
        <span className="ob-info-label">Data ID</span>
        <span className="ob-info-val">{metricItem.metricId}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">단위</span>
        <span className="ob-info-val">{metricItem.unit || '-'}</span>
      </div>
      <div className="ob-info-item">
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
        {readOnlyYn ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
            <span style={{ fontWeight: 600, color: '#1e293b' }}>{assigneeName || '-'}</span>
            <span className="ob-assignment-card-status">Read-only history</span>
          </div>
        ) : isConsultantViewer ? (
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

        {canManageAssignments && !readOnlyYn && (
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

  /* ─── Render: Generic G0 Input ─── */
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

    // Grouping logic
    const groups = [
      { key: 'ROLLUP', id: '집계형', desc: '자회사 데이터 취합 후 자동 반영', items: [] },
      { key: 'INPUT', id: '입력형', desc: '직접 입력 필요', items: [] },
      { key: 'REFERENCE', id: '참조형', desc: '참고용 정보', items: [] },
      { key: 'CALCULATED', id: '계산형', desc: '자동 계산', items: [] }
    ];

    subMetrics.forEach((sub) => {
      const id = getAtomicId(sub);
      if (!id) return;
      const parts = id.split('__');
      if (parts.length > 1) {
        const suffix = parts[1];
        if (suffix.startsWith('G')) groups[0].items.push(sub);
        else if (suffix.startsWith('Q') || suffix.startsWith('QL')) groups[1].items.push(sub);
        else if (suffix.startsWith('R')) groups[2].items.push(sub);
        else if (suffix.startsWith('C')) groups[3].items.push(sub);
        else groups[1].items.push(sub);
      } else {
        groups[1].items.push(sub);
      }
    });

    const activeGroups = groups.filter(g => g.items.length > 0);

    let globalIndex = 1;
    activeGroups.forEach(g => {
      g.items.forEach(sub => {
        sub._displayIndex = globalIndex++;
      });
    });

    return (
      <div className="ob-input-panel-section">
        <style>{`
          .ob-type-tooltip-wrapper {
            position: relative;
            display: inline-block;
          }
          .ob-type-tooltip-content {
            visibility: hidden;
            background-color: #334155;
            color: #fff;
            text-align: center;
            padding: 6px 10px;
            border-radius: 4px;
            position: absolute;
            z-index: 9999;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(-4px);
            opacity: 0;
            transition: opacity 0.2s, transform 0.2s;
            font-size: 0.75rem;
            white-space: nowrap;
            pointer-events: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          }
          .ob-type-tooltip-content::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -4px;
            border-width: 4px;
            border-style: solid;
            border-color: #334155 transparent transparent transparent;
          }
          .ob-type-tooltip-wrapper:hover .ob-type-tooltip-content {
            visibility: visible;
            opacity: 1;
            transform: translateX(-50%) translateY(-8px);
          }
        `}</style>
        <table className="ob-input-table" style={{ tableLayout: 'fixed', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: '6%', textAlign: 'center' }}>No.</th>
              <th style={{ width: '28%', textAlign: 'center' }}>항목명</th>
              <th style={{ width: '14%', textAlign: 'center' }}>데이터 유형</th>
              <th style={{ width: '40%', textAlign: 'center' }}>입력값 (Value)</th>
              <th style={{ width: '12%', textAlign: 'center' }}>단위</th>
            </tr>
          </thead>
          {activeGroups.map(group => (
            <tbody key={group.key}>
              <tr className="ob-group-header" onClick={() => toggleGroup(group.key)} style={{ cursor: 'pointer' }}>
                <td colSpan={5} style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#1e293b', fontSize: '0.9rem', fontWeight: 600 }}>
                  <span style={{ marginRight: '8px', color: '#94a3b8', display: 'inline-flex', alignItems: 'center', transform: expandedGroups[group.key] ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.2s' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </span>
                  {group.id}
                  <span style={{ marginLeft: '8px', color: '#64748b', fontSize: '0.85rem', fontWeight: 400 }}>· {group.desc}</span>
                </td>
              </tr>
              {expandedGroups[group.key] && group.items.map((sub) => {
                const id = getAtomicId(sub);
                const isRollup = group.key === 'ROLLUP';
                const isCalculated = group.key === 'CALCULATED';
                const isReference = group.key === 'REFERENCE';
                
                let typeBadge = '';
                let typeClass = '';
                let typeTooltip = '';
                if (isRollup) { typeBadge = '집계형'; typeClass = 'rollup'; typeTooltip = '데이터 취합 및 취합 계산 완료 후 자동 반영됩니다.'; }
                else if (isCalculated) { typeBadge = '계산형'; typeClass = 'calc'; typeTooltip = '입력된 데이터를 바탕으로 자동 계산됩니다.'; }
                else if (isReference) { typeBadge = '참조형'; typeClass = 'ref'; typeTooltip = '다른 지표의 값을 참조하여 자동 반영됩니다.'; }
                else { typeBadge = '입력형'; typeClass = 'manual'; typeTooltip = '직접 데이터를 입력해야 하는 항목입니다.'; }

                return (
                  <tr key={id}>
                    <td style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center' }}>{sub._displayIndex}</td>
                    <td style={{ fontWeight: '400', color: '#1e293b', fontSize: '0.85rem', textAlign: 'center' }}>
                      {sub.atomicName || sub.metricName || '-'}
                    </td>
                    <td style={{ fontSize: '0.85rem', textAlign: 'center' }}>
                      <div className="ob-type-tooltip-wrapper">
                        <span className={`ob-type-badge ${typeClass}`} style={{ display: 'inline-block', padding: '2px 6px', borderRadius: '4px', margin: '0', fontWeight: 600, cursor: 'default' }}>{typeBadge}</span>
                        <div className="ob-type-tooltip-content">{typeTooltip}</div>
                      </div>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'inline-block', textAlign: 'left', width: '100%' }}>
                        {renderInputField(sub, id, isCalculated)}
                      </div>
                    </td>
                    <td style={{ color: '#475569', fontSize: '0.85rem', textAlign: 'center' }}>
                      {(() => {
                        const inputMode = resolveG0InputMode(sub, metricItem?.metricId);
                        if (inputMode === 'MANUAL_TEXTAREA' || inputMode === 'STRUCTURED_LOOKUP') {
                          return (
                            <button
                              type="button"
                              className="ob-btn ob-btn-secondary"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
                              onClick={() => setEditingTextId(id)}
                            >
                              수정하기
                            </button>
                          );
                        }
                        return sub.unit || '-';
                      })()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          ))}
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
          isPass: value !== undefined && value !== null && String(value).trim() !== '',
          isRequired: sub.requiredYn !== false,
        };
      });
    const requiredValidations = validations.filter((v) => v.isRequired);
    const passedValidations = requiredValidations.filter((v) => v.isPass);
    const allPass = requiredValidations.length > 0 && passedValidations.length === requiredValidations.length;
    const hasValidationTargets = requiredValidations.length > 0;
    const progressPercent = hasValidationTargets ? Math.round((passedValidations.length / requiredValidations.length) * 100) : 100;

    return (
      <div className="ob-side-card">   
        {hasValidationTargets ? (
          <>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                <span>필수 <span style={{ color: '#ef4444' }}>{requiredValidations.length}개</span> 중 <span style={{ color: '#ef4444' }}>{passedValidations.length}개</span> 완료</span>
                <span style={{ fontSize: '0.85rem', color: '#64748b' }}>{progressPercent}%</span>
              </div>
              <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progressPercent}%`, background: progressPercent === 100 ? '#16a34a' : '#3b82f6', transition: 'width 0.3s ease' }}></div>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              {validations.map((item) => (
                <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: item.isPass ? '#16a34a' : '#ef4444', fontWeight: 600, width: '12px', textAlign: 'center' }}>
                      {item.isPass ? '✓' : '①'}
                    </span>
                    <span style={{ color: '#334155' }}>
                      {item.label}
                    </span>
                  </div>
                  <span style={{ color: item.isPass ? '#16a34a' : '#ef4444' }}>
                    {item.isPass ? '입력 완료' : '입력 필요'}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.4 }}>
              필수값을 모두 입력해야 승인 요청이 가능합니다.
            </div>
          </>
        ) : (
          <div style={{ padding: '12px', background: '#f1f5f9', borderRadius: '6px', fontSize: '0.85rem', color: '#475569', fontWeight: '600', textAlign: 'center' }}>
            수기 입력 검증 대상이 없습니다.
          </div>
        )}
      </div>
    );
  };

  /* ─── Render: Footer ─── */
  const renderFooterActions = () => {
    if (readOnlyYn || isConsultantViewer) {
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
          className="ob-btn ob-btn-secondary"
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
        {!readOnlyYn && editingTextId && (() => {
          const editingSub = subMetrics.find(sub => getAtomicId(sub) === editingTextId);
          const title = editingSub?.atomicName || editingSub?.metricName || '상세 입력';
          return (
            <TextEditorModal
              isOpen={true}
              title={title}
              initialValue={atomicValues[editingTextId] || ''}
              onSave={(val) => {
                handleInputChange(editingTextId, val);
                setEditingTextId(null);
              }}
              onClose={() => setEditingTextId(null)}
            />
          );
        })()}
      </div>
    </div>,
    document.body
  );
}

