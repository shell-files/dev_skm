import React, { useEffect, useRef, useState } from 'react';
import '@styles/onboardingModal.css';

/**
 * OnboardingModalShell
 *
 * G0 공통 입력 modal shell.
 * - key: atomicMetricId (issueId fallback 제거)
 * - 입력 유형별 renderer binding은 보류 (DTO에 inputFormat / atomicDataRole 미포함)
 * - 현재는 generic G0 input renderer만 사용
 */
export default function OnboardingModalShell({
  isOpen,
  onClose,
  metricItem,
  subMetrics,
  onSaveAndSubmit,
}) {
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!metricItem || !subMetrics) return;
    const initialValues = {};
    const initialFiles = {};

    subMetrics.forEach((sub) => {
      const id = sub.atomicMetricId;
      if (!id) return;
      initialValues[id] = sub.valueText || (sub.valueNumeric != null ? String(sub.valueNumeric) : '') || '';
      initialFiles[id] = null;
    });

    setAtomicValues(initialValues);
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

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleEvidenceFileChange = (event) => {
    const file = event.target.files[0];
    if (file && subMetrics && subMetrics.length > 0 && subMetrics[0].atomicMetricId) {
      handleFileChange(subMetrics[0].atomicMetricId, file);
    }
    event.target.value = null;
  };

  const handleSaveDraft = () => {
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'DRAFT');
  };

  const handleSubmit = () => {
    onSaveAndSubmit?.(atomicValues, atomicFiles, 'SUBMITTED');
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
        <span className="ob-info-label">Atomic Metric ID</span>
        <span className="ob-info-val">{metricItem.atomicMetricId || '-'}</span>
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
              const id = sub.atomicMetricId;
              if (!id) return null;

              return (
                <tr key={id}>
                  <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{id}</td>
                  <td style={{ fontWeight: '400', color: '#1e293b' }}>
                    {sub.atomicName || sub.metricName || '-'}
                  </td>
                  <td>
                    <input
                      type="text"
                      className="ob-table-input"
                      value={atomicValues[id] || ''}
                      onChange={(event) => handleInputChange(id, event.target.value)}
                      placeholder="값 입력"
                    />
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
      .filter((sub) => sub.atomicMetricId)
      .map((sub) => {
        const id = sub.atomicMetricId;
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
            background: allPass ? '#dcfce7' : '#fee2e2',
            borderRadius: '6px',
            fontSize: '0.85rem',
            color: allPass ? '#166534' : '#991b1b',
            fontWeight: '600',
            textAlign: 'center',
          }}
        >
          {allPass ? '모든 필수 데이터 입력이 완료되었습니다.' : '필수 입력 항목이 누락되었습니다.'}
        </div>
      </div>
    );
  };

  /* ─── Render: Footer ─── */
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
            {renderGenericG0Input()}
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
