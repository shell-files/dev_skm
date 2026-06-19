/**
 * RollupInboxPanel.jsx
 * 레이어: Component (onboards)
 * 역할: ROLLUP_RESPONSE 모드에서 자회사가 수신한 지주사 데이터 요청 목록(받은 요청함)을 테이블로 표시하고 상세 진입을 지원하는 패널
 *
 * Props:
 *   requests — 수신된 롤업 요청 배열 (batchId, parentCompanyName, transferStatus 등 포함)
 *   onRefresh — 목록 새로고침 핸들러
 */
import React from "react";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { setCurruntYear } from "@stores/reportSlice";

const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "중대성 평가 사전 입력";
  return value || "-";
};

const RollupInboxPanel = ({ requests = [], onRefresh }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  // const handleDetail = (req) => {
  //   navigate(`?mode=ROLLUP_RESPONSE&batchId=${req.batchId}&reportingYear=${req.reportingYear}`);
  // };

  const handleDetail = (req) => {
    dispatch(setCurruntYear(req.reportingYear));
    navigate(`?mode=ROLLUP_RESPONSE&batchId=${req.batchId}`);
  };
  return (
    <div style={{ padding: "20px", background: "#fff", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: "600", color: "#1e293b", margin: 0 }}>받은 요청함</h2>
        {onRefresh && (
          <button 
            onClick={onRefresh}
            style={{ padding: "6px 12px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "6px", cursor: "pointer", fontSize: "0.85rem", color: "#475569", display: "flex", alignItems: "center", gap: "6px" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            새로고침
          </button>
        )}
      </div>
      <p style={{ marginBottom: "20px", color: "#64748b", fontSize: "0.9rem" }}>
        지주사에서 연결 공시 또는 중대성 평가를 위해 요청한 데이터 목록입니다.
      </p>

      {requests.length === 0 ? (
        <div style={{ padding: "40px 0", textAlign: "center", color: "#94a3b8", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1" }}>
          도착한 요청이 없습니다.
        </div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ background: "#f1f5f9", borderBottom: "1px solid #e2e8f0" }}>
              <th style={{ padding: "12px", textAlign: "left", color: "#475569", fontWeight: "600" }}>요청 기업</th>
              <th style={{ padding: "12px", textAlign: "center", color: "#475569", fontWeight: "600" }}>보고연도</th>
              <th style={{ padding: "12px", textAlign: "left", color: "#475569", fontWeight: "600" }}>요청 유형</th>
              <th style={{ padding: "12px", textAlign: "center", color: "#475569", fontWeight: "600" }}>요청 지표</th>
              <th style={{ padding: "12px", textAlign: "center", color: "#475569", fontWeight: "600" }}>승인 현황</th>
              <th style={{ padding: "12px", textAlign: "center", color: "#475569", fontWeight: "600" }}>전송 상태</th>
              <th style={{ padding: "12px", textAlign: "center", color: "#475569", fontWeight: "600" }}>관리</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((req) => {
              const transferStatusStr = (req.transferStatus || "").toLowerCase();
              const isSent = transferStatusStr === "sent" || transferStatusStr === "received";
              const isReady = req.sendReadyYn;
              
              let transferStatusText = "미전송";
              let transferStatusColor = "#64748b";
              
              if (isSent) {
                transferStatusText = "전송 완료";
                transferStatusColor = "#059669";
              } else if (isReady) {
                transferStatusText = "전송 대기";
                transferStatusColor = "#ea580c";
              }

              return (
                <tr key={req.batchId} style={{ borderBottom: "1px solid #e2e8f0", transition: "background 0.2s" }} onMouseOver={e => e.currentTarget.style.background = "#f8fafc"} onMouseOut={e => e.currentTarget.style.background = "transparent"}>
                  <td style={{ padding: "12px", color: "#1e293b", fontWeight: "500" }}>{req.parentCompanyName || req.parentCompanyId}</td>
                  <td style={{ padding: "12px", textAlign: "center", color: "#1e293b" }}>{req.reportingYear}</td>
                  <td style={{ padding: "12px", color: "#1e293b" }}>{purposeLabel(req.rollupPurposeCode)}</td>
                  <td style={{ padding: "12px", textAlign: "center", color: "#1e293b" }}>{req.requestedMetricCount || 0}</td>
                  <td style={{ padding: "12px", textAlign: "center", color: "#1e293b" }}>
                    <span style={{ color: req.currentApprovedAtomicCount === req.requiredAtomicCount && req.requiredAtomicCount > 0 ? "#059669" : "#ea580c", fontWeight: "600" }}>
                      {req.currentApprovedAtomicCount || 0}
                    </span>
                    {" / "}
                    {req.requiredAtomicCount || 0}
                  </td>
                  <td style={{ padding: "12px", textAlign: "center", color: transferStatusColor, fontWeight: "500" }}>
                    {transferStatusText}
                  </td>
                  <td style={{ padding: "12px", textAlign: "center" }}>
                    <button 
                      onClick={() => handleDetail(req)}
                      style={{
                        padding: "6px 12px",
                        background: "#ffffff",
                        border: "1px solid #cbd5e1",
                        borderRadius: "4px",
                        color: "#334155",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                        transition: "all 0.2s"
                      }}
                      onMouseOver={e => { e.currentTarget.style.background = "#f1f5f9"; e.currentTarget.style.borderColor = "#94a3b8"; }}
                      onMouseOut={e => { e.currentTarget.style.background = "#ffffff"; e.currentTarget.style.borderColor = "#cbd5e1"; }}
                    >
                      상세 보기
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RollupInboxPanel;
