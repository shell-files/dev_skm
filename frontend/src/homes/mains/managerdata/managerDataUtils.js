/**
 * managerDataUtils.js
 * ManagerData 페이지 전용 상수 및 표시 헬퍼.
 * ManagerData.jsx에서 import하여 사용.
 *
 * exports:
 *   PAGE_SIZE                      — 테이블 페이지당 행 수
 *   SUPPORTED_APPROVAL_CYCLE_TYPES — 이 페이지에서 처리 가능한 승인 사이클 타입 목록
 *   safeArray                      — null/undefined 방어용 배열 보장
 *   normalizeStatus                — approvalStatus 문자열 정규화 (대문자 + trim)
 *   mapApprovalItemToInput         — API 승인 아이템 → 테이블 행 데이터로 변환
 *   basisLabel                     — 연결/독립 기준 레이블 반환
 *   runStatusLabel                 — 프로젝트 진행 상태 한글 레이블 반환
 *   formatStageLabel               — 워크플로우 단계명 한글 레이블로 변환
 */

/** 테이블 페이지당 행 수 */
export const PAGE_SIZE = 10;

/** 이 페이지에서 처리하는 승인 사이클 타입 — 이외 타입은 필터링됨 */
export const SUPPORTED_APPROVAL_CYCLE_TYPES = [
  "PRE_DMA_G0",
  "POST_DMA_DISCLOSURE",
  "ROLLUP_RESPONSE",
];

/** null/undefined/비배열 값을 빈 배열로 보장 */
export const safeArray = (value) => (Array.isArray(value) ? value : []);

/** approvalStatus 값을 대문자 trim 문자열로 정규화, 없으면 "NOT_STARTED" */
export const normalizeStatus = (value) =>
  String(value || "NOT_STARTED").trim().toUpperCase();

/** API 승인 아이템 DTO → 테이블 행 표시용 데이터로 변환 */
export const mapApprovalItemToInput = (item = {}) => {
  const approvalStatus = normalizeStatus(item.approvalStatus);
  const missingAtomicIds = safeArray(item.missingAtomicMetricIds);
  const completedCount = Number(item.completedAtomicCount || 0);
  const requiredCount = Number(item.requiredAtomicCount || 0);
  const missingCount =
    missingAtomicIds.length || Math.max(requiredCount - completedCount, 0);

  return {
    ...item,
    id: item.metricId,
    metricId: item.metricId,
    metricName: item.metricName || item.metricId,
    service: item.service || "disclosure",
    issueDomain: item.issueDomain || "general",
    issueGroup: item.issueGroup || null,
    subIssueId: item.subIssueId ?? null,
    subIssueCode: item.subIssueCode || null,
    subIssueName: item.subIssueName || null,
    status: approvalStatus,
    approvalStatus,
    submitStatus: ["SUBMITTED", "REVIEWED", "APPROVED", "REJECTED"].includes(
      approvalStatus
    )
      ? "SUBMITTED"
      : "DRAFT",
    reviewStatus: [
      "REVIEWED",
      "APPROVED",
      "REJECTED",
    ].includes(approvalStatus)
      ? "REVIEWED"
      : "PENDING",
    inputCompletedCount: completedCount,
    inputMissingCount: missingCount,
    assigneeName:
      item.assigneeName ||
      item.assigneeEmailMasked ||
      (item.assigneeUserId ? `user#${item.assigneeUserId}` : "-"),
    userName:
      item.assigneeName ||
      item.assigneeEmailMasked ||
      (item.assigneeUserId ? `user#${item.assigneeUserId}` : "-"),
    actionSupportedYn: item.actionSupportedYn,
    actionDisabledReason: item.actionDisabledReason,
  };
};

/** 연결/독립 기준 코드 → 한글 레이블 */
export const basisLabel = (basisType) => {
  if (basisType === "CONSOLIDATED") return "연결 기준";
  if (basisType === "ENTITY") return "독립 기준";
  return "기준 미선택";
};

/** 프로젝트 진행 상태 코드 → 한글 레이블 */
export const runStatusLabel = (runStatus) => {
  const status = String(runStatus || "ACTIVE").toUpperCase();
  if (status === "COMPLETED") return "완료";
  if (status === "ARCHIVED") return "보관됨";
  return "진행 중";
};

/** 워크플로우 단계 레이블 문자열 → 사용자 표시용 한글 레이블로 변환 */
export const formatStageLabel = (label) => {
  if (!label) return "-";
  const lower = String(label).toLowerCase();
  if (lower.includes("g0") || lower.includes("pre_dma")) return "경영일반 입력";
  if (lower.includes("all approvals") || lower.includes("completed")) return "데이터 승인 완료";
  if (lower.includes("disclosure") || lower.includes("post_dma")) return "보고서 연결 공시 승인";
  return label;
};
