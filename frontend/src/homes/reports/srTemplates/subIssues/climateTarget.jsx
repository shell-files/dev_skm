/**
 * climateTarget.jsx
 * 레이어: Component (srTemplates/subIssues)
 * 역할: 기후목표·전환계획 서브이슈의 SR 페이지 컴포넌트, adapter, metricFields, 서브이슈 매니페스트를 하나의 파일로 통합한 모듈
 *
 * exports:
 *   climateTarget (default) — id·label·adapter·metricFields·pages를 포함하는 서브이슈 매니페스트 객체
 */
// srTemplates/subIssues/climateTarget.jsx
// 기후목표·전환계획 서브이슈 단일 파일
// (통합: index.js + adapter.js + metricFields.js + pages/ClimateTargetPageA.jsx)
import React from "react";
import { SRChrome, MetricBar } from "../core/SRChrome";
import {
  Narrative, mt, num, reductionFromBase, NARRATIVE_TEMPLATE_CLIMATE,
} from "../core/srHelpers";

// ── 웹 편집 대상 지표 필드 ─────────────────────────────────────
const metricFields = [
  { id: "E1-05__QL0001", label: "탄소중립 전략 개요" },
  { id: "E1-05__QL0002", label: "기준연도" },
  { id: "E1-05__G0003", label: "기준연도 Scope1·2 배출량" },
  { id: "E1-05__QL0004", label: "전환계획 주요 이행수단" },
  { id: "E1-05__QL0005", label: "추가 맥락·전환 전략 설명" },
  { id: "E1-06__G0003", label: "보고연도 Scope1·2 배출량" },
  { id: "E1-06__G0004", label: "전년 대비 감축량" },
  { id: "E1-06__G0005", label: "감축률" },
  { id: "E1-07__G0003", label: "재생에너지 전환율" },
  { id: "E1-08__G0001", label: "탄소중립 목표연도" },
  { id: "E1-08__G0002", label: "재생E 100% 목표연도" },
  { id: "E1-08__QL0001", label: "탄소중립 범위" },
  { id: "E1-08__QL0002", label: "재생E 목표수준" },
  { id: "E1-05__G0001", label: "기준 Scope 1 (선택)" },
  { id: "E1-05__G0002", label: "기준 Scope 2 (선택)" },
  { id: "E1-06__G0001", label: "보고 Scope 1 (선택)" },
  { id: "E1-06__G0002", label: "보고 Scope 2 (선택)" },
];

// ── Adapter: metric rows → MetricsMap ─────────────────────────
// 원칙: 하드코딩 더미 수치 금지 / 값 누락 시 "—" / status 보존
function buildDisplayValue(row) {
  if (row.displayValue != null && String(row.displayValue).trim() !== "") {
    return row.displayValue;
  }
  if (row.valueNumeric != null && !Number.isNaN(Number(row.valueNumeric))) {
    const n = Number(row.valueNumeric).toLocaleString("en-US");
    return row.unit ? `${n} ${row.unit}` : n;
  }
  if (row.valueText != null && String(row.valueText).trim() !== "") {
    return String(row.valueText);
  }
  return "—";
}

function pickValue(row) {
  if (typeof row.valueNumeric === "number") return row.valueNumeric;
  if (typeof row.value === "number") return row.value;
  if (row.valueNumeric != null) {
    const n = parseFloat(String(row.valueNumeric).replace(/[^0-9.\-]/g, ""));
    if (!Number.isNaN(n)) return n;
  }
  return row.value ?? null;
}

function toClimateTargetMetrics(metricRows = []) {
  const map = {};
  if (!Array.isArray(metricRows)) return map;
  for (const row of metricRows) {
    if (!row) continue;
    const id =
      row.metricId ??
      row.metric_id ??
      row.atomicMetricId ??
      row.atomic_metric_id;
    if (!id) continue;
    map[id] = {
      value: pickValue(row),
      displayValue: buildDisplayValue(row),
      unit: row.unit,
      sourceType: row.sourceType ?? row.source_type,
      status: row.status,
      label: row.label,
    };
  }
  return map;
}

// ── 페이지 컴포넌트 ────────────────────────────────────────────
function ClimateTargetPageA(props) {
  
  const {
    metrics, narrativeText, mode = "render", highlight = true,
    template = NARRATIVE_TEMPLATE_CLIMATE,
    aiMetricIds = [],
  } = props;

  const baseV = num(metrics, "E1-05__G0003");
  const repV = num(metrics, "E1-06__G0003");
  const maxVal = Math.max(baseV || 0, repV || 0) || 1;
  const cutFromBase = reductionFromBase(metrics, "E1-05__G0003", "E1-06__G0003");
  const MAXH = 150;
  
  return (
    <SRChrome {...props}>
      <Narrative 
      narrativeText={narrativeText} 
      template={template} 
      metrics={metrics}
      mode={mode} 
      metricIds={aiMetricIds} 
      onNarrativeChange={props.onNarrativeChange} />

      {/* KPI strip */}
      <div className="sr-kpis">
        <div className="sr-kpi">
          <div className="kl">보고연도 연결 Scope 1·2</div>
          <div className="kv" data-source="E1-06__G0003">{mt(metrics, "E1-06__G0003", mode)}</div>
          <div className="kd down" data-source="E1-05__G0003,E1-06__G0003">
            기준연도 대비 {cutFromBase != null ? cutFromBase.toFixed(2) + "%" : "—"}
          </div>
        </div>
        <div className="sr-kpi">
          <div className="kl">전년 대비 감축량</div>
          <div className="kv" data-source="E1-06__G0004">{mt(metrics, "E1-06__G0004", mode)}</div>
          <div className="kd down" data-source="E1-06__G0005">감축률 {mt(metrics, "E1-06__G0005", mode)}</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">재생에너지 전환율</div>
          <div className="kv" data-source="E1-07__G0003">{mt(metrics, "E1-07__G0003", mode)}</div>
          <div className="kd up" data-source="E1-08__G0002">{mt(metrics, "E1-08__G0002", mode)} 100% 목표</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">탄소중립 목표</div>
          <div className="kv" data-source="E1-08__G0001">{mt(metrics, "E1-08__G0001", mode)}</div>
          <div className="kd flat" data-source="E1-05__QL0002">기준연도 {mt(metrics, "E1-05__QL0002", mode)}</div>
        </div>
      </div>

      {/* 탄소중립 로드맵 */}
      <div className="sr-road">
        <div className="sr-road-h">
          <div className="t">탄소중립 로드맵</div>
          <div className="d">연결 기준 Scope 1·2 배출량 추이 및 목표 경로</div>
          <div className="lg">
            <span><i style={{ background: "var(--s1)" }} />Scope 1</span>
            <span><i style={{ background: "var(--s2)" }} />Scope 2</span>
            <span><i style={{ background: "#e4f0ea", border: "1px dashed var(--brand2)" }} />목표 경로</span>
          </div>
        </div>
        <div className="sr-chart">
          <div className="sr-col">
            <div className="sr-barval" data-source="E1-05__G0003">{mt(metrics, "E1-05__G0003", mode)}</div>
            <MetricBar metrics={metrics} totalId="E1-05__G0003" s1Id="E1-05__G0001" s2Id="E1-05__G0002" maxVal={maxVal} maxH={MAXH} />
          </div>
          <div className="sr-col">
            <div className="sr-phase"><div className="pl">PHASE</div><div className="pn">1</div></div>
            <div className="sr-barval" style={{ color: "var(--brand)" }} data-source="E1-06__G0003">{mt(metrics, "E1-06__G0003", mode)}</div>
            <MetricBar metrics={metrics} totalId="E1-06__G0003" s1Id="E1-06__G0001" s2Id="E1-06__G0002" maxVal={maxVal} maxH={MAXH} />
          </div>
          <div className="sr-col">
            <div className="sr-phase"><div className="pl">PHASE</div><div className="pn">2</div></div>
            <div className="sr-mile" style={{ top: 28 }} data-source="E1-08__G0002">재생에너지<br />100% 전환</div>
            <div className="sr-bar target" style={{ height: 56 }} />
          </div>
          <div className="sr-col">
            <div className="sr-mile" style={{ top: 78 }} data-source="E1-08__G0001">Net-Zero<br /><span style={{ fontSize: 11 }}>100% 감축</span></div>
            <div className="sr-barval" style={{ color: "var(--brand)" }}>0 <small>(흡수·상쇄)</small></div>
            <div className="sr-bar zero" />
          </div>
        </div>
        <div className="sr-xrow">
          <div className="sr-xc"><div className="yr" data-source="E1-05__QL0002">{mt(metrics, "E1-05__QL0002", mode)}</div><div className="ph">기준연도 <b>Base</b></div></div>
          <div className="sr-xc"><div className="yr">보고연도</div><div className="ph"><b>Reporting</b> · 현재</div></div>
          <div className="sr-xc"><div className="yr" data-source="E1-08__G0002">{mt(metrics, "E1-08__G0002", mode)}</div><div className="ph">중간 목표</div></div>
          <div className="sr-xc"><div className="yr" data-source="E1-08__G0001">{mt(metrics, "E1-08__G0001", mode)}</div><div className="ph"><b>탄소중립</b></div></div>
        </div>
      </div>

      {/* 전환계획 주요 이행수단 */}
      <div className="sr-measures" data-source="E1-05__QL0004">
        <span className="ml">전환계획 주요 이행수단</span>
        <span className="mv">{mt(metrics, "E1-05__QL0004", mode)}</span>
      </div>
    </SRChrome>
  );
}

// ── 서브이슈 매니페스트 ────────────────────────────────────────
const climateTarget = {
  id: "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  label: "기후목표·전환계획",
  subLabel: "기후변화 대응",
  exportName: "climate-target",
  adapter: toClimateTargetMetrics,
  metricFields,
  pages: [
    {
      key: "climate-a",
      tabLabel: "기후변화 대응",
      tocTag: "E1",
      Component: ClimateTargetPageA,
      props: {
        pageTitle: "기후목표·전환계획",
        pageTitleEn: "Climate Target & Transition Plan",
        sourceNote: "SKM SR Template v1.0 · Auto-generated",
        subNavItems: [
          { label: "기후변화 대응", active: true },
          { label: "공급망 감사" },
          { label: "교육훈련" },
          { label: "친환경 제품" },
          { label: "제품안전" },
        ],
      },
    },
  ],
};

export default climateTarget;
