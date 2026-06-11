// srTemplates/subIssues/supplyChain.jsx
// 공급망 감사·시정조치 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, buildMetricsMap } from "../core/srHelpers";

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
  return (
    <SRChrome {...props}>
      <Narrative
        narrativeText={narrativeText}
        template={TEMPLATE}
        metrics={metrics}
        mode={mode}
        metricIds={aiMetricIds}
        onNarrativeChange={props.onNarrativeChange}
      />

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

      <div className="sr-measures" data-source="S6-05__QL0001">
        <span className="ml">주요 시정조치 내용</span>
        <span className="mv">{mt(metrics, "S6-05__QL0001", mode)}</span>
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
