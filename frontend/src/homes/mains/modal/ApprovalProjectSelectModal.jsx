import React from 'react';
import { createPortal } from 'react-dom';

export default function ApprovalProjectSelectModal({
  isOpen,
  projects,
  selectedRunId,
  onSelectProject,
  onClose,
}) {
  if (!isOpen) return null;

  // sort projects: 1. reportingYear desc, 2. active first
  const sortedProjects = [...(projects || [])].sort((a, b) => {
    if (a.reportingYear !== b.reportingYear) {
      return (b.reportingYear || 0) - (a.reportingYear || 0);
    }
    const aActive = a.runStatus === 'ACTIVE' ? 1 : 0;
    const bActive = b.runStatus === 'ACTIVE' ? 1 : 0;
    return bActive - aActive;
  });

  return createPortal(
    <div className="ob-modal-overlay" onClick={onClose} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="ob-modal-shell" onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: '12px', width: '100%', maxWidth: '700px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
        <div className="ob-modal-header" style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="ob-modal-title" style={{ fontSize: '1.25rem', margin: '0 0 4px 0', color: '#1e293b' }}>데이터 승인 프로젝트 선택</h2>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>승인 작업을 확인할 보고서 프로젝트를 선택하세요.</p>
          </div>
          <button type="button" aria-label="프로젝트 선택 모달 닫기" onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b' }}>×</button>
        </div>
        
        <div className="ob-modal-body approval-project-select-list" style={{ padding: '24px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {sortedProjects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b' }}>
              <p style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: 600 }}>표시할 보고서 프로젝트가 없습니다.</p>
              <p style={{ margin: 0, fontSize: '0.9rem' }}>보고서 프로젝트를 먼저 시작해 주세요.</p>
            </div>
          ) : (
            sortedProjects.map(project => {
              const isSelected = project.runId === selectedRunId;
              const isCompleted = project.runStatus === 'COMPLETED';
              
              return (
                <div 
                  key={project.runId} 
                  className={`approval-project-select-card ${isSelected ? 'selected' : ''}`}
                  style={{ 
                    border: `1px solid ${isSelected ? '#10b981' : '#e2e8f0'}`,
                    borderRadius: '8px', 
                    padding: '20px', 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: isSelected ? '#ecfdf5' : '#fff',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  onClick={() => onSelectProject?.(project)}
                >
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                    <div style={{ 
                      width: '20px', 
                      height: '20px', 
                      borderRadius: '50%', 
                      border: `2px solid ${isSelected ? '#10b981' : '#cbd5e1'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginTop: '4px'
                    }}>
                      {isSelected && <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }} />}
                    </div>
                    <div>
                      <h3 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', color: '#1e293b' }}>
                        {project.reportingYear} 지속가능경영보고서
                      </h3>
                      <p style={{ margin: '0 0 12px 0', fontSize: '0.85rem', color: '#64748b' }}>
                        {project.reportBasisType === "CONSOLIDATED" ? "연결 기준" : "개별 기준"}
                        {" · "}
                        {isCompleted ? "완료" : "진행 중"}
                      </p>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className="approval-project-status-chip" style={{ 
                          padding: '4px 8px', 
                          borderRadius: '4px', 
                          fontSize: '0.8rem', 
                          fontWeight: 600,
                          background: isCompleted ? '#e0e7ff' : '#dcfce7',
                          color: isCompleted ? '#4338ca' : '#15803d'
                        }}>
                          현재 단계 · {project.currentStageLabel}
                        </span>
                        
                        {!isCompleted && project.pendingCount > 0 && (
                          <span style={{ fontSize: '0.85rem', color: '#64748b' }}>승인 대기 {project.pendingCount}건</span>
                        )}
                        
                        {project.readOnlyYn && (
                          <span className="approval-project-readonly-chip" style={{ fontSize: '0.85rem', color: '#94a3b8' }}>읽기 전용</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <button 
                    type="button" 
                    style={{ 
                      padding: '8px 16px', 
                      borderRadius: '6px', 
                      background: isCompleted ? '#fff' : '#059669', 
                      color: isCompleted ? '#059669' : '#fff',
                      border: `1px solid #059669`,
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectProject?.(project);
                    }}
                  >
                    {isCompleted ? '작업함 보기' : '작업함 열기'}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
