// ============================================================
// types.js — JSDoc 타입 정의 (순수 JS. 에디터 자동완성용, 런타임 영향 없음)
// ============================================================

/**
 * 단일 metric 값. 화면 렌더는 항상 displayValue 기준, 계산은 value 기준.
 * @typedef {Object} MetricValue
 * @property {number|string|null} value        원천 값(숫자/문자). 차트 스케일·계산용
 * @property {string} displayValue             표시값 ("112,500 tCO2eq")
 * @property {string} [unit]                   "tCO2eq" | "%" | "년"
 * @property {"QL"|"QN"|"DERIVED"|"REFERENCE"} [sourceType]
 * @property {"DRAFT"|"PENDING"|"APPROVED"|"REJECTED"|"MISSING"} [status]
 * @property {string} [label]
 * @property {string} [atomicMetricId]
 */

/**
 * metric_id → MetricValue 맵
 * @typedef {Object.<string, MetricValue>} MetricsMap
 */

/**
 * @typedef {Object} NavItem
 * @property {string} key
 * @property {string} label
 * @property {boolean} [active]
 */

/**
 * @typedef {Object} ClimatePageProps
 * @property {MetricsMap} metrics                필수
 * @property {string} [narrativeText]            있으면 우선, 없으면 buildNarrative
 * @property {string} [template]                 기본 NARRATIVE_TEMPLATE_CLIMATE
 * @property {"render"|"placeholder"} [mode]
 * @property {boolean} [highlight]               본문 수치 강조(기본 true)
 * @property {NavItem[]} [navItems]
 * @property {{label:string,active?:boolean}[]} [subNavItems]
 * @property {string} [sectionLabel]
 * @property {string} [ghost]
 * @property {string} pageTitle
 * @property {string} [pageTitleEn]
 * @property {number|string} [pageNumber]
 * @property {string[]} [footnotes]
 * @property {string} [sourceNote]
 * @property {string} [tag]
 */

export {};
