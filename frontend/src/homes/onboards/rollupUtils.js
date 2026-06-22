/**
 * rollupUtils.js
 * 레이어: Utils (onboards)
 * 역할: 롤업 상태·목적·전송·승인 코드를 한국어 레이블로 변환하는 순수 유틸리티
 */

export const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "이중중대성평가 사전 계산";
  return value || "-";
};

export const readinessLabel = (status) => {
  const value = String(status || "").toUpperCase();
  if (value === "READY") return "전송 가능";
  if (value === "PARTIAL") return "입력 진행중";
  if (value === "NOT_STARTED") return "미입력";
  return status || "-";
};

export const transferLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "received") return "수신 완료";
  if (value === "sent") return "전송 완료";
  if (value === "not_sent") return "미전송";
  return status || "-";
};

export const approvalLabel = (status) => {
  const value = String(status || "").toLowerCase();
  if (value === "approved") return "승인 완료";
  if (value === "reviewed") return "검토 완료";
  if (value === "rejected") return "반려";
  if (value === "pending" || value === "submitted") return "승인 대기";
  return status || "-";
};

export const numberOrZero = (value) => Number(value || 0);
