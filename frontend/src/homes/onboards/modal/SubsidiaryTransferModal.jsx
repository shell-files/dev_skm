import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  fetchRollupRequestDetail,
  fetchRollupRequests,
  sendRollupSource,
} from "@stores/reportSlice";
import { showConfirmAlert, showDefaultAlert } from "@components/UI/ServiceAlert";

const readinessLabel = (status) => {
  const value = String(status || "").toUpperCase();
  if (value === "READY") return "전송 가능";
  if (value === "PARTIAL") return "입력 진행중";
  if (value === "NOT_STARTED") return "미입력";
  return status || "-";
};

const transferLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "received") return "수신 완료";
  if (value === "sent") return "전송 완료";
  if (value === "not_sent") return "미전송";
  return status || "-";
};

const approvalLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "approved") return "승인 완료";
  if (value === "reviewed") return "검토 완료";
  if (value === "rejected") return "반려";
  if (value === "pending" || value === "submitted") return "승인 대기";
  return status || "-";
};

const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "DMA 사전 계산";
  return value || "-";
};

const metricMissingCount = (item = {}) =>
  item.currentMissingAtomicCount ??
  item.missingAtomicCount ??
  item.missingAtomicMetricIds?.length ??
  0;

const metricApprovedCount = (item = {}) =>
  item.currentApprovedAtomicCount ?? item.approvedAtomicCount ?? 0;

const MetricReadinessList = ({ title, description, items = [] }) => (
  <div style={{ marginTop: "14px" }}>
    <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "8px" }}>
      <strong style={{ color: "#0f172a" }}>{title}</strong>
      {description && <span style={{ fontSize: "0.78rem", color: "#64748b" }}>{description}</span>}
    </div>
    {items.length === 0 ? (
      <div style={{ padding: "12px", border: "1px dashed #cbd5e1", borderRadius: "8px", color: "#64748b" }}>
        표시할 항목이 없습니다.
      </div>
    ) : (
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {items.map((item) => {
          const missing = item.missingAtomicMetricIds || [];
          return (
            <div key={item.metricId} style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                <div>
                  <div style={{ fontWeight: 700, color: "#1e293b" }}>{item.metricId}</div>
                  <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "2px" }}>
                    {item.metricName || item.metricNameKr || "-"}
                  </div>
                </div>
                <div style={{ fontSize: "0.82rem", color: "#475569", textAlign: "right" }}>
                  승인 {metricApprovedCount(item)} / 필요 {item.requiredAtomicCount ?? item.requiredCount ?? 0}
                  <br />
                  누락 {metricMissingCount(item)}
                </div>
              </div>
              {missing.length > 0 && (
                <div style={{ marginTop: "6px", fontSize: "0.78rem", color: "#b45309" }}>
                  누락 Atomic: {missing.join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>
    )}
  </div>
);

const SubsidiaryTransferModal = ({
  isOpen,
  onClose,
  onTransferred,
  onNavigateToInput,
  reportingYear,
}) => {
  const dispatch = useDispatch();
  const requests = useSelector((state) => state.report.rollup.requests);
  const requestDetail = useSelector((state) => state.report.rollup.selectedRequestDetail);
  const loadingRequests = useSelector((state) => state.report.loading.requests);
  const loadingDetail = useSelector((state) => state.report.loading.rollupRequestDetail);
  const sendingSource = useSelector((state) => state.report.loading.sendSource);
  const requestError = useSelector((state) => state.report.error.requests);
  const detailError = useSelector((state) => state.report.error.rollupRequestDetail);
  const [sending, setSending] = useState(false);
  const [selectedBatchId, setSelectedBatchId] = useState(null);
  const [error, setError] = useState(null);

  const loadRequests = useCallback(async () => {
    setError(null);
    try {
      await dispatch(fetchRollupRequests({ includeSentYn: true, allPurposesYn: true })).unwrap();
    } catch (err) {
      console.error(err);
      setError(err?.message || "요청 목록 조회에 실패했습니다.");
    }
  }, [dispatch]);

  const loadDetail = useCallback(async (batchId) => {
    if (!batchId) return;
    setError(null);
    try {
      await dispatch(fetchRollupRequestDetail({ batchId })).unwrap();
    } catch (err) {
      console.error(err);
      setError(err?.message || "요청 상세 조회에 실패했습니다.");
    }
  }, [dispatch]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      if (isOpen) {
        loadRequests();
      } else {
        setSelectedBatchId(null);
        setError(null);
      }
    });
    return () => {
      active = false;
    };
  }, [isOpen, loadRequests]);

  const selectedRequest = useMemo(
    () => requests.find((request) => request.batchId === selectedBatchId),
    [requests, selectedBatchId]
  );

  const activeDetail = requestDetail?.batchId === selectedBatchId ? requestDetail : null;
  const activeRequest = activeDetail || selectedRequest || {};
  const transferStatus = String(activeRequest.transferStatus || "").toLowerCase();
  const isTransferred = transferStatus === "sent" || transferStatus === "received";
  const currentMissingAtomicCount =
    activeRequest.currentMissingAtomicCount ??
    activeRequest.missingAtomicCount ??
    activeRequest.missingAtomicMetricIds?.length ??
    0;
  const sendReadyYn = activeRequest.sendReadyYn === true;
  const inputWorkspace = activeDetail?.inputWorkspace || activeRequest.inputWorkspace || {};
  const actionableInputMetricIds = inputWorkspace.actionableInputMetricIds || activeDetail?.actionableInputMetricIds || [];
  const canSend = selectedBatchId && sendReadyYn && !isTransferred && !sending && !sendingSource;
  const canNavigateToInput =
    selectedBatchId &&
    currentMissingAtomicCount > 0 &&
    inputWorkspace.availableYn === true;

  const handleSelectBatch = (batchId) => {
    setSelectedBatchId(batchId);
    loadDetail(batchId);
  };

  const handleNavigateInput = () => {
    if (!canNavigateToInput) return;
    const targetYear =
      inputWorkspace.reportingYear ||
      activeDetail?.reportingYear ||
      selectedRequest?.reportingYear ||
      reportingYear;
    const targetCycleType =
      inputWorkspace.cycleType ||
      activeDetail?.inputCycleType ||
      activeDetail?.cycleType ||
      "POST_DMA_DISCLOSURE";
    const metricId = actionableInputMetricIds[0] || activeDetail?.requestedMetricIds?.[0] || activeDetail?.metricIds?.[0];
    const params = new URLSearchParams({
      reportingYear: String(targetYear),
      cycleType: targetCycleType,
    });
    if (metricId) params.set("metricId", metricId);
    onNavigateToInput?.({
      url: `/onb?${params.toString()}`,
      reportingYear: targetYear,
      cycleType: targetCycleType,
      metricId,
    });
  };

  const handleSend = async () => {
    if (!selectedBatchId || !canSend) return;

    const confirm = await showConfirmAlert(
      "데이터 전송",
      "현재 승인 완료된 데이터를 지주사로 전송하시겠습니까?",
      "question"
    );
    if (!confirm) return;

    setSending(true);
    try {
      await dispatch(sendRollupSource({ batchId: selectedBatchId })).unwrap();
      await Promise.all([
        dispatch(fetchRollupRequests({ includeSentYn: true, allPurposesYn: true })).unwrap(),
        dispatch(fetchRollupRequestDetail({ batchId: selectedBatchId })).unwrap(),
      ]);
      showDefaultAlert("전송 완료", "지주사로 데이터 전송이 완료되었습니다.", "success");
      onTransferred?.(selectedBatchId);
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "데이터 전송에 실패했습니다.", "error");
    } finally {
      setSending(false);
    }
  };

  if (!isOpen) return null;

  const activeError = error || requestError?.message || detailError?.message;

  return createPortal(
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 920 }}>
        <div className="ob1-modal-header">
          <h2>지주사 데이터 전송 요청 확인</h2>
          <button className="ob1-btn-close" onClick={onClose}>×</button>
        </div>
        <div className="ob1-modal-body">
          <p style={{ marginBottom: 16, fontSize: "0.9rem", color: "#475569" }}>
            지주사에서 접수한 데이터 요청을 확인하고 전송할 수 있습니다.
          </p>

          {loadingRequests && requests.length === 0 && (
            <div className="ob1-table-loading" style={{ padding: "24px" }}>
              <div className="ob1-spinner" />
              <p>요청 목록을 불러오고 있습니다.</p>
            </div>
          )}

          {activeError && (
            <div className="ob1-inline-error" style={{ margin: "16px 0" }}>
              <span className="ob1-error-icon">!</span>
              <span>{activeError}</span>
              <button type="button" className="ob1-btn-retry" onClick={loadRequests}>
                다시 시도
              </button>
            </div>
          )}

          {!loadingRequests && !activeError && requests.length === 0 && (
            <div style={{ padding: "24px", textAlign: "center", color: "#64748b" }}>
              대기 중인 요청이 없습니다.
            </div>
          )}

          {requests.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "300px minmax(0, 1fr)", gap: "16px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "560px", overflow: "auto" }}>
                {requests.map((req) => {
                  const missing = req.currentMissingAtomicCount ?? req.missingAtomicCount ?? req.missingAtomicMetricIds?.length ?? 0;
                  const approved =
                    req.currentApprovedAtomicCount ??
                    req.approvedAtomicCount ??
                    0;
                  const required =
                    req.requiredAtomicCount ??
                    0;
                  return (
                    <button
                      key={req.batchId}
                      type="button"
                      onClick={() => handleSelectBatch(req.batchId)}
                      style={{
                        textAlign: "left",
                        padding: "14px",
                        border: `1px solid ${selectedBatchId === req.batchId ? "#3b82f6" : "#e2e8f0"}`,
                        borderRadius: "8px",
                        cursor: "pointer",
                        background: selectedBatchId === req.batchId ? "#eff6ff" : "#fff",
                      }}
                    >
                      <div style={{ fontWeight: 700, color: "#1e293b" }}>
                        Batch #{req.batchId}
                      </div>
                      <div style={{ fontSize: "0.82rem", color: "#64748b", marginTop: "4px" }}>
                        {req.parentCompanyName || "지주사 요청"} · {req.reportingYear || "-"}
                      </div>
                      <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "4px" }}>
                        {purposeLabel(req.rollupPurposeCode)} · {req.metricScopeCode || "-"}
                      </div>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                        <span className="ob1-status-pill">{readinessLabel(req.readinessStatus)}</span>
                        <span className="ob1-status-pill">{transferLabel(req.transferStatus)}</span>
                        <span className="ob1-status-pill">승인 Atomic {approved} / {required}</span>
                        {missing > 0 && <span className="ob1-status-pill not-started">누락 {missing}</span>}
                      </div>
                    </button>
                  );
                })}
              </div>

              <div style={{ border: "1px solid #e2e8f0", borderRadius: "10px", padding: "16px", minHeight: "420px" }}>
                {!selectedBatchId ? (
                  <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
                    왼쪽에서 요청을 선택하세요.
                  </div>
                ) : loadingDetail && !activeDetail ? (
                  <div className="ob1-table-loading" style={{ padding: "24px" }}>
                    <div className="ob1-spinner" />
                    <p>요청 상세를 불러오고 있습니다.</p>
                  </div>
                ) : (
                  <>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "8px" }}>
                      {[
                        ["Batch", activeRequest.batchId || selectedBatchId],
                        ["보고연도", activeRequest.reportingYear || "-"],
                        ["요청 Metric", activeRequest.requestedMetricCount ?? activeRequest.metricCount ?? "-"],
                        ["해결 Metric", activeRequest.resolvedMetricCount ?? "-"],
                        ["승인 Atomic", activeRequest.currentApprovedAtomicCount ?? activeRequest.approvedAtomicCount ?? 0],
                        ["누락 Atomic", currentMissingAtomicCount],
                        ["준비", readinessLabel(activeRequest.readinessStatus)],
                        ["전송", transferLabel(activeRequest.transferStatus)],
                      ].map(([label, value]) => (
                        <div key={label} style={{ padding: "10px", background: "#f8fafc", borderRadius: "8px" }}>
                          <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: "3px" }}>{label}</div>
                          <div style={{ fontWeight: 700, color: "#0f172a" }}>{value}</div>
                        </div>
                      ))}
                    </div>

                    <div style={{ marginTop: "12px", fontSize: "0.82rem", color: "#475569" }}>
                      승인 상태: {approvalLabel(activeRequest.approvalStatus)} · 범위: {activeRequest.metricScopeCode || "-"}
                    </div>

                    <MetricReadinessList
                      title="직접 요청 Metric"
                      items={activeDetail?.items || []}
                    />
                    <MetricReadinessList
                      title="계산 의존 Metric"
                      description="Rollup 계산에 필요한 의존 입력입니다."
                      items={activeDetail?.dependencyItems || []}
                    />

                    <div style={{ marginTop: "14px", padding: "12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#f8fafc" }}>
                      <strong>입력 Workspace</strong>
                      <div style={{ fontSize: "0.82rem", color: "#475569", marginTop: "6px" }}>
                        {inputWorkspace.availableYn
                          ? `이동 가능: Cycle #${inputWorkspace.cycleId || "-"} · ${inputWorkspace.cycleType || "-"} · ${inputWorkspace.reportingYear || "-"}`
                          : `준비 필요: ${inputWorkspace.reason || "INPUT_WORKSPACE_NOT_READY"}`}
                      </div>
                      {actionableInputMetricIds.length > 0 && (
                        <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "4px" }}>
                          보완 대상: {actionableInputMetricIds.join(", ")}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
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
            닫기
          </button>

          {currentMissingAtomicCount > 0 && inputWorkspace.availableYn === true && (
            <button
              style={{
                padding: "8px 16px",
                border: "1px solid #16a34a",
                background: "#fff",
                color: "#15803d",
                borderRadius: "4px",
                cursor: "pointer",
              }}
              onClick={handleNavigateInput}
            >
              입력 보완하기
            </button>
          )}

          {currentMissingAtomicCount > 0 && inputWorkspace.availableYn !== true && selectedBatchId && (
            <button
              style={{
                padding: "8px 16px",
                border: "none",
                background: "#94a3b8",
                color: "#fff",
                borderRadius: "4px",
                cursor: "not-allowed",
                opacity: 0.7,
              }}
              disabled
              title={inputWorkspace.reason || "INPUT_WORKSPACE_NOT_READY"}
            >
              입력 workspace 준비 필요
            </button>
          )}

          {currentMissingAtomicCount === 0 && !sendReadyYn && !isTransferred && selectedBatchId && (
            <button
              style={{
                padding: "8px 16px",
                border: "none",
                background: "#94a3b8",
                color: "#fff",
                borderRadius: "4px",
                cursor: "not-allowed",
                opacity: 0.7,
              }}
              disabled
              title="승인 완료 후 전송할 수 있습니다."
            >
              승인 완료 대기
            </button>
          )}

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
            {isTransferred ? "전송 완료" : sending || sendingSource ? "전송 중..." : "지주사에 전송하기"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default SubsidiaryTransferModal;
