import React from 'react';

export default function DirectInputPanel({ subMetrics, atomicValues, onChange }) {
  if (!subMetrics || subMetrics.length === 0) return null;

  return (
    <div className="ob-input-panel-section">
      <h3 className="ob-section-title">데이터 정량 직접입력</h3>
      <table className="ob-input-table">
        <thead>
          <tr>
            <th style={{ width: '20%' }}>Atomic ID</th>
            <th style={{ width: '40%' }}>항목명</th>
            <th style={{ width: '25%' }}>입력 (Value)</th>
            <th style={{ width: '15%' }}>단위</th>
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
                    type="number"
                    className="ob-table-input"
                    value={atomicValues[id] || ''}
                    onChange={(e) => onChange(id, e.target.value)}
                    placeholder="숫자 입력"
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
}
