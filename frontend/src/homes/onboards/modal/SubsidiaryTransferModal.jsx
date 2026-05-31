import { useState, useEffect } from "react";
import { listRequests, sendSource } from "@/apis/report";
import { showDefaultAlert, showConfirmAlert } from "@components/UI/ServiceAlert";

/**
 * SubsidiaryTransferModal
 *
 * 지주사 데이터 전송 modal.
 * DTO: res.data.items → {
 *   batchId, parentCompanyName, reportingYear,
 *   metricScopeCode, sendReadyYn, missingAtomicMetricIds
 * }
 * sendReadyYn=false 면 전송 비활성화
 */
const SubsidiaryTransferModal = ({ isOpen, onClose, onTransferred }) => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedBatchId, setSelectedBatchId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadRequests();
    } else {
      setSelectedBatchId(null);
      setError(null);
    }
  }, [isOpen]);

  const loadRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listRequests();
      const isFailed =
        res?.status === false || res?.success === false || !res?.data;

      if (isFailed) {
        setRequests([]);
        setError(res?.error?.message || "요청 목록 조회에 실패했습니다.");
        return;
      }

      setRequests(res.data.items || res.data || []);
    } catch (err) {
      console.error(err);
      setRequests([]);
      setError("요청 목록 조회에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const selectedRequest = requests.find((r) => r.batchId === selectedBatchId);
  const canSend =
    selectedBatchId &&
    selectedRequest?.sendReadyYn !== false &&
    !sending;

  const handleSend = async () => {
    if (!selectedBatchId) return;

    /* sendReadyYn 체크 */
    if (selectedRequest?.sendReadyYn === false) {
      const missing = selectedRequest.missingAtomicMetricIds || [];
      showDefaultAlert(
        "전송 불가",
        `필수 입력 항목이 누락되어 전송할 수 없습니다.${missing.length > 0 ? `\n누락 항목: ${missing.join(", ")}` : ""}`,
        "warning"
      );
      return;
    }

    const confirm = await showConfirmAlert(
      "데이터 전송",
      "현재까지 입력/승인한 G0 데이터를 지주사로 전송하시겠습니까?",
      "question"
    );
    if (!confirm) return;

    setSending(true);
    try {
      const res = await sendSource(selectedBatchId);
      const isFailed =
        res?.status === false || res?.success === false;

      if (!isFailed) {
        showDefaultAlert("전송 완료", "지주사로 데이터 전송이 완료되었습니다.", "success");
        onTransferred?.(selectedBatchId);
        onClose();
      } else {
        showDefaultAlert("오류", res?.error?.message || "데이터 전송에 실패했습니다.", "error");
      }
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", "데이터 전송에 실패했습니다.", "error");
    } finally {
      setSending(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 500 }}>
        <div className="ob1-modal-header">
          <h2>지주사 데이터 전송 요건 확인</h2>
          <button className="ob1-btn-close" onClick={onClose}>×</button>
        </div>
        <div className="ob1-modal-body">
          <p style={{ marginBottom: 16, fontSize: "0.9rem", color: "#475569" }}>
            지주사에서 접수한 데이터 요청 목록입니다. 전송할 요청을 선택해 주세요.
          </p>

          {/* loading */}
          {loading && (
            <div className="ob1-table-loading" style={{ padding: "24px" }}>
              <div className="ob1-spinner" />
              <p>요청 목록 불러오는 중...</p>
            </div>
          )}

          {/* error */}
          {!loading && error && (
            <div className="ob1-inline-error" style={{ margin: "16px 0" }}>
              <span className="ob1-error-icon">⚠</span>
              <span>{error}</span>
              <button type="button" className="ob1-btn-retry" onClick={loadRequests}>
                다시 시도
              </button>
            </div>
          )}

          {/* empty */}
          {!loading && !error && requests.length === 0 && (
            <div style={{ padding: "24px", textAlign: "center", color: "#64748b" }}>
              대기 중인 요청이 없습니다.
            </div>
          )}

          {/* list */}
          {!loading && !error && requests.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {requests.map((req) => {
                const isNotReady = req.sendReadyYn === false;
                return (
                  <label
                    key={req.batchId}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "16px",
                      border: `1px solid ${selectedBatchId === req.batchId ? "#3b82f6" : "#e2e8f0"}`,
                      borderRadius: "8px",
                      cursor: isNotReady ? "not-allowed" : "pointer",
                      background: selectedBatchId === req.batchId
                        ? "#eff6ff"
                        : isNotReady
                          ? "#fefce8"
                          : "#fff",
                      opacity: isNotReady ? 0.8 : 1,
                    }}
                  >
                    <input
                      type="radio"
                      name="requestBatch"
                      value={req.batchId}
                      checked={selectedBatchId === req.batchId}
                      onChange={() => setSelectedBatchId(req.batchId)}
                      disabled={isNotReady}
                      style={{ marginTop: "4px" }}
                    />
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div style={{ fontWeight: 600, color: "#1e293b" }}>
                        {req.parentCompanyName || "데이터 요청"}
                      </div>
                      <div style={{ fontSize: "0.85rem", color: "#64748b" }}>
                        보고년도: {req.reportingYear || "-"}
                        {req.metricScopeCode && ` · 범위: ${req.metricScopeCode}`}
                      </div>
                      {isNotReady && (
                        <div style={{ fontSize: "0.8rem", color: "#d97706", marginTop: "4px" }}>
                          ⚠ 필수 항목 미완료 — 전송 불가
                          {req.missingAtomicMetricIds?.length > 0 && (
                            <span style={{ display: "block", marginTop: "2px", fontSize: "0.75rem", color: "#92400e" }}>
                              누락: {req.missingAtomicMetricIds.join(", ")}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>
        <div
          className="ob1-modal-footer"
          style={{
            borderTop: "1px solid #e2e8f0",
            padding: "16px",
            display: "flex",
            justifyContent: "flex-end",
            gap: "8px",
          }}
        >
          <button
            style={{
              padding: "8px 16px",
              border: "1px solid #cbd5e1",
              background: "#fff",
              borderRadius: "4px",
              cursor: "pointer",
            }}
            onClick={onClose}
          >
            취소
          </button>
          <button
            style={{
              padding: "8px 16px",
              background: canSend ? "#1d4ed8" : "#94a3b8",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: canSend ? "pointer" : "not-allowed",
              opacity: canSend ? 1 : 0.5,
            }}
            onClick={handleSend}
            disabled={!canSend}
          >
            {sending ? "전송 중..." : "지주사에 전송하기"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubsidiaryTransferModal;
