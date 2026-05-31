import React, { useEffect, useRef, useState } from 'react';
import '@styles/onboardingModal.css';

export default function OnboardingModalShell({
  isOpen,
  onClose,
  metricItem,
  subMetrics,
  onSaveAndSubmit,
  modalType = 'MIXED'
}) {
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!metricItem || !subMetrics) return;
    const initialValues = {};
    const initialFiles = {};

    subMetrics.forEach(sub => {
      const id = getAtomicId(sub);
      initialValues[id] = sub.valueText || sub.valueNumeric || sub.value || '';
      initialFiles[id] = sub.evidenceFileName ? { name: sub.evidenceFileName } : null;
    });

    setAtomicValues(initialValues);
    setAtomicFiles(initialFiles);
  }, [metricItem, subMetrics]);

  const getStatusText = (status) => {
    switch (status) {
      case 'DRAFT': return '작성중';
      case 'SUBMITTED': return '검토요청';
      case 'APPROVED': return '완료';
      default: return '미입력';
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'DRAFT': return 'draft';
      case 'SUBMITTED': return 'submitted';
      case 'APPROVED': return 'approved';
      default: return 'not-started';
    }
  };

  const getAtomicId = (sub) => sub.atomicMetricId || sub.issueId;

  const handleInputChange = (id, value) => {
    setAtomicValues(prev => ({ ...prev, [id]: value }));
  };

  const handleFileChange = (id, file) => {
    setAtomicFiles(prev => ({ ...prev, [id]: file }));
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleEvidenceFileChange = (event) => {
    const file = event.target.files[0];
    if (file && subMetrics && subMetrics.length > 0) {
      handleFileChange(getAtomicId(subMetrics[0]), file);
    }
    event.target.value = null;
  };

  const handleSaveDraft = () => {
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'DRAFT');
  };

  const handleSubmit = () => {
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'SUBMITTED');
  };

  const renderHeader = () => (
    <div className="ob-modal-header">
      <div>
        <h2 className="ob-modal-title">
          <span className="ob-modal-tag">{metricItem.issueId || metricItem.metricId}</span>
          {metricItem.issueName || metricItem.metricName}
        </h2>
      </div>
      <div className="ob-header-badges">
        <span className={`ob-status-badge ${getStatusClass(metricItem.status)}`}>
          {getStatusText(metricItem.status)}
        </span>
        <div className="ob-deadline-badge">마감기한: 2026-06-30 까지</div>
      </div>
    </div>
  );

  const renderContextSummary = () => (
    <div className="ob-info-summary-box">
      <div className="ob-info-item">
        <span className="ob-info-label">이슈그룹</span>
        <span className="ob-info-val">{metricItem.issueGroup || metricItem.category || '-'}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">대상 코드 (Metric ID)</span>
        <span className="ob-info-val">{metricItem.issueId || metricItem.metricId}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">입력 방식 / 유형</span>
        <span className="ob-info-val" style={{ color: '#0284c7' }}>
          {modalType} 입력
        </span>
      </div>
      <div className="ob-info-item" style={{ flex: 1 }}>
        <span className="ob-info-label">지표 설명</span>
        <span className="ob-info-val" style={{ fontSize: '0.85rem' }}>
          {metricItem.checklistQuestion || metricItem.metricDescription || '입력 가이드 및 설명을 표시합니다.'}
        </span>
      </div>
    </div>
  );

  const renderInputField = (sub, options = {}) => {
    const id = getAtomicId(sub);
    const isDerived = sub.atomicDataRole === 'DERIVED';
    const type = options.type || (isDerived ? 'text' : 'number');
    const placeholder = options.placeholder || (isDerived ? '자동 계산됨' : '숫자 입력');

    return (
      <input
        type={type}
        className={`ob-table-input ${isDerived ? 'readonly' : ''}`}
        value={atomicValues[id] || ''}
        onChange={(event) => !isDerived && handleInputChange(id, event.target.value)}
        placeholder={placeholder}
        readOnly={isDerived}
      />
    );
  };

  const renderMetricTable = (items, options = {}) => (
    <table className="ob-input-table">
      <thead>
        <tr>
          <th style={{ width: '20%' }}>Atomic ID</th>
          <th style={{ width: options.withUnit ? '40%' : '30%' }}>항목명</th>
          <th style={{ width: options.withUnit ? '25%' : '50%' }}>입력 (Value)</th>
          {options.withUnit && <th style={{ width: '15%' }}>단위</th>}
        </tr>
      </thead>
      <tbody>
        {items.map(sub => {
          const id = getAtomicId(sub);
          const isDerived = sub.atomicDataRole === 'DERIVED';
          return (
            <tr key={id} style={{ background: isDerived ? '#f8fafc' : '#ffffff' }}>
              <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{id}</td>
              <td style={{ fontWeight: isDerived ? '600' : '400', color: isDerived ? '#2563eb' : '#1e293b' }}>
                {sub.atomicName || sub.checklistQuestion || '-'}
              </td>
              <td>{renderInputField(sub, options)}</td>
              {options.withUnit && <td style={{ color: '#475569' }}>{sub.unit || '-'}</td>}
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  const renderDirectSection = (items = subMetrics) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="ob-input-panel-section">
        <h3 className="ob-section-title">데이터 정량 직접입력</h3>
        {renderMetricTable(items, { withUnit: true, type: 'number', placeholder: '숫자 입력' })}
      </div>
    );
  };

  const renderCalculationSection = (items = subMetrics) => {
    if (!items || items.length === 0) return null;
    const derivedMetrics = items.filter(item => item.atomicDataRole === 'DERIVED');

    return (
      <div className="ob-input-panel-section">
        <h3 className="ob-section-title">데이터 계산 (Calculation)</h3>
        {derivedMetrics.length > 0 && (
          <div className="ob-calc-formula-card">
            <strong>시스템 자동 계산 룰셋 적용:</strong><br />
            {derivedMetrics.map(item => (
              <div key={item.atomicMetricId} style={{ marginTop: '4px' }}>
                ∙ {item.atomicName} = {item.calculationFormula || '산식 미정'}
              </div>
            ))}
          </div>
        )}
        {renderMetricTable(items, { withUnit: true })}
      </div>
    );
  };

  const renderNarrativeSection = (items = subMetrics, title = '정성 서술형 입력 (Narrative)') => {
    if (!items || items.length === 0) return null;
    return (
      <div className="ob-input-panel-section">
        <h3 className="ob-section-title">{title}</h3>
        {items.map(sub => {
          const id = getAtomicId(sub);
          return (
            <div key={id} style={{ marginBottom: '24px' }}>
              <div style={{ marginBottom: '8px', fontWeight: '600', color: '#1e293b' }}>
                <span style={{ color: '#64748b', fontSize: '0.85rem', marginRight: '8px' }}>{id}</span>
                {sub.atomicName || sub.checklistQuestion || '서술 항목'}
              </div>
              <textarea
                className="ob-narrative-textarea"
                placeholder="상세 내용을 서술해 주세요."
                value={atomicValues[id] || ''}
                onChange={(event) => handleInputChange(id, event.target.value)}
              />
            </div>
          );
        })}
      </div>
    );
  };

  const renderReferenceSection = (items = subMetrics) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="ob-input-panel-section">
        <h3 className="ob-section-title">근거 참조형 (Reference)</h3>
        {renderMetricTable(items, { type: 'text', placeholder: '문서명, 링크 또는 근거 요약 입력' })}
      </div>
    );
  };

  const renderMixedSection = () => {
    const narrativeMetrics = subMetrics.filter(
      item => item.tokenRole === 'QL' || (item.dataValueType === '정성' && item.atomicDataRole === 'INPUT')
    );
    const quantitativeMetrics = subMetrics.filter(
      item => item.tokenRole === 'Q' || item.dataValueType === '정량'
    );
    const evidenceMetrics = subMetrics.filter(
      item => item.tokenRole === 'EV' || item.atomicDataRole === 'REFERENCE'
    );

    return (
      <>
        {renderNarrativeSection(narrativeMetrics, '1. 정성 서술 (Narrative)')}
        {renderCalculationSection(quantitativeMetrics)}
        {renderReferenceSection(evidenceMetrics)}
      </>
    );
  };

  const renderDynamicSection = () => {
    switch (modalType) {
      case 'DIRECT':
        return renderDirectSection();
      case 'CALCULATION':
        return renderCalculationSection();
      case 'NARRATIVE':
        return renderNarrativeSection();
      case 'REFERENCE':
        return renderReferenceSection();
      case 'MIXED':
      default:
        return renderMixedSection();
    }
  };

  const renderEvidenceSection = () => {
    const uploadedFiles = Object.entries(atomicFiles)
      .filter(([, file]) => file !== null)
      .map(([id, file]) => ({ id, name: file.name }));

    return (
      <div className="ob-side-card">
        <h4>증빙 자료 (Evidence)</h4>
        <input
          type="file"
          style={{ display: 'none' }}
          ref={fileInputRef}
          onChange={handleEvidenceFileChange}
        />
        <div className="ob-file-upload-btn" onClick={handleUploadClick}>
          + 파일 업로드 또는 링크 추가
        </div>

        {uploadedFiles.length > 0 && (
          <div className="ob-evidence-list">
            {uploadedFiles.map(file => (
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

  const renderValidationSection = () => {
    const validations = subMetrics.map(sub => {
      const id = getAtomicId(sub);
      const value = atomicValues[id];
      return {
        id,
        label: sub.atomicName || sub.checklistQuestion || id,
        isPass: value !== undefined && value !== null && value.toString().trim() !== ''
      };
    });
    const allPass = validations.length > 0 && validations.every(item => item.isPass);

    return (
      <div className="ob-side-card">
        <h4>필수값 검증 및 룰셋</h4>
        <div style={{ marginBottom: '16px' }}>
          {validations.map(item => (
            <div key={item.id} className={`ob-validation-item ${item.isPass ? 'pass' : 'fail'}`}>
              <span>{item.isPass ? '✓' : '!'}</span>
              <span style={{ color: '#334155' }}>{item.label}</span>
            </div>
          ))}
        </div>
        <div style={{ padding: '12px', background: allPass ? '#dcfce7' : '#fee2e2', borderRadius: '6px', fontSize: '0.85rem', color: allPass ? '#166534' : '#991b1b', fontWeight: '600', textAlign: 'center' }}>
          {allPass ? '모든 데이터 입력이 완료되었습니다.' : '필수 입력 항목이 누락되었습니다.'}
        </div>
      </div>
    );
  };

  const renderFooterActions = () => (
    <div className="ob-modal-footer">
      <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>
        취소
      </button>
      <button type="button" className="ob-btn ob-btn-secondary" onClick={handleSaveDraft}>
        임시저장
      </button>
      <button type="button" className="ob-btn ob-btn-primary" onClick={handleSubmit}>
        데이터 최종 제출
      </button>
    </div>
  );

  if (!isOpen || !metricItem || !subMetrics) return null;

  return (
    <div className="ob-modal-overlay" onClick={onClose}>
      <div className="ob-modal-shell" onClick={(event) => event.stopPropagation()}>
        {renderHeader()}

        <div className="ob-modal-body-layout">
          <div className="ob-modal-left-panel">
            {renderContextSummary()}
            {renderDynamicSection()}
          </div>

          <div className="ob-modal-right-panel">
            {renderEvidenceSection()}
            {renderValidationSection()}
          </div>
        </div>

        {renderFooterActions()}
      </div>
    </div>
  );
}
