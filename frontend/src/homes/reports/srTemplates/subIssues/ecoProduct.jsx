/**
 * ecoProduct.jsx
 * 레이어: Component (srTemplates/subIssues)
 * 역할: 저탄소·친환경 제품 서브이슈의 SR 페이지 컴포넌트, adapter, metricFields, 서브이슈 매니페스트를 포함한 모듈 — 친환경 제품 매출액·회피 배출량·매출 비중 게이지를 렌더링
 *
 * exports:
 *   ecoProduct (default) — id·label·adapter·metricFields·pages를 포함하는 서브이슈 매니페스트 객체
 */
// srTemplates/subIssues/ecoProduct.jsx
// 저탄소·친환경 제품 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

// AI 생성 문단이 없을 때 폴백 — 숫자 지표만 참조
const TEMPLATE =
  "연결 친환경 제품 매출액은 {AP-E-06__G0001}이며, 연결 매출 대비 비중은 {AP-E-06__G0003}이다. " +
  "제품 사용 단계 회피 배출량은 {AP-E-06__G0004}, 사회적 비용 절감 효과는 {AP-E-06__G0005}로 산정된다.";

const metricFields = [
  { id: "AP-E-06__G0001",  label: "친환경 제품 매출액" },
  { id: "AP-E-06__G0003",  label: "매출 대비 친환경 비중" },
  { id: "AP-E-06__G0004",  label: "제품 사용 회피 배출량" },
  { id: "AP-E-06__G0005",  label: "사회적 비용 절감 효과" },
  { id: "AP-E-06__QL0001", label: "친환경 제품 전략" },
  { id: "AP-E-06__QL0002", label: "친환경 인증·기준" },
];

function EcoProductPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const greenRatio = num(metrics, "AP-E-06__G0003");
  const fillPct = greenRatio != null ? Math.min(Math.max(greenRatio, 0), 100) : 0;

  return (
    <SRChrome {...props}>
      {/* 문단 + 친환경 제품 매출액 KPI 나란히 */}
      <div className="sr-cols">
        <div className="c-main">
          <Narrative
            narrativeText={narrativeText}
            template={TEMPLATE}
            metrics={metrics}
            mode={mode}
            metricIds={aiMetricIds}
            onNarrativeChange={props.onNarrativeChange}
          />
        </div>
        <div className="c-side">
          <div className="sr-panel" style={{ padding: "16px 14px" }}>
            <div className="sr-stat hl">
              <span className="l">
                친환경 제품 매출액<br />
                <small>연결 기준</small>
              </span>
              <span className="v" data-source="AP-E-06__G0001">
                {mt(metrics, "AP-E-06__G0001", mode)}
              </span>
            </div>
            {/* <div style={{ marginTop: 10, borderTop: "1px solid var(--panel-line)", paddingTop: 10 }}>
              <div style={{ fontSize: 18, fontWeight: 900, color: "var(--brand)" }}
                data-source="AP-E-06__G0003">
                {mt(metrics, "AP-E-06__G0003", mode)}
              </div>
              <div className="sr-track" style={{ marginTop: 6 }}>
                <div className="sr-fill" style={{ width: `${fillPct}%` }} />
              </div>
            </div> */}
          </div>
        </div>
      </div>

      {/* ── 친환경 임팩트 패널 — flex:1 로 남은 공간 흡수 ── */}
      <div className="sr-panel sr-last">
        <div className="sr-panel-grid">

          {/* 좌: 환경 임팩트 수치 (sr-stat) */}
          <div className="sr-panel-l">
            <div className="sr-panel-h">
              <span className="tagn">1</span> 친환경 제품 환경 임팩트
            </div>
            <div className="sr-stat hl">
              <span className="l">
                제품 사용 단계 회피 배출량<br />
                <small>고객 사용 시 탄소 감축 기여량</small>
              </span>
              <span className="v" data-source="AP-E-06__G0004">
                {mt(metrics, "AP-E-06__G0004", mode)}
              </span>
            </div>
            <div className="sr-stat hl">
              <span className="l">
                사회적 비용 절감 효과<br />
                <small>탄소 사회비용 기준 환산액</small>
              </span>
              <span className="v" data-source="AP-E-06__G0005">
                {mt(metrics, "AP-E-06__G0005", mode)}
              </span>
            </div>
            <div className="sr-flow-note" data-source="AP-E-06__QL0002">
              <b>친환경 인증·기준</b> · {mt(metrics, "AP-E-06__QL0002", mode)}
            </div>
          </div>

          {/* 우: 매출 비중 게이지 */}
          <div className="sr-panel-r">
            <div className="sr-panel-h">친환경 매출 비중</div>
            <div style={{ paddingTop: 4 }}>
              <div className="gv" style={{ fontSize: 26, fontWeight: 900, color: "var(--brand)", marginBottom: 8 }}
                data-source="AP-E-06__G0003">
                {mt(metrics, "AP-E-06__G0003", mode)}
              </div>
              <div className="sr-track">
                <div className="sr-fill" style={{ width: `${fillPct}%` }} />
              </div>
              <div className="sr-gx"><span>0%</span><span>100%</span></div>
              <div style={{ fontSize: 9, color: "var(--muted)", marginTop: 8, lineHeight: 1.5 }}>
                연결 매출 대비 친환경 제품이 차지하는 비중
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 친환경 제품 전략 ── */}
      <div className="sr-measures" data-source="AP-E-06__QL0001">
        <span className="ml">친환경 제품 전략</span>
        <span className="mv">{mt(metrics, "AP-E-06__QL0001", mode)}</span>
      </div>
    </SRChrome>
  );
}

const ecoProduct = {
  id: "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE",
  label: "저탄소·친환경 제품",
  subLabel: "친환경 제품 성과",
  exportName: "eco-product",
  adapter: buildMetricsMap,
  metricFields,
  pages: [
    {
      key: "eco-product-a",
      tabLabel: "친환경 제품",
      tocTag: "AP-E",
      Component: EcoProductPage,
      props: {
        pageTitle: "저탄소·친환경 제품",
        pageTitleEn: "Low-Carbon & Eco-Friendly Products",
        sourceNote: "SKM SR Template v1.0 · Auto-generated",
        footnotes: [
          "1) 회피 배출량: 제품 사용 단계에서 기존 대비 절감된 온실가스 배출량 (tCO₂eq 기준)",
          "2) 사회적 비용: 탄소 사회적 비용(SCC) 기준 환산 / 3) 친환경 제품 기준은 사내 인증 기준 및 법적 기준 준용",
        ],
        subNavItems: [
          { label: "기후변화 대응" },
          { label: "공급망 감사" },
          { label: "교육훈련" },
          { label: "친환경 제품", active: true },
          { label: "제품안전" },
        ],
      },
    },
  ],
};

export default ecoProduct;
