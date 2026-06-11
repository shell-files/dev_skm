// srTemplates/subIssues/supplyChain.jsx
// 공급망 감사·시정조치 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

const TEMPLATE =
  "{S6-01__QL0001} {S6-02__QL0001} 연결 기준 공급업체 감사 수행률은 {S6-04__G0003}, " +
  "고위험 공급업체 수는 {S6-04__G0004}이다. " +
  "공급망 CAP 완료율은 {S6-05__G0003}이며, {S6-05__QL0001}";

const metricFields = [
  { id: "S6-01__QL0001", label: "공급망 사회적 책임 정책" },
  { id: "S6-02__QL0001", label: "공급업체 리스크 평가 방법론" },
  { id: "S6-04__G0003", label: "공급업체 감사 수행률" },
  { id: "S6-04__G0004", label: "고위험 공급업체 수" },
  { id: "S6-05__G0003", label: "공급망 CAP 완료율" },
  { id: "S6-05__QL0001", label: "CAP 주요 시정조치 내용" },
];

function SupplyChainPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const capRate = num(metrics, "S6-05__G0003");
  const fillPct = capRate != null ? Math.min(Math.max(capRate, 0), 100) : 0;

  return (
    <SRChrome {...props}>
      {/* AI 생성 문단 — report_text 우선, 없으면 template 폴백 */}
      <Narrative
        narrativeText={narrativeText}
        template={TEMPLATE}
        metrics={metrics}
        mode={mode}
        metricIds={aiMetricIds}
        onNarrativeChange={props.onNarrativeChange}
      />

      {/* KPI strip */}
      <div className="sr-kpis">
        <div className="sr-kpi">
          <div className="kl">공급업체 감사 수행률</div>
          <div className="kv" data-source="S6-04__G0003">{mt(metrics, "S6-04__G0003", mode)}</div>
          <div className="kd flat">연결 기준</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">고위험 공급업체 수</div>
          <div className="kv" data-source="S6-04__G0004">{mt(metrics, "S6-04__G0004", mode)}</div>
          <div className="kd down">감사 결과 식별</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">CAP 완료율</div>
          <div className="kv" data-source="S6-05__G0003">{mt(metrics, "S6-05__G0003", mode)}</div>
          <div className="kd up">시정조치 이행</div>
        </div>
      </div>

      {/* 감사·CAP 상세 */}
      <div className="sr-cols" style={{ marginTop: 16 }}>
        <div className="c-main">
          <div className="sr-tcap">
            <span className="num">1</span>공급망 감사 및 시정조치 현황
          </div>
          <table className="sr-tbl">
            <thead>
              <tr>
                <th style={{ width: "52%" }}>지표</th>
                <th>보고연도</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>공급업체 감사 수행률</td>
                <td className="strong" data-source="S6-04__G0003">
                  {mt(metrics, "S6-04__G0003", mode)}
                </td>
                <td><span className="unit">연결</span></td>
              </tr>
              <tr>
                <td>고위험 공급업체 수</td>
                <td data-source="S6-04__G0004">
                  {mt(metrics, "S6-04__G0004", mode)}
                </td>
                <td><span className="unit">감사 식별</span></td>
              </tr>
              <tr>
                <td>공급망 CAP 완료율</td>
                <td className="up" data-source="S6-05__G0003">
                  {mt(metrics, "S6-05__G0003", mode)}
                </td>
                <td><span className="unit">시정 이행</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c-side">
          {/* CAP 완료율 게이지 */}
          <div className="sr-gauge">
            <div className="gl">CAP 완료율</div>
            <div className="gv" data-source="S6-05__G0003">
              {mt(metrics, "S6-05__G0003", mode)}
            </div>
            <div className="sr-track">
              <div className="sr-fill" style={{ width: `${fillPct}%` }} />
            </div>
            <div className="sr-gx"><span>0%</span><span>100%</span></div>
          </div>

          {/* 주요 시정조치 */}
          <div className="sr-note-card" data-source="S6-05__QL0001">
            <div className="l">주요 시정조치</div>
            <div className="b" style={{ fontSize: 11 }}>
              {mt(metrics, "S6-05__QL0001", mode)}
            </div>
          </div>
        </div>
      </div>

      <div className="sr-measures" data-source="S6-01__QL0001">
        <span className="ml">공급망 사회적 책임 정책</span>
        <span className="mv">{mt(metrics, "S6-01__QL0001", mode)}</span>
      </div>
    </SRChrome>
  );
}

const supplyChain = {
  id: "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
  label: "공급망 감사·시정조치",
  subLabel: "공급망 사회적 책임",
  exportName: "supply-chain",
  adapter: buildMetricsMap,
  metricFields,
  pages: [
    {
      key: "supply-chain-a",
      tabLabel: "공급망 감사",
      tocTag: "S6",
      Component: SupplyChainPage,
      props: {
        pageTitle: "공급망 감사·시정조치",
        pageTitleEn: "Supply Chain Audit & Corrective Action Plan",
        sourceNote: "SKM SR Template v1.0 · Auto-generated",
      },
    },
  ],
};

export default supplyChain;
