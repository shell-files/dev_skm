import React from 'react';

export default function ModalHeader({ metricItem }) {
  if (!metricItem) return null;

  const getStatusText = (status) => {
    switch(status) {
      case 'DRAFT': return '작성중';
      case 'SUBMITTED': return '검토요청';
      case 'APPROVED': return '완료';
      default: return '미입력';
    }
  };

  const getStatusClass = (status) => {
    switch(status) {
      case 'DRAFT': return 'draft';
      case 'SUBMITTED': return 'submitted';
      case 'APPROVED': return 'approved';
      default: return 'not-started';
    }
  };

  return (
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
}
