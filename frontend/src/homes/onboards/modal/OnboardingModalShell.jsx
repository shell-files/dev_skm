import React, { useState, useEffect, useRef } from 'react';
import '@styles/onboardingModal.css';

// ---------------------------------------------------------
// Helper components (Inlined from old files)
// ---------------------------------------------------------

export const buildFieldKey = (field) => {
  return field.atomicMetricId;
};
export const isDerived = (field) => field.atomicDataRole === 'DERIVED';
export const isReference = (field) => field.tokenRole === 'EV' || field.atomicDataRole === 'REFERENCE';
export const isNarrative = (field) => field.tokenRole === 'QL' || (field.dataValueType === '정성' && field.atomicDataRole === 'INPUT');
export const isDirect = (field) => !isDerived(field) && !isReference(field) && !isNarrative(field);

export const renderDirectField = (field, value, onChange) => {
  const key = buildFieldKey(field);
  const type = field.inputType || 'TEXT';
  
  switch (type.toUpperCase()) {
    case 'NUMBER': return <input type="number" className="ob-table-input" value={value || ''} onChange={e => onChange(key, e.target.value)} placeholder="숫자 입력" />;
    case 'TEXTAREA': return <textarea className="ob-narrative-textarea" value={value || ''} onChange={e => onChange(key, e.target.value)} placeholder="입력해 주세요..." />;
    case 'DATE': return <input type="date" className="ob-table-input" value={value || ''} onChange={e => onChange(key, e.target.value)} />;
    case 'BOOLEAN':
      return (
        <select className="ob-table-input" value={value || ''} onChange={e => onChange(key, e.target.value)}>
          <option value="">선택</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    case 'ENUM':
      return (
        <select className="ob-table-input" value={value || ''} onChange={e => onChange(key, e.target.value)}>
          <option value="">선택</option>
          {field.options && field.options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
      );
    case 'TEXT':
    default: return <input type="text" className="ob-table-input" value={value || ''} onChange={e => onChange(key, e.target.value)} placeholder="텍스트 입력" />;
  }
};

export const FieldRow = ({ field, value, onChange }) => {
  const isDerivedField = isDerived(field);
  return (
    <tr style={{ background: isDerivedField ? '#f8fafc' : '#ffffff' }}>
      <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{field.atomicMetricId}</td>
      <td style={{ fontWeight: isDerivedField ? '600' : '400', color: isDerivedField ? '#2563eb' : '#1e293b' }}>
        {field.atomicName || field.checklistQuestion || '-'}
      </td>
      <td>
        {isDerivedField ? (
          <input type="text" className="ob-table-input readonly" value={value || ''} readOnly placeholder="자동 계산됨" />
        ) : (
          renderDirectField(field, value, onChange)
        )}
      </td>
      <td style={{ color: '#475569' }}>{field.unit || '-'}</td>
    </tr>
  );
};

export const Section = ({ title, fields, values, onChange, type }) => {
  if (!fields || fields.length === 0) return null;
  return (
    <div style={{ marginBottom: '32px' }}>
      <h4 style={{ fontSize: '1rem', color: '#334155', marginBottom: '12px' }}>{title}</h4>
      {type === 'NARRATIVE' ? (
        fields.map(field => {
          const key = buildFieldKey(field);
          return (
            <div key={key} style={{ marginBottom: '16px' }}>
              <div style={{ marginBottom: '8px', fontWeight: '500', color: '#1e293b', fontSize: '0.9rem' }}>
                <span style={{ color: '#64748b', fontSize: '0.8rem', marginRight: '8px' }}>{field.atomicMetricId}</span>
                {field.atomicName || field.checklistQuestion || '-'}
              </div>
              <textarea className="ob-narrative-textarea" style={{ minHeight: '100px' }} placeholder="상세 내용을 서술해 주세요..." value={values[key] || ''} onChange={(e) => onChange(key, e.target.value)} />
            </div>
          );
        })
      ) : type === 'REFERENCE' ? (
        <table className="ob-input-table">
          <thead>
            <tr><th style={{ width: '20%' }}>Atomic ID</th><th style={{ width: '30%' }}>참조 항목</th><th style={{ width: '50%' }}>입력 (Value)</th></tr>
          </thead>
          <tbody>
            {fields.map(field => {
              const key = buildFieldKey(field);
              return (
                <tr key={key}>
                  <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{field.atomicMetricId}</td>
                  <td>{field.atomicName || field.checklistQuestion || '-'}</td>
                  <td><input type="text" className="ob-table-input" value={values[key] || ''} onChange={(e) => onChange(key, e.target.value)} placeholder="근거 문서명이나 요약 내용 입력" /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <table className="ob-input-table">
          <thead>
            <tr><th style={{ width: '20%' }}>Atomic ID</th><th style={{ width: '40%' }}>항목명</th><th style={{ width: '25%' }}>입력/결과 (Value)</th><th style={{ width: '15%' }}>단위</th></tr>
          </thead>
          <tbody>
            {fields.map(field => (
              <FieldRow key={buildFieldKey(field)} field={field} value={values[buildFieldKey(field)]} onChange={onChange} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export function OnboardingInputPanel({ fields, values, onChange }) {
  if (!fields || fields.length === 0) return null;
  const directFields = fields.filter(isDirect);
  const calcFields = fields.filter(isDerived);
  const narrativeFields = fields.filter(isNarrative);
  const refFields = fields.filter(isReference);
  return (
    <div className="ob-input-panel-section">
      <Section title="1. 기본 정보 입력 (Direct)" fields={directFields} values={values} onChange={onChange} type="DIRECT" />
      <Section title="2. 정성 서술 (Narrative)" fields={narrativeFields} values={values} onChange={onChange} type="NARRATIVE" />
      <Section title="3. 자동 계산 결과 (Calculation)" fields={calcFields} values={values} onChange={onChange} type="CALCULATION" />
      <Section title="4. 근거 요약 및 참조 (Reference)" fields={refFields} values={values} onChange={onChange} type="REFERENCE" />
    </div>
  );
}

export function ContextSummaryPanel({ metricId, metricName }) {
  if (!metricId) return null;
  return (
    <div className="ob-info-summary-box">
      <div className="ob-info-item"><span className="ob-info-label">대표 코드 (Metric ID)</span><span className="ob-info-val">{metricId}</span></div>
      <div className="ob-info-item"><span className="ob-info-label">입력 수준 / 유형</span><span className="ob-info-val" style={{ color: '#0284c7' }}>MIXED (정성+정량 혼합)</span></div>
      <div className="ob-info-item" style={{ flex: 1 }}><span className="ob-info-label">지표 설명</span><span className="ob-info-val" style={{ fontSize: '0.85rem' }}>{metricName || '입력 가이드 및 설명이 표시됩니다.'}</span></div>
    </div>
  );
}

export function EvidencePanel({ subMetrics, atomicFiles, onFileChange }) {
  const fileInputRef = useRef(null);
  const handleUploadClick = () => { if (fileInputRef.current) fileInputRef.current.click(); };
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && subMetrics && subMetrics.length > 0) {
      const targetId = buildFieldKey(subMetrics[0]);
      onFileChange(targetId, file);
    }
    e.target.value = null;
  };
  const uploadedFiles = Object.entries(atomicFiles).filter(([_, file]) => file !== null).map(([id, file]) => ({ id, name: file.name }));
  return (
    <div className="ob-side-card">
      <h4>📎 증빙 자료 (Evidence)</h4>
      <input type="file" style={{ display: 'none' }} ref={fileInputRef} onChange={handleFileChange} />
      <div className="ob-file-upload-btn" onClick={handleUploadClick}>+ 파일 업로드 또는 링크 추가</div>
      {uploadedFiles.length > 0 && (
        <div className="ob-evidence-list">
          {uploadedFiles.map(file => (
            <div key={file.id} className="ob-evidence-item">
              <span>{file.name}</span>
              <button type="button" style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#ef4444' }} onClick={() => onFileChange(file.id, null)}>×</button>
            </div>
          ))}
        </div>
      )}
      {uploadedFiles.length === 0 && (
        <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8', textAlign: 'center' }}>등록된 증빙 자료가 없습니다.</div>
      )}
    </div>
  );
}

export function ValidationPreviewPanel({ subMetrics, atomicValues }) {
  if (!subMetrics) return null;
  const validations = subMetrics.map(sub => {
    const id = buildFieldKey(sub);
    const value = atomicValues[id];
    const isPass = value !== undefined && value !== null && value.toString().trim() !== '';
    return { id, label: sub.atomicName || sub.checklistQuestion || id, isPass };
  });
  const allPass = validations.length > 0 && validations.every(v => v.isPass);
  return (
    <div className="ob-side-card">
      <h4>✅ 필수값 검증 및 룰셋</h4>
      <div style={{ marginBottom: '16px' }}>
        {validations.map(val => (
          <div key={val.id} className={`ob-validation-item ${val.isPass ? 'pass' : 'fail'}`}>
            <span>{val.isPass ? '✓' : '✗'}</span><span style={{ color: '#334155' }}>{val.label}</span>
          </div>
        ))}
      </div>
      <div style={{ padding: '12px', background: allPass ? '#dcfce7' : '#fee2e2', borderRadius: '6px', fontSize: '0.85rem', color: allPass ? '#166534' : '#991b1b', fontWeight: '600', textAlign: 'center' }}>
        {allPass ? '모든 데이터 입력이 완료되었습니다.' : '필수 입력 항목이 누락되었습니다.'}
      </div>
    </div>
  );
}

export function ModalHeader({ metricId, metricName }) {
  if (!metricId) return null;
  return (
    <div className="ob-modal-header">
      <div>
        <h2 className="ob-modal-title">
          <span className="ob-modal-tag">{metricId}</span>
          {metricName}
        </h2>
      </div>
      <div className="ob-header-badges">
        <span className="ob-status-badge draft">작성중</span>
        <div className="ob-deadline-badge">마감기한: 2026-06-30 까지</div>
      </div>
    </div>
  );
}

export function ModalFooterActions({ onClose, onSaveDraft, onSubmit }) {
  return (
    <div className="ob-modal-footer">
      <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>취소</button>
      <button type="button" className="ob-btn ob-btn-secondary" onClick={onSaveDraft}>임시저장</button>
      <button type="button" className="ob-btn ob-btn-primary" onClick={onSubmit}>데이터 최종 제출</button>
    </div>
  );
}

// ---------------------------------------------------------
// Main Shell Component
// ---------------------------------------------------------

export default function OnboardingModalShell({
  isOpen,
  onClose,
  metricId,
  metricName,
  items,
  onSaveAndSubmit,
}) {
  const [fieldValues, setFieldValues] = useState({});
  const [evidenceItems, setEvidenceItems] = useState({});

  useEffect(() => {
    if (!items) return;
    const initialValues = {};
    const initialFiles = {};

    items.forEach(sub => {
      const key = sub.atomicMetricId;
      initialValues[key] = sub.valueNumeric ?? sub.valueText ?? '';
      initialFiles[key] = null;
    });

    setFieldValues(initialValues);
    setEvidenceItems(initialFiles);
  }, [items]);

  const handleValueChange = (id, value) => {
    setFieldValues(prev => ({ ...prev, [id]: value }));
  };

  const handleEvidenceChange = (id, file) => {
    setEvidenceItems(prev => ({ ...prev, [id]: file }));
  };

  const handleSaveDraft = () => {
    if (onSaveAndSubmit) {
      onSaveAndSubmit(fieldValues, evidenceItems, 'DRAFT');
    }
  };

  const handleSubmit = () => {
    if (onSaveAndSubmit) {
      onSaveAndSubmit(fieldValues, evidenceItems, 'SUBMITTED');
    }
  };

  if (!isOpen || !items) return null;

  return (
    <div className="ob-modal-overlay" onClick={onClose}>
      <div className="ob-modal-shell" onClick={(e) => e.stopPropagation()}>
        <ModalHeader metricId={metricId} metricName={metricName} />
        
        <div className="ob-modal-body-layout">
          {/* Left Panel: 70% */}
          <div className="ob-modal-left-panel">
            <ContextSummaryPanel metricId={metricId} metricName={metricName} />
            <OnboardingInputPanel
              fields={items}
              values={fieldValues}
              onChange={handleValueChange}
              evidenceItems={evidenceItems}
              onEvidenceChange={handleEvidenceChange}
            />
          </div>

          {/* Right Panel: 30% */}
          <div className="ob-modal-right-panel">
            <EvidencePanel 
              subMetrics={items} 
              atomicFiles={evidenceItems} 
              onFileChange={handleEvidenceChange} 
            />
            <ValidationPreviewPanel 
              subMetrics={items} 
              atomicValues={fieldValues} 
            />
          </div>
        </div>

        <ModalFooterActions 
          onClose={onClose} 
          onSaveDraft={handleSaveDraft} 
          onSubmit={handleSubmit} 
        />
      </div>
    </div>
  );
}
