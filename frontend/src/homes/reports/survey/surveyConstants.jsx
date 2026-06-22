/**
 * surveyConstants.jsx
 * 이해관계자 설문 페이지 공통 상수 및 표시 헬퍼.
 * Survey.jsx · SurveyResultDashboard.jsx에서 공유.
 *
 * exports:
 *   GROUP_META       — 그룹별 표시 레이블/색상/아이콘
 *   GROUP_KEYS       — 그룹 키 순서 배열
 *   GROUP_SCORE_KEY  — 그룹별 Redux 점수 필드명 매핑
 *   URL_LABEL        — 그룹별 설문 URL 표시 레이블 생성 함수
 *   pctFromRate      — responseRate(0~1) → 0~100 변환
 *   displayRate      — 목표 미설정 처리 포함 응답률 문자열 반환
 *   rateBarWidth     — 프로그레스 바 너비(%) 계산
 *   fmtScore         — 점수 소수 2자리 포맷 (null이면 "-")
 */

/** 그룹(임직원/경영진/외부) 표시 레이블, 색상, 배경색, SVG 아이콘 */
export const GROUP_META = {
  employee: {
    label: "임직원",
    color: "#03A94D",
    bg: "#e8f8ef",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  management: {
    label: "경영진",
    color: "#3b82f6",
    bg: "#eff6ff",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  external: {
    label: "외부이해관계자",
    color: "#f97316",
    bg: "#fff7ed",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
};

/** 그룹 키 순서 — map/forEach 시 순서 보장용 */
export const GROUP_KEYS = ["employee", "management", "external"];

/** 그룹별 Redux state 점수 필드명 — stakeholderTopIssues 정렬 기준 */
export const GROUP_SCORE_KEY = {
  employee:   "employeeImpactScore05",
  management: "managementImpactScore05",
  external:   "externalImpactScore05",
};

/** 그룹별 설문 폼 URL 표시 레이블 생성 (연도 파라미터 포함) */
export const URL_LABEL = {
  employee:   (year) => `임직원 ESG ${year} 설문조사`,
  management: (year) => `경영진 ESG ${year} 설문조사`,
  external:   (year) => `외부이해관계자 용 ESG ${year} 설문조사`,
};

/** responseRate(0~1) → 0~100 (소수 1자리 반올림) */
export const pctFromRate = (rate) => Math.round((rate ?? 0) * 1000) / 10;

/** 목표 인원 0이면 "목표 미설정" 반환, 아니면 백분율 문자열 */
export const displayRate = (rate, targetCount) =>
  targetCount > 0 ? `${pctFromRate(rate).toFixed(1)}%` : "목표 미설정";

/** 프로그레스 바 너비(%) — 목표 미설정 시 0 */
export const rateBarWidth = (rate, targetCount) =>
  targetCount > 0 ? Math.min(100, pctFromRate(rate)) : 0;

/** 숫자이면 toFixed(2), null/undefined이면 "-" */
export const fmtScore = (v) =>
  v != null && Number.isFinite(Number(v)) ? Number(v).toFixed(2) : "-";
