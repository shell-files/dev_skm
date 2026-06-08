import { useState } from "react";
import { createPortal } from "react-dom";
import { useDispatch, useSelector } from "react-redux";
import { sendRollupSource } from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "중대성 평가 사전 입력";
  return value || "-";
};

const SubsidiaryTransferModal = ({
  isOpen,
  onClose,
  onTransferred,
}) => {
  const dispatch = useDispatch();
  const [sending, setSending] = useState(false);

  const activeRequest = useSelector((state) => state.report.rollup.selectedRequestDetail);
  const sendingSource = useSelector((state) => state.report.loading.sendSource);

  if (!isOpen || !activeRequest) return null;

  const handleSend = async () => {
    if (!activeRequest.batchId) return;

    if (!activeRequest.sendReadyYn) {
      showDefaultAlert("안내", "모든 필요한 지표의 승인이 완료되어야 전송할 수 있습니다.", "info");
      return;
    }

    setSending(true);
    try {
      await dispatch(sendRollupSource({ batchId: activeRequest.batchId })).unwrap();
      showDefaultAlert("성공", "데이터가 지주사로 성공적으로 전송되었습니다.", "success");
      onTransferred?.();
      onClose();
    } catch (error) {
      showDefaultAlert("오류", error.message || "데이터 전송 중 문제가 발생했습니다.", "error");
    } finally {
      setSending(false);
    }
  };

  const requestedMetricCount = activeRequest.requestedMetricCount || 0;
  const requiredAtomicCount = activeRequest.requiredAtomicCount || 0;
  const missingAtomicCount = activeRequest.missingAtomicCount || activeRequest.missingAtomicMetricIds?.length || 0;
  const isSendReady = activeRequest.sendReadyYn === true;

  return createPortal(
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: "500px", maxWidth: "90vw" }}>
        <div className="ob1-modal-header">
          <h2 className="ob1-modal-title">데이터 전송 확인</h2>
          <button className="ob1-modal-close" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>

        <div className="ob1-modal-body">
          <div style={{ marginBottom: "16px", padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.9rem" }}>
              <div>
                <span style={{ color: "#64748b", display: "block", fontSize: "0.8rem" }}>요청 기관(지주사)</span>
                <strong style={{ color: "#1e293b" }}>{activeRequest.parentCompanyName || activeRequest.parentCompanyId}</strong>
              </div>
              <div>
                <span style={{ color: "#64748b", display: "block", fontSize: "0.8rem" }}>보고연도</span>
                <strong style={{ color: "#1e293b" }}>{activeRequest.reportingYear}</strong>
              </div>
              <div>
                <span style={{ color: "#64748b", display: "block", fontSize: "0.8rem" }}>요청 유형</span>
                <strong style={{ color: "#1e293b" }}>{purposeLabel(activeRequest.rollupPurposeCode)}</strong>
              </div>
              <div>
                <span style={{ color: "#64748b", display: "block", fontSize: "0.8rem" }}>승인 완료 상태</span>
                {isSendReady ? (
                  <strong style={{ color: "#059669" }}>완료 (전송 가능)</strong>
                ) : (
                  <strong style={{ color: "#ea580c" }}>대기중</strong>
                )}
              </div>
            </div>
            <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px dashed #cbd5e1" }}>
               <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                 <span style={{ color: "#64748b", fontSize: "0.8rem" }}>요청 지표</span>
                 <strong style={{ color: "#1e293b" }}>{requestedMetricCount}개</strong>
               </div>
               <div style={{ display: "flex", justifyContent: "space-between" }}>
                 <span style={{ color: "#64748b", fontSize: "0.8rem" }}>전송 원천 데이터</span>
                 <strong style={{ color: "#1e293b" }}>{requiredAtomicCount}개</strong>
               </div>
               {!isSendReady && missingAtomicCount > 0 && (
                 <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
                   <span style={{ color: "#ea580c", fontSize: "0.8rem", fontWeight: "600" }}>미승인 원천 데이터</span>
                   <strong style={{ color: "#ea580c" }}>{missingAtomicCount}개</strong>
                 </div>
               )}
            </div>
          </div>

          <div style={{ marginTop: "24px", padding: "16px", background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: "8px", fontSize: "0.85rem", color: "#9a3412" }}>
            <ul style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <li><strong>현재 회사의 독립 기준 원천값만 전송합니다.</strong></li>
              <li>연결 합산 값은 포함되지 않습니다.</li>
            </ul>
          </div>
        </div>

        <div className="ob1-modal-footer">
          <button className="ob1-btn-secondary" onClick={onClose} disabled={sending || sendingSource}>
            취소
          </button>
          <button 
            className="ob1-request-btn" 
            onClick={handleSend} 
            disabled={sending || sendingSource || !isSendReady}
            style={(!isSendReady) ? { opacity: 0.6, cursor: "not-allowed" } : {}}
          >
            {sending || sendingSource ? "전송 중..." : "전송하기"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default SubsidiaryTransferModal;
