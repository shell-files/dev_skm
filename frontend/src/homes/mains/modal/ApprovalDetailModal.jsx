import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export default function ApprovalDetailModal({
  isOpen,
  onClose,
  metricItem,
  viewerRole,
  hasConsultant = false,
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
  const metricId = metricItem.metricId || metricItem.id;

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
          <h2 className="ob-modal-title" style={titleStyle}>Approval detail</h2>
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
          <div style={summaryStyle}>
            <InfoRow label="Metric" value={metricItem.metricName || metricItem.checklistQuestion || "-"} />
            <InfoRow label="Metric ID" value={metricItem.metricId || metricItem.id || "-"} />
            <InfoRow label="Assignee" value={metricItem.assigneeName || metricItem.userName || "-"} />
            <InfoRow label="Submitted" value={metricItem.submittedAt || "-"} />
          </div>

          <div style={tableBoxStyle}>
            <table style={tableStyle}>
              <thead style={tableHeadStyle}>
                <tr>
                  <th style={thStyle}>Input item</th>
                  <th style={thStyle}>Value</th>
                  <th style={thStyle}>Unit</th>
                </tr>
              </thead>
              <tbody>
                <tr style={tableRowStyle}>
                  <td style={tdStyle}>{metricItem.metricName || "Primary value"}</td>
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{metricItem.value ?? "-"}</td>
                  <td style={{ ...tdStyle, color: "#64748b" }}>{metricItem.unit ?? "-"}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <h4 style={sectionTitleStyle}>Evidence</h4>
            <div style={emptyEvidenceStyle}>No attached evidence.</div>
          </div>

          <div style={{ marginBottom: "8px" }}>
            <h4 style={sectionTitleStyle}>Rejection reason</h4>
            <textarea
              style={textareaStyle}
              placeholder="Enter rejection reason."
              value={rejectReason}
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
              cursor: rejectReason.trim() ? "pointer" : "not-allowed",
              opacity: rejectReason.trim() ? 1 : 0.5,
            }}
            onClick={() => onReject?.({ metricId, commentText: rejectReason })}
            disabled={!rejectReason.trim()}
            title={!rejectReason.trim() ? "Enter rejection reason." : ""}
          >
            Reject
          </button>

          {isConsultant ? (
            <button
              type="button"
              className="ob-btn ob-btn-primary"
              style={primaryButtonStyle}
              onClick={() => onReview?.({ metricId, commentText: "" })}
            >
              Mark reviewed
            </button>
          ) : (
            <button
              type="button"
              className="ob-btn ob-btn-primary"
              style={{
                ...primaryButtonStyle,
                background: canApprove ? "#059669" : "#94a3b8",
                cursor: canApprove ? "pointer" : "not-allowed",
              }}
              onClick={() => onApprove?.({ metricId, commentText: "" })}
              disabled={!canApprove}
              title={!canApprove ? "Consultant review must be completed first." : ""}
            >
              Approve
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
  maxWidth: "700px",
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
  marginBottom: "24px",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  overflow: "hidden",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.9rem",
  textAlign: "left",
};

const tableHeadStyle = {
  background: "#f8fafc",
  borderBottom: "1px solid #e2e8f0",
};

const thStyle = {
  padding: "12px 16px",
  fontWeight: 600,
  color: "#475569",
};

const tableRowStyle = {
  borderBottom: "1px solid #e2e8f0",
};

const tdStyle = {
  padding: "12px 16px",
  color: "#1e293b",
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
