import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const FIXTURE_ATOMIC_ITEMS = [
  { atomicMetricId: "E1-1-a", atomicMetricName: "Scope 1 온실가스 직접 배출량", value: "12,450", unit: "tCO₂e", inputType: "MANUAL_NUMBER", evidenceCount: 2, inputStatus: "COMPLETED" },
  { atomicMetricId: "E1-1-b", atomicMetricName: "Scope 2 온실가스 간접 배출량", value: "8,320", unit: "tCO₂e", inputType: "MANUAL_NUMBER", evidenceCount: 1, inputStatus: "COMPLETED" },
  { atomicMetricId: "E1-1-c", atomicMetricName: "배출 산정 기준", value: "GHG Protocol", unit: "-", inputType: "SELECT", evidenceCount: 0, inputStatus: "COMPLETED" },
  { atomicMetricId: "E1-1-d", atomicMetricName: "검증 여부", value: "", unit: "-", inputType: "MANUAL_TEXT", evidenceCount: 0, inputStatus: "NOT_STARTED" },
];

export default function ApprovalDetailModal({
  isOpen,
  onClose,
  metricItem,
  viewerRole,
  hasConsultant = false,
  readOnlyYn = false,
  modalActionMode = null,
  onReview,
  onApprove,
  onReject,
}) {
  const [rejectReason, setRejectReason] = useState("");

  useEffect(() => {
    if (isOpen) {
      setRejectReason("");
    }
  }, [isOpen]);

  if (!isOpen || !metricItem) return null;

  const isConsultant =
    String(viewerRole || "").toUpperCase() === "CONSULTANT" ||
    String(viewerRole || "").toUpperCase().includes("CONSULTANT");
  const isReviewed = metricItem.reviewStatus === "REVIEWED";
  const canApprove = isConsultant ? false : !hasConsultant || isReviewed;
  const rejectDisabled = readOnlyYn || !rejectReason.trim();
  const approveDisabled = readOnlyYn || !canApprove;
  const metricId = metricItem.metricId || metricItem.id;
  const isApproveMode = modalActionMode === "approve";

  const atomicItems = metricItem.atomicItems || FIXTURE_ATOMIC_ITEMS;
  const totalEvidenceCount = atomicItems.reduce((sum, item) => sum + (item.evidenceCount || 0), 0);

  const handleApproveClick = () => {
    showDefaultAlert("안내", "최종 승인 API 연결은 후속 단계에서 진행됩니다.", "info");
  };

  const handleReviewClick = () => {
    showDefaultAlert("안내", "검토 완료 API 연결은 후속 단계에서 진행됩니다.", "info");
  };

  return createPortal(
    <div
      className="ob-modal-overlay"
      onClick={onClose}
      style={overlayStyle}
    >
      <div
        className="ob-modal-shell ob-approval-modal"
        onClick={(event) => event.stopPropagation()}
        style={shellStyle}
      >
        <div className="ob-modal-header" style={headerStyle}>
          <h2 className="ob-modal-title" style={titleStyle}>
            {isApproveMode ? "최종 승인 — Atomic 상세 검토" : "Approval detail"}
          </h2>
          <button
            type="button"
            aria-label="Close approval detail modal"
            className="ob1-btn-close"
            onClick={onClose}
            style={closeButtonStyle}
          >
            x
          </button>
        </div>

        <div className="ob-modal-body" style={bodyStyle}>
          {readOnlyYn && (
            <div className="alert alert-info" style={readOnlyAlertStyle}>
              Completed projects are read-only.
            </div>
          )}

          {isApproveMode && (
            <div style={{ marginBottom: '16px', padding: '12px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a', fontSize: '0.85rem', color: '#92400e' }}>
              최종 승인 전에 아래 Atomic 상세 항목을 검토하세요.
            </div>
          )}

          <div style={summaryStyle}>
            <InfoRow label="Metric" value={metricItem.metricName || metricItem.checklistQuestion || "-"} />
            <InfoRow label="Metric ID" value={metricItem.metricId || metricItem.id || "-"} />
            <InfoRow label="Sub-Issue" value={metricItem.subIssueName || metricItem.sub_issue_name || metricItem.subIssueCode || "-"} />
            <InfoRow label="Assignee" value={metricItem.assigneeName || metricItem.userName || "-"} />
            <InfoRow label="Submitted" value={metricItem.submittedAt || "-"} />
          </div>

          {/* Atomic detail table */}
          <div style={{ marginBottom: "24px" }}>
            <h4 style={sectionTitleStyle}>Atomic Metric 상세</h4>
            <div style={tableBoxStyle}>
              <table style={tableStyle}>
                <thead style={tableHeadStyle}>
                  <tr>
                    <th style={thStyle}>Atomic Metric ID</th>
                    <th style={thStyle}>입력 항목명</th>
                    <th style={thStyle}>입력값</th>
                    <th style={thStyle}>단위</th>
                    <th style={thStyle}>입력 유형</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>증빙</th>
                    <th style={thStyle}>입력 상태</th>
                  </tr>
                </thead>
                <tbody>
                  {atomicItems.map((atomic, idx) => {
                    const statusLabel = atomic.inputStatus === "COMPLETED" ? "완료" : atomic.inputStatus === "IN_PROGRESS" ? "작성중" : "미입력";
                    const statusCls = atomic.inputStatus === "COMPLETED" ? "#16a34a" : atomic.inputStatus === "IN_PROGRESS" ? "#d97706" : "#94a3b8";
                    return (
                      <tr key={atomic.atomicMetricId || idx} style={tableRowStyle}>
                        <td style={{ ...tdStyle, fontWeight: 600, fontSize: "0.8rem", color: "#475569" }}>{atomic.atomicMetricId}</td>
                        <td style={tdStyle}>{atomic.atomicMetricName}</td>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{atomic.value || "-"}</td>
                        <td style={{ ...tdStyle, color: "#64748b" }}>{atomic.unit || "-"}</td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: "11px", background: "#f1f5f9", padding: "2px 8px", borderRadius: "4px" }}>
                            {atomic.inputType || "-"}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>{atomic.evidenceCount || 0}</td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: "12px", fontWeight: 600, color: statusCls }}>{statusLabel}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <h4 style={sectionTitleStyle}>Evidence</h4>
            {totalEvidenceCount > 0 ? (
              <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "0.85rem", color: "#334155" }}>
                첨부 증빙 {totalEvidenceCount}건<br />
                <span style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "4px", display: "inline-block" }}>상세 파일 목록은 API 연결 후 표시됩니다.</span>
              </div>
            ) : (
              <div style={emptyEvidenceStyle}>첨부된 증빙이 없습니다.</div>
            )}
          </div>

          <div style={{ marginBottom: "8px" }}>
            <h4 style={sectionTitleStyle}>Rejection reason</h4>
            <textarea
              style={textareaStyle}
              placeholder="Enter rejection reason."
              value={rejectReason}
              disabled={readOnlyYn}
              onChange={(event) => setRejectReason(event.target.value)}
            />
          </div>
        </div>

        <div className="ob-modal-footer" style={footerStyle}>
          <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose} style={secondaryButtonStyle}>
            Close
          </button>

          <button
            type="button"
            className="ob-btn"
            style={{
              ...rejectButtonStyle,
              cursor: rejectDisabled ? "not-allowed" : "pointer",
              opacity: rejectDisabled ? 0.5 : 1,
            }}
            onClick={() => onReject?.({ metricId, commentText: rejectReason })}
            disabled={rejectDisabled}
            title={
              readOnlyYn
                ? "Completed projects are read-only."
                : !rejectReason.trim()
                  ? "Enter rejection reason."
                  : ""
            }
          >
            Reject
          </button>

          {isConsultant ? (
            <button
              type="button"
              className="ob-btn ob-btn-primary"
              style={{
                ...primaryButtonStyle,
                cursor: readOnlyYn ? "not-allowed" : "pointer",
                opacity: readOnlyYn ? 0.5 : 1,
              }}
              onClick={handleReviewClick}
              disabled={readOnlyYn}
              title={readOnlyYn ? "Completed projects are read-only." : ""}
            >
              Mark reviewed
            </button>
          ) : (
            <button
              type="button"
              className="ob-btn ob-btn-primary"
              style={{
                ...primaryButtonStyle,
                background: approveDisabled ? "#94a3b8" : "#059669",
                cursor: approveDisabled ? "not-allowed" : "pointer",
              }}
              onClick={handleApproveClick}
              disabled={approveDisabled}
              title={
                readOnlyYn
                  ? "Completed projects are read-only."
                  : !canApprove
                    ? "Consultant review must be completed first."
                    : ""
              }
            >
              {isApproveMode ? "최종 승인" : "Approve"}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

const InfoRow = ({ label, value }) => (
  <div style={{ display: "flex", gap: "16px", marginBottom: "8px" }}>
    <span style={infoLabelStyle}>{label}</span>
    <span style={infoValueStyle}>{value}</span>
  </div>
);

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
  maxWidth: "860px",
  maxHeight: "90vh",
  display: "flex",
  flexDirection: "column",
  boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
};

const headerStyle = {
  padding: "20px 24px",
  borderBottom: "1px solid #e2e8f0",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const titleStyle = {
  fontSize: "1.1rem",
  margin: 0,
  color: "#1e293b",
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
};

const summaryStyle = {
  marginBottom: "24px",
  background: "#f8fafc",
  padding: "16px",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
};

const readOnlyAlertStyle = {
  marginBottom: "12px",
};

const infoLabelStyle = {
  fontWeight: 600,
  color: "#475569",
  minWidth: "80px",
  fontSize: "0.9rem",
};

const infoValueStyle = {
  color: "#1e293b",
  fontSize: "0.9rem",
};

const tableBoxStyle = {
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  overflow: "hidden",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.85rem",
  textAlign: "left",
};

const tableHeadStyle = {
  background: "#f8fafc",
  borderBottom: "1px solid #e2e8f0",
};

const thStyle = {
  padding: "10px 12px",
  fontWeight: 600,
  color: "#475569",
  fontSize: "0.8rem",
};

const tableRowStyle = {
  borderBottom: "1px solid #f1f5f9",
};

const tdStyle = {
  padding: "10px 12px",
  color: "#1e293b",
  fontSize: "0.85rem",
};

const sectionTitleStyle = {
  fontSize: "0.95rem",
  marginBottom: "8px",
  color: "#1e293b",
};

const emptyEvidenceStyle = {
  padding: "16px",
  background: "#f8fafc",
  borderRadius: "8px",
  border: "1px dashed #cbd5e1",
  fontSize: "0.85rem",
  color: "#64748b",
  textAlign: "center",
};

const textareaStyle = {
  width: "100%",
  padding: "12px",
  borderRadius: "6px",
  border: "1px solid #cbd5e1",
  minHeight: "80px",
  resize: "vertical",
  fontSize: "0.9rem",
  fontFamily: "inherit",
};

const footerStyle = {
  padding: "16px 24px",
  borderTop: "1px solid #e2e8f0",
  background: "#f8fafc",
  display: "flex",
  justifyContent: "flex-end",
  gap: "8px",
  borderBottomLeftRadius: "12px",
  borderBottomRightRadius: "12px",
};

const secondaryButtonStyle = {
  padding: "8px 16px",
  borderRadius: "6px",
  border: "1px solid #cbd5e1",
  background: "#fff",
  color: "#475569",
  cursor: "pointer",
  fontWeight: 600,
};

const rejectButtonStyle = {
  padding: "8px 16px",
  borderRadius: "6px",
  background: "#fff",
  border: "1px solid #fecaca",
  color: "#dc2626",
  fontWeight: 600,
};

const primaryButtonStyle = {
  padding: "8px 16px",
  borderRadius: "6px",
  background: "#2563eb",
  border: "none",
  color: "#fff",
  cursor: "pointer",
  fontWeight: 600,
};
