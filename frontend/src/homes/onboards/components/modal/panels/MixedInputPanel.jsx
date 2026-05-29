import React from 'react';

export default function MixedInputPanel({ subMetrics, atomicValues, onChange }) {
  if (!subMetrics || subMetrics.length === 0) return null;

  // 정성(QL, 서술형)과 정량/참조(Q, EV)를 분리해서 렌더링
  const qlMetrics = subMetrics.filter(m => m.tokenRole === 'QL' || m.dataValueType === '정성' && m.atomicDataRole === 'INPUT');
  const qMetrics = subMetrics.filter(m => m.tokenRole === 'Q' || m.dataValueType === '정량');
  const evMetrics = subMetrics.filter(m => m.tokenRole === 'EV' || m.atomicDataRole === 'REFERENCE');

  return (
    <div className="ob-input-panel-section">
      <h3 className="ob-section-title">혼합형 명세 (Mixed)</h3>
      
      {/* 1. 정성 서술 영역 */}
      {qlMetrics.length > 0 && (
        <div style={{ marginBottom: '32px' }}>
          <h4 style={{ fontSize: '1rem', color: '#334155', marginBottom: '12px' }}>1. 정성 서술 (Narrative)</h4>
          {qlMetrics.map(sub => {
            const id = sub.atomicMetricId || sub.issueId;
            return (
              <div key={id} style={{ marginBottom: '16px' }}>
                <div style={{ marginBottom: '8px', fontWeight: '500', color: '#1e293b', fontSize: '0.9rem' }}>
                  <span style={{ color: '#64748b', fontSize: '0.8rem', marginRight: '8px' }}>{id}</span>
                  {sub.atomicName || sub.checklistQuestion || '-'}
                </div>
                <textarea
                  className="ob-narrative-textarea"
                  style={{ minHeight: '100px' }}
                  placeholder="상세 내용을 서술해 주세요..."
                  value={atomicValues[id] || ''}
                  onChange={(e) => onChange(id, e.target.value)}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* 2. 정량/수치 입력 영역 */}
      {qMetrics.length > 0 && (
        <div style={{ marginBottom: '32px' }}>
          <h4 style={{ fontSize: '1rem', color: '#334155', marginBottom: '12px' }}>2. 정량 데이터 (Quantitative)</h4>
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
              {qMetrics.map(sub => {
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
      )}

      {/* 3. 근거/참조 영역 */}
      {evMetrics.length > 0 && (
        <div>
          <h4 style={{ fontSize: '1rem', color: '#334155', marginBottom: '12px' }}>3. 근거 요약 및 참조 (Reference)</h4>
          <table className="ob-input-table">
            <thead>
              <tr>
                <th style={{ width: '20%' }}>Atomic ID</th>
                <th style={{ width: '30%' }}>참조 항목</th>
                <th style={{ width: '50%' }}>입력 (Value)</th>
              </tr>
            </thead>
            <tbody>
              {evMetrics.map(sub => {
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
                        placeholder="근거 문서명이나 요약 내용 입력"
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}
