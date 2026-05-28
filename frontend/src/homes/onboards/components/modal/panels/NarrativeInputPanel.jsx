import React from 'react';

export default function NarrativeInputPanel({ subMetrics, atomicValues, onChange }) {
  if (!subMetrics || subMetrics.length === 0) return null;

  return (
    <div className="ob-input-panel-section">
      <h3 className="ob-section-title">정성 서술형 입력 (Narrative)</h3>
      
      {subMetrics.map(sub => {
        const id = sub.atomicMetricId || sub.issueId;
        return (
          <div key={id} style={{ marginBottom: '24px' }}>
            <div style={{ marginBottom: '8px', fontWeight: '600', color: '#1e293b' }}>
              <span style={{ color: '#64748b', fontSize: '0.85rem', marginRight: '8px' }}>{id}</span>
              {sub.atomicName || sub.checklistQuestion || '서술 항목'}
            </div>
            
            <textarea
              className="ob-narrative-textarea"
              placeholder="상세 내용을 서술해 주세요..."
              value={atomicValues[id] || ''}
              onChange={(e) => onChange(id, e.target.value)}
            />
          </div>
        );
      })}
    </div>
  );
}
