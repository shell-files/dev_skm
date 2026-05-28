import React from 'react';

export default function ValidationPreviewPanel({ subMetrics, atomicValues }) {
  if (!subMetrics) return null;

  // 더미 검증 로직: required인 항목이 채워졌는가?
  const validations = subMetrics.map(sub => {
    const id = sub.atomicMetricId || sub.issueId;
    const value = atomicValues[id];
    const isPass = value !== undefined && value !== null && value.toString().trim() !== '';
    return {
      id,
      label: sub.atomicName || sub.checklistQuestion || id,
      isPass
    };
  });

  const allPass = validations.length > 0 && validations.every(v => v.isPass);

  return (
    <div className="ob-side-card">
      <h4>✅ 필수값 검증 및 룰셋</h4>
      
      <div style={{ marginBottom: '16px' }}>
        {validations.map(val => (
          <div key={val.id} className={`ob-validation-item ${val.isPass ? 'pass' : 'fail'}`}>
            <span>{val.isPass ? '✓' : '✗'}</span>
            <span style={{ color: '#334155' }}>{val.label}</span>
          </div>
        ))}
      </div>

      <div style={{ padding: '12px', background: allPass ? '#dcfce7' : '#fee2e2', borderRadius: '6px', fontSize: '0.85rem', color: allPass ? '#166534' : '#991b1b', fontWeight: '600', textAlign: 'center' }}>
        {allPass ? '모든 데이터 입력이 완료되었습니다.' : '필수 입력 항목이 누락되었습니다.'}
      </div>
    </div>
  );
}
