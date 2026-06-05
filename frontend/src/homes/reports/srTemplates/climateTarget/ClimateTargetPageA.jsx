// ============================================================
// ClimateTargetPageA.jsx — A안 (도형/시각화 버전)
// 모든 수치는 metrics 객체에서만 읽고, 각 요소에 data-source 부여
// ============================================================
import React from "react";
import { SRChrome, MetricBar } from "./SRChrome";
import { Narrative, mt, num, reductionFromBase, NARRATIVE_TEMPLATE_CLIMATE } from "./srHelpers";

export function ClimateTargetPageA(props) {
  const {
    metrics, narrativeText, mode = "render", highlight = true,
    template = NARRATIVE_TEMPLATE_CLIMATE,
  } = props;

  const baseV = num(metrics, "E1-05__G0003");
  const repV = num(metrics, "E1-06__G0003");
  const maxVal = Math.max(baseV || 0, repV || 0) || 1;
  const cutFromBase = reductionFromBase(metrics, "E1-05__G0003", "E1-06__G0003");
  const MAXH = 150;

  return (
    <SRChrome {...props}>
      <Narrative narrativeText={narrativeText} template={template} metrics={metrics} mode={mode} highlight={highlight} />

      {/* KPI strip — 타일마다 source metric 바인딩 */}
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

      {/* 탄소중립 로드맵 — 실측 막대는 metric에서 스케일, 미래 목표는 점선 경로 */}
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
            {/* 미래 목표 막대 = 데이터값이 아닌 목표 경로(점선) */}
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

      {/* 전환계획 주요 이행수단 — E1-05__QL0004 바인딩 */}
      <div className="sr-measures" data-source="E1-05__QL0004">
        <span className="ml">전환계획 주요 이행수단</span>
        <span className="mv">{mt(metrics, "E1-05__QL0004", mode)}</span>
      </div>
    </SRChrome>
  );
}
