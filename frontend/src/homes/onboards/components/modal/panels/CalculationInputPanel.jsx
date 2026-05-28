import React from 'react';

export default function CalculationInputPanel({ subMetrics, atomicValues, onChange }) {
  if (!subMetrics || subMetrics.length === 0) return null;

  // 더미로 유도된 지표(DERIVED)와 원천 지표(INPUT) 분리
  const derivedMetrics = subMetrics.filter(m => m.atomicDataRole === 'DERIVED');
  const inputMetrics = subMetrics.filter(m => m.atomicDataRole !== 'DERIVED');

  return (
    <div className="ob-input-panel-section">
      <h3 className="ob-section-title">데이터 계산 (Calculation)</h3>
      
      {derivedMetrics.length > 0 && (
        <div className="ob-calc-formula-card">
          <strong>시스템 자동 계산 룰셋 적용:</strong><br />
          {derivedMetrics.map(m => (
            <div key={m.atomicMetricId} style={{ marginTop: '4px' }}>
              • {m.atomicName} = {m.calculationFormula || '산식 미지정'}
            </div>
          ))}
        </div>
      )}

      <table className="ob-input-table">
        <thead>
          <tr>
            <th style={{ width: '20%' }}>Atomic ID</th>
            <th style={{ width: '40%' }}>항목명</th>
            <th style={{ width: '25%' }}>입력/결과 (Value)</th>
            <th style={{ width: '15%' }}>단위</th>
          </tr>
        </thead>
        <tbody>
          {subMetrics.map(sub => {
            const id = sub.atomicMetricId || sub.issueId;
            const isDerived = sub.atomicDataRole === 'DERIVED';
            
            return (
              <tr key={id} style={{ background: isDerived ? '#f8fafc' : '#ffffff' }}>
                <td style={{ color: '#64748b', fontSize: '0.85rem' }}>{id}</td>
                <td style={{ fontWeight: isDerived ? '600' : '400', color: isDerived ? '#2563eb' : '#1e293b' }}>
                  {sub.atomicName || sub.checklistQuestion || '-'}
                </td>
                <td>
                  <input 
                    type={isDerived ? "text" : "number"}
                    className={`ob-table-input ${isDerived ? 'readonly' : ''}`}
                    value={atomicValues[id] || ''}
                    onChange={(e) => !isDerived && onChange(id, e.target.value)}
                    placeholder={isDerived ? "자동 계산됨" : "숫자 입력"}
                    readOnly={isDerived}
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
