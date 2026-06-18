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
export const GROUP_KEYS = ["employee", "management", "external"];
export const GROUP_SCORE_KEY = {
  employee:   "employeeImpactScore05",
  management: "managementImpactScore05",
  external:   "externalImpactScore05",
};

// responseRate(0~1 fraction) → 0~100 (소수 1자리)
export const pctFromRate = (rate) => Math.round((rate ?? 0) * 1000) / 10;
// 목표 인원이 0이면 백분율 대신 "목표 미설정" 표기
export const displayRate = (rate, targetCount) =>
  targetCount > 0 ? `${pctFromRate(rate).toFixed(1)}%` : "목표 미설정";
export const rateBarWidth = (rate, targetCount) =>
  targetCount > 0 ? Math.min(100, pctFromRate(rate)) : 0;
// 점수 포맷: 숫자면 toFixed(2), null/undefined면 "-"
export const fmtScore = (v) =>
  v != null && Number.isFinite(Number(v)) ? Number(v).toFixed(2) : "-";

export const URL_LABEL = {
  employee:   (year) => `임직원 ESG ${year} 설문조사`,
  management: (year) => `경영진 ESG ${year} 설문조사`,
  external:   (year) => `외부이해관계자 용 ESG ${year} 설문조사`,
};
