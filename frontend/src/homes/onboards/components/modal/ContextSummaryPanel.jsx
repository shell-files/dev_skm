import React from 'react';

export default function ContextSummaryPanel({ metricItem }) {
  if (!metricItem) return null;

  return (
    <div className="ob-info-summary-box">
      <div className="ob-info-item">
        <span className="ob-info-label">이슈그룹</span>
        <span className="ob-info-val">{metricItem.issueGroup || metricItem.category || '-'}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">대표 코드 (Metric ID)</span>
        <span className="ob-info-val">{metricItem.issueId || metricItem.metricId}</span>
      </div>
      <div className="ob-info-item">
        <span className="ob-info-label">입력 수준 / 유형</span>
        <span className="ob-info-val" style={{ color: '#0284c7' }}>
          MIXED (정성+정량 혼합)
        </span>
      </div>
      <div className="ob-info-item" style={{ flex: 1 }}>
        <span className="ob-info-label">지표 설명</span>
        <span className="ob-info-val" style={{ fontSize: '0.85rem' }}>
          {metricItem.checklistQuestion || metricItem.metricDescription || '입력 가이드 및 설명이 표시됩니다.'}
        </span>
      </div>
    </div>
  );
}
