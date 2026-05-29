import React from 'react';

export default function ReferenceInputPanel({ subMetrics, atomicValues, onChange }) {
  if (!subMetrics || subMetrics.length === 0) return null;

  return (
    <div className="ob-input-panel-section">
      <h3 className="ob-section-title">근거 참조형 (Reference)</h3>
      
      <table className="ob-input-table">
        <thead>
          <tr>
            <th style={{ width: '20%' }}>Atomic ID</th>
            <th style={{ width: '30%' }}>참조 항목</th>
            <th style={{ width: '50%' }}>입력 (Value)</th>
          </tr>
        </thead>
        <tbody>
          {subMetrics.map(sub => {
            const id = sub.atomicMetricId || sub.issueId;
            return (
              <tr key={id}>
                <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{id}</td>
                <td>{sub.atomicName || sub.checklistQuestion || '-'}</td>
                <td>
                  <input 
                    type="text"
                    className="ob-table-input"
                    value={atomicValues[id] || ''}
                    onChange={(e) => onChange(id, e.target.value)}
                    placeholder="문서명, 링크, 또는 근거 요약 입력"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
