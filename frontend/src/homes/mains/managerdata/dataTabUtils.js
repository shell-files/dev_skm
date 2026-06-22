/**
 * dataTabUtils.js
 * DataTab 컴포넌트 전용 상수 및 표시 헬퍼.
 * DataTab.jsx에서 import하여 사용.
 *
 * exports:
 *   PAGE_SIZE               — 테이블 페이지당 행 수
 *   DOMAIN_ORDER            — 이슈 도메인 정렬 순서
 *   DOMAIN_LABEL            — 이슈 도메인 표시 레이블 (E/S/G/General)
 *   safeArray               — null/undefined 방어용 배열 보장
 *   normalizeIssueDomain    — 다양한 필드명으로부터 issueDomain 추출
 *   normalizeSubIssueCode   — 다양한 필드명으로부터 subIssueCode 추출
 *   normalizeSubIssueName   — 다양한 필드명으로부터 subIssueName 추출, 없으면 code 사용
 *   normalizeApprovalStatus — approvalStatus 정규화 (대문자 + trim)
 *   normalizeSubmitStatus   — submitStatus 정규화 (SUBMITTED / DRAFT)
 *   normalizeReviewStatus   — reviewStatus 정규화 (REVIEWED / PENDING)
 *   isActionSupported       — 승인 액션 버튼 활성화 여부 판단
 *   actionDisabledTitle     — 비활성화 사유 툴팁 문자열 반환
 *   submitLabel             — 제출 상태 한글 레이블
 *   reviewLabel             — 검토 상태 한글 레이블
 *   approvalLabel           — 승인 상태 한글 레이블
 */

/** 테이블 페이지당 행 수 */
export const PAGE_SIZE = 10;

/** 이슈 도메인 정렬 순서 — 탭/행 렌더링 시 이 순서로 표시 */
export const DOMAIN_ORDER = ["general", "environmental", "social", "governance"];

/** 이슈 도메인 코드 → 탭 레이블 (ESG 약자 포함) */
export const DOMAIN_LABEL = {
  general: "General",
  environmental: "E",
  social: "S",
  governance: "G",
};

/** null/undefined/비배열 값을 빈 배열로 보장 */
export const safeArray = (value) => (Array.isArray(value) ? value : []);

/** item의 다양한 domain 필드명을 통일된 issueDomain 문자열로 추출 */
export const normalizeIssueDomain = (item = {}) =>
  String(item.issueDomain ?? item.issue_domain ?? item.domain ?? "general").trim();

/** item의 다양한 subIssueCode 필드명을 통일된 문자열로 추출 */
export const normalizeSubIssueCode = (item = {}) => {
  const value =
    item.subIssueCode ??
    item.sub_issue_code ??
    item.sourceSubIssueCode ??
    item.source_sub_issue_code;
  return value ? String(value).trim() : "";
};

/** item의 다양한 subIssueName 필드명 추출, 없으면 subIssueCode로 대체 */
export const normalizeSubIssueName = (item = {}) => {
  const value =
    item.subIssueName ??
    item.sub_issue_name ??
    item.displaySubIssueName;
  return value ? String(value).trim() : normalizeSubIssueCode(item);
};

/** approvalStatus 값을 대문자 trim 문자열로 정규화, 없으면 "NOT_STARTED" */
export const normalizeApprovalStatus = (item = {}) =>
  String(item.approvalStatus ?? item.status ?? "NOT_STARTED")
    .trim()
    .toUpperCase();

/** submitStatus 정규화 — 제출/검토/승인/반려 상태면 "SUBMITTED", 아니면 "DRAFT" */
export const normalizeSubmitStatus = (item = {}) => {
  if (item.submitStatus) return String(item.submitStatus).toUpperCase();
  const status = normalizeApprovalStatus(item);
  return ["SUBMITTED", "REVIEWED", "APPROVED", "REJECTED"].includes(status)
    ? "SUBMITTED"
    : "DRAFT";
};

/** reviewStatus 정규화 — 승인/반려 상태면 "REVIEWED", 아니면 "PENDING" */
export const normalizeReviewStatus = (item = {}) => {
  if (item.reviewStatus) return String(item.reviewStatus).toUpperCase();
  const status = normalizeApprovalStatus(item);
  return ["APPROVED", "REJECTED"].includes(status) ? "REVIEWED" : "PENDING";
};

/** 액션 버튼 활성화 여부 — readOnly이거나 actionSupportedYn=false이면 비활성 */
export const isActionSupported = (item = {}, readOnlyYn = false) =>
  !readOnlyYn && item.actionSupportedYn !== false;

/** 액션 비활성화 사유 툴팁 문자열 반환 */
export const actionDisabledTitle = (item = {}, readOnlyYn = false) =>
  readOnlyYn
    ? "Completed projects are read-only."
    : item.actionDisabledReason ||
      "This item does not support approval actions in the current step.";

/** 제출 상태 코드 → 한글 레이블 */
export const submitLabel = (status) => (status === "SUBMITTED" ? "제출 완료" : "작성 중");

/** 검토 상태 코드 → 한글 레이블 */
export const reviewLabel = (status) => (status === "REVIEWED" ? "검토 완료" : "대기");

/** 승인 상태 코드 → 한글 레이블 */
export const approvalLabel = (status) => {
  if (status === "APPROVED") return "승인";
  if (status === "REJECTED") return "반려";
  return "대기";
};
