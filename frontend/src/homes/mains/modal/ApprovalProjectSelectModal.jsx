import React from "react";
import { createPortal } from "react-dom";

const statusLabel = (project = {}) => {
  const status = String(project.runStatus || "ACTIVE").toUpperCase();
  if (status === "COMPLETED") return "완료";
  if (status === "ARCHIVED") return "보관됨";
  return "진행 중";
};

const basisLabel = (basisType) => {
  if (basisType === "CONSOLIDATED") return "연결 기준";
  if (basisType === "ENTITY") return "독립 기준";
  return "기준 미선택";
};

const formatStageLabel = (label) => {
  if (!label) return "-";
  const lower = String(label).toLowerCase();
  if (lower.includes("g0") || lower.includes("pre_dma")) return "경영일반 입력";
  if (lower.includes("all approvals") || lower.includes("completed")) return "데이터 승인 완료";
  if (lower.includes("disclosure") || lower.includes("post_dma")) return "중대성 이슈 데이터";
  return label;
};

export default function ApprovalProjectSelectModal({
  isOpen,
  projects = [],
  selectedRunId,
  onSelectProject,
  onClose,
}) {
  if (!isOpen) return null;

  const sortedProjects = [...projects].sort((a, b) => {
    if ((a.reportingYear || 0) !== (b.reportingYear || 0)) {
      return (b.reportingYear || 0) - (a.reportingYear || 0);
    }
    return (b.runId || 0) - (a.runId || 0);
  });

  return createPortal(
    <div
      className="ob-modal-overlay"
      onClick={onClose}
      style={overlayStyle}
    >
      <div
        className="ob-modal-shell"
        onClick={(event) => event.stopPropagation()}
        style={shellStyle}
      >
        <div className="ob-modal-header" style={headerStyle}>
          <div>
            <h2 className="ob-modal-title" style={titleStyle}>
              보고서 프로젝트 선택
            </h2>
            <p style={descriptionStyle}>
              조회할 연도별 지속가능경영보고서 프로젝트를 선택하세요.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close report project selector"
            onClick={onClose}
            style={closeButtonStyle}
          >
            x
          </button>
        </div>

        <div className="ob-modal-body approval-project-select-list" style={bodyStyle}>
          {sortedProjects.length === 0 ? (
            <div style={emptyStyle}>
              <p style={emptyTitleStyle}>조회 가능한 보고서 프로젝트가 없습니다.</p>
              <p style={descriptionStyle}>먼저 보고서 워크플로우 프로젝트를 시작해 주세요.</p>
            </div>
          ) : (
            sortedProjects.map((project) => {
              const isSelected = project.runId === selectedRunId;
              const isReadOnly = Boolean(project.readOnlyYn);

              return (
                <div
                  key={project.runId}
                  className={`approval-project-select-card ${isSelected ? "selected" : ""}`}
                  style={{
                    ...cardStyle,
                    borderColor: isSelected ? "#10b981" : "#e2e8f0",
                    background: isSelected ? "#ecfdf5" : "#fff",
                  }}
                  onClick={() => onSelectProject?.(project)}
                >
                  <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                    <div
                      style={{
                        ...radioStyle,
                        borderColor: isSelected ? "#10b981" : "#cbd5e1",
                      }}
                    >
                      {isSelected && <div style={radioInnerStyle} />}
                    </div>
                    <div>
                      <h3 style={projectTitleStyle}>
                        {project.reportingYear} 지속가능경영보고서
                      </h3>
                      <p style={projectMetaStyle}>
                        {basisLabel(project.reportBasisType)} · {statusLabel(project)}
                      </p>
                      <div style={chipRowStyle}>
                        <span
                          className="approval-project-status-chip"
                          style={{
                            ...stageChipStyle,
                            background: isReadOnly ? "#e0e7ff" : "#dcfce7",
                            color: isReadOnly ? "#4338ca" : "#15803d",
                          }}
                        >
                          현재 단계 · {formatStageLabel(project.currentStageLabel)}
                        </span>

                        {!isReadOnly && Number(project.pendingCount || 0) > 0 && (
                          <span style={metaTextStyle}>
                            대기 {project.pendingCount}건
                          </span>
                        )}

                        {isReadOnly && (
                          <span className="approval-project-readonly-chip" style={readonlyTextStyle}>
                            읽기 전용
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    style={{
                      ...selectButtonStyle,
                      background: isSelected ? "#059669" : "#fff",
                      color: isSelected ? "#fff" : "#059669",
                    }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectProject?.(project);
                    }}
                  >
                    조회하기
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

const overlayStyle = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0,0,0,0.5)",
  zIndex: 1000,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const shellStyle = {
  background: "#fff",
  borderRadius: "12px",
  width: "100%",
  maxWidth: "700px",
  maxHeight: "90vh",
  display: "flex",
  flexDirection: "column",
  boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
};

const headerStyle = {
  padding: "20px 24px",
  borderBottom: "1px solid #e2e8f0",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const titleStyle = {
  fontSize: "1.25rem",
  margin: "0 0 4px 0",
  color: "#1e293b",
};

const descriptionStyle = {
  margin: 0,
  fontSize: "0.9rem",
  color: "#64748b",
};

const closeButtonStyle = {
  border: "none",
  background: "none",
  fontSize: "1.5rem",
  cursor: "pointer",
  color: "#64748b",
};

const bodyStyle = {
  padding: "24px",
  flex: 1,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "16px",
};

const emptyStyle = {
  textAlign: "center",
  padding: "40px 0",
  color: "#64748b",
};

const emptyTitleStyle = {
  margin: "0 0 8px 0",
  fontSize: "1rem",
  fontWeight: 600,
};

const cardStyle = {
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  padding: "20px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  cursor: "pointer",
  transition: "all 0.2s ease",
};

const radioStyle = {
  width: "20px",
  height: "20px",
  borderRadius: "50%",
  border: "2px solid #cbd5e1",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  marginTop: "4px",
};

const radioInnerStyle = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: "#10b981",
};

const projectTitleStyle = {
  margin: "0 0 6px 0",
  fontSize: "1.1rem",
  color: "#1e293b",
};

const projectMetaStyle = {
  margin: "0 0 12px 0",
  fontSize: "0.85rem",
  color: "#64748b",
};

const chipRowStyle = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  flexWrap: "wrap",
};

const stageChipStyle = {
  padding: "4px 8px",
  borderRadius: "4px",
  fontSize: "0.8rem",
  fontWeight: 600,
};

const metaTextStyle = {
  fontSize: "0.85rem",
  color: "#64748b",
};

const readonlyTextStyle = {
  fontSize: "0.85rem",
  color: "#94a3b8",
};

const selectButtonStyle = {
  padding: "8px 16px",
  borderRadius: "6px",
  border: "1px solid #059669",
  fontWeight: 600,
  cursor: "pointer",
  width: "120px",
  textAlign: "center",
  whiteSpace: "nowrap",
};
