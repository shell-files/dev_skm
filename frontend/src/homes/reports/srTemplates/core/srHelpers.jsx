// ============================================================
// srHelpers.jsx — metric 접근/포맷/narrative 조합 공통 유틸 (순수 JS)
// 의존성: react 만 사용 (차트 라이브러리 없음)
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

import React from "react";

/** KRW 단위 → 억 원 변환 (소수점 1자리, 불필요한 .0 제거) */
function krwToUk(n) {
  const uk = n / 100_000_000;
  return uk % 1 === 0
    ? uk.toLocaleString("ko-KR")
    : uk.toLocaleString("ko-KR", { maximumFractionDigits: 1 });
}

/**
 * 범용 adapter: metricRows(API) → MetricsMap
 * 모든 서브이슈 파일에서 import해서 adapter로 사용
 * - 단위가 KRW이면 1억 단위로 변환하여 표시 (unit → "억 원")
 */
export function buildMetricsMap(metricRows = []) {
  const map = {};
  if (!Array.isArray(metricRows)) return map;
  for (const row of metricRows) {
    if (!row) continue;
    const id = row.metricId ?? row.metric_id ?? row.atomicMetricId ?? row.atomic_metric_id;
    if (!id) continue;
    const isKrw = (row.unit ?? "").toUpperCase() === "KRW";
    let displayValue;
    if (row.displayValue != null && String(row.displayValue).trim() !== "") {
      displayValue = row.displayValue;
    } else if (row.valueNumeric != null && !Number.isNaN(Number(row.valueNumeric))) {
      const n = Number(row.valueNumeric);
      displayValue = isKrw
        ? `${krwToUk(n)} 억 원`
        : `${n.toLocaleString("en-US")}${row.unit ? ` ${row.unit}` : ""}`;
    } else if (row.valueText != null && String(row.valueText).trim() !== "") {
      displayValue = String(row.valueText);
    } else {
      displayValue = "—";
    }
    let value = null;
    if (typeof row.valueNumeric === "number") value = row.valueNumeric;
    else if (row.valueNumeric != null) {
      const n = parseFloat(String(row.valueNumeric).replace(/[^0-9.\-]/g, ""));
      value = Number.isNaN(n) ? null : n;
    } else {
      value = row.value ?? null;
    }
    map[id] = {
      value,
      displayValue,
      unit: isKrw ? "억 원" : row.unit,
      sourceType: row.sourceType ?? row.source_type,
      status: row.status,
      label: row.label,
    };
  }
  return map;
}

/** 기후목표·전환계획 기본 narrative 템플릿 (option B: 값으로 문장 조합) */
export const NARRATIVE_TEMPLATE_CLIMATE =
  "{E1-05__QL0001} 기준연도는 {E1-05__QL0002}이며 기준연도 연결 Scope 1·2 배출량은 {E1-05__G0003}이다. " +
  "{E1-05__QL0004} 보고연도 연결 Scope 1·2 배출량은 {E1-06__G0003}, 전년 대비 감축량은 {E1-06__G0004}, " +
  "감축률은 {E1-06__G0005}이다. 재생에너지 전환율은 {E1-07__G0003}이며, {E1-05__QL0005}";

/** displayValue 안전 접근 */
export const dv = (m, id) =>
  m && m[id] && m[id].displayValue != null ? m[id].displayValue : null;

/** metric 텍스트: render → displayValue, placeholder → {id} */
export const mt = (m, id, mode = "render") =>
  mode === "placeholder" ? `{${id}}` : (dv(m, id) ?? `{${id}}`);

/** 숫자 추출 (차트 스케일/계산용) */
export const num = (m, id) => {
  const v = m && m[id];
  if (!v) return null;
  if (typeof v.value === "number") return v.value;
  const n = parseFloat(String(v.value ?? "").replace(/[^0-9.\-]/g, ""));
  return isNaN(n) ? null : n;
};

export const fmtInt = (n) => (n == null ? "—" : n.toLocaleString("en-US"));

/** option B — 템플릿의 {id}를 metric displayValue로 치환 */
export function buildNarrative(template, metrics, mode = "render") {
  return template.replace(/\{([^}]+)\}/g, (_, id) =>
    mode === "placeholder" ? `{${id}}` : (dv(metrics, id) ?? `{${id}}`)
  );
}

/**
 * 본문 결정 규칙:
 *  - placeholder 모드: 항상 템플릿 토큰 노출
 *  - narrativeText(AI 완성문)이 있으면 우선
 *  - 없으면 buildNarrative로 조합
 */
export function resolveNarrative({ narrativeText, template, metrics, mode = "render" }) {
  if (mode === "placeholder") return buildNarrative(template, metrics, "placeholder");
  if (narrativeText && narrativeText.trim()) return narrativeText;
  return buildNarrative(template, metrics, "render");
}

/** 파생값: 기준연도 대비 감축률(%). 두 source metric에 추적 가능 */
export function reductionFromBase(metrics, baseId, curId) {
  const b = num(metrics, baseId);
  const c = num(metrics, curId);
  if (b == null || c == null || b === 0) return null;
  return ((b - c) / b) * 100;
}

/** AI 문단 안의 짧은 수치(displayValue)를 굵게 처리하고 data-source 부여 */
export function highlightFigures(text, metrics, ids) {
  const toks = ids
    .map((id) => ({ id, str: dv(metrics, id) }))
    .filter((t) => t.str && t.str.length <= 22)
    .sort((a, b) => b.str.length - a.str.length);
  let nodes = [text];
  let key = 0;
  toks.forEach(({ id, str }) => {
    const next = [];
    nodes.forEach((node) => {
      if (typeof node !== "string") { next.push(node); return; }
      node.split(str).forEach((p, i) => {
        if (i > 0) next.push(<b key={"h" + key++} data-source={id}>{str}</b>);
        if (p) next.push(p);
      });
    });
    nodes = next;
  });
  return nodes;
}

/** placeholder 토큰을 칩으로 렌더 (시안용) */
export function renderPlaceholder(text) {
  return text.split(/(\{[^}]+\})/g).map((p, i) => {
    const m = p.match(/^\{([^}]+)\}$/);
    return m ? (
      <code key={i} className="sr-token" data-source={m[1]}>{p}</code>
    ) : (
      <React.Fragment key={i}>{p}</React.Fragment>
    );
  });
}

/** 편집 모드: 템플릿의 {id} 토큰을 클릭 편집 가능한 span으로 (값 있으면 값, 없으면 {id}) */
export function renderEditableNarrative(template, metrics) {
  return template.split(/(\{[^}]+\})/g).map((p, i) => {
    const m = p.match(/^\{([^}]+)\}$/);
    if (!m) return <React.Fragment key={i}>{p}</React.Fragment>;
    const id = m[1];
    const val = dv(metrics, id);
    return (
      <span key={i} className={"sr-tok-edit" + (val == null ? " empty" : "")} data-source={id}>
        {val != null ? val : `{${id}}`}
      </span>
    );
  });
}

/** 본문에서 강조 대상으로 삼을 metric_id (짧은 수치류) */
export const CLIMATE_HIGHLIGHT_IDS = [
  "E1-05__QL0002", "E1-05__G0003", "E1-06__G0003", "E1-06__G0004",
  "E1-06__G0005", "E1-07__G0003", "E1-08__G0001", "E1-08__G0002",
];

/** 템플릿을 텍스트/토큰 노드로 분해 */
export function splitNarrative(template) {
  return (template || "")
    .split(/(\{[^}]+\})/g)
    .map((part) => {
      const m = part.match(/^\{([^}]+)\}$/);
      return m ? { token: true, id: m[1] } : { token: false, text: part };
    })
    .filter((n) => n.token || n.text);
}

/**
 * 정적 본문(보기/PDF):
 *  - {token} 형식이 있으면 토큰 기반 강조 렌더링
 *  - 없으면(AI 생성 텍스트) metricIds 를 이용해 highlightFigures 로 수치 강조
 */
export function NarrativeStatic({ template, metrics, metricIds = [] }) {
  const hasTokens = /\{[^}]+\}/.test(template || "");
  if (!hasTokens && metricIds.length > 0 && template) {
    const nodes = highlightFigures(template, metrics, metricIds);
    return <div className="sr-prose"><p>{nodes}</p></div>;
  }
  const nodes = splitNarrative(template);
  return (
    <div className="sr-prose">
      <p>
        {nodes.map((n, i) => {
          if (!n.token) return <React.Fragment key={i}>{n.text}</React.Fragment>;
          const val = dv(metrics, n.id);
          return (
            <span key={i} className={"sr-fig" + (val == null ? " empty" : "")} data-source={n.id}>
              {val != null ? val : `{${n.id}}`}
            </span>
          );
        })}
      </p>
    </div>
  );
}

/** 편집용 본문(contentEditable): 사이 문구는 자유 편집, 토큰은 강조 span(클릭해 값 수정).
 *  - 토큰 span 은 contentEditable=false 라 글자 편집 대상이 아니며, 클릭 시 값 팝업이 열림(Draft에서 처리)
 *  - blur 시 DOM을 다시 템플릿 문자열({id} 보존)로 직렬화해 저장 → 강조/데이터바인딩 유지 */
export function EditableNarrative({ template, metrics, onChange }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el || document.activeElement === el) return; // 편집 중엔 덮어쓰지 않음(커서 보존)
    el.innerHTML = "";
    splitNarrative(template).forEach((n) => {
      if (n.token) {
        const val = dv(metrics, n.id);
        const span = document.createElement("span");
        span.className = "sr-fig" + (val == null ? " empty" : "");
        span.setAttribute("data-source", n.id);
        span.setAttribute("contenteditable", "false");
        span.textContent = val != null ? val : `{${n.id}}`;
        el.appendChild(span);
      } else {
        el.appendChild(document.createTextNode(n.text));
      }
    });
  }, [template, metrics]);

  const serialize = () => {
    const el = ref.current;
    if (!el) return template;
    let out = "";
    el.childNodes.forEach((node) => {
      if (node.nodeType === 3) out += node.textContent;
      else if (node.getAttribute && node.getAttribute("data-source")) out += "{" + node.getAttribute("data-source") + "}";
      else out += node.textContent || "";
    });
    return out;
  };

  return (
    <div
      ref={ref}
      className="sr-prose sr-prose-edit"
      contentEditable
      suppressContentEditableWarning
      spellCheck={false}
      onBlur={() => onChange && onChange(serialize())}
    />
  );
}

/** 본문 렌더 컴포넌트 (A/B 공통) */
export function Narrative({
  narrativeText, template, metrics, mode = "render", onNarrativeChange, metricIds = [],
}) {
  // AI 생성 본문이 있으면 우선, 없으면 기본 템플릿({token} 방식)
  const tpl = (narrativeText && narrativeText.trim()) ? narrativeText : template;
  if (mode === "edit") {
    return <EditableNarrative template={tpl} metrics={metrics} onChange={onNarrativeChange} />;
  }
  return <NarrativeStatic template={tpl} metrics={metrics} metricIds={metricIds} />;
}