// srTemplates/subIssues/ecoProduct.jsx
// 저탄소·친환경 제품 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

const TEMPLATE =
  "{AP-E-06__QL0001} {AP-E-06__QL0002} 연결 친환경 제품 매출액은 {AP-E-06__G0001}이며, " +
  "연결 매출 대비 비중은 {AP-E-06__G0003}이다. " +
  "회피 배출량은 {AP-E-06__G0004}, 사회적 비용 절감 효과는 {AP-E-06__G0005}로 산정된다.";

const metricFields = [
  { id: "AP-E-06__QL0001", label: "친환경 제품 전략 개요" },
  { id: "AP-E-06__QL0002", label: "친환경 인증·기준 설명" },
  { id: "AP-E-06__G0001", label: "친환경 제품 매출액" },
  { id: "AP-E-06__G0003", label: "매출 대비 친환경 비중" },
  { id: "AP-E-06__G0004", label: "제품 사용 회피 배출량" },
  { id: "AP-E-06__G0005", label: "사회적 비용 절감 효과" },
];

function EcoProductPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const greenRatio = num(metrics, "AP-E-06__G0003");
  const fillPct = greenRatio != null ? Math.min(Math.max(greenRatio, 0), 100) : 0;

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
          <div className="kl">친환경 제품 매출액</div>
          <div className="kv" data-source="AP-E-06__G0001">{mt(metrics, "AP-E-06__G0001", mode)}</div>
          <div className="kd up">연결 기준</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">매출 대비 비중</div>
          <div className="kv" data-source="AP-E-06__G0003">{mt(metrics, "AP-E-06__G0003", mode)}</div>
          <div className="kd up">친환경 포트폴리오</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">회피 배출량</div>
          <div className="kv" data-source="AP-E-06__G0004">{mt(metrics, "AP-E-06__G0004", mode)}</div>
          <div className="kd down">제품 사용단계</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">사회적 비용 절감</div>
          <div className="kv" data-source="AP-E-06__G0005">{mt(metrics, "AP-E-06__G0005", mode)}</div>
          <div className="kd up">탄소비용 환산</div>
        </div>
      </div>

      {/* 친환경 제품 성과 상세 */}
      <div className="sr-cols" style={{ marginTop: 16 }}>
        <div className="c-main">
          <div className="sr-tcap">
            <span className="num">1</span>친환경 제품 성과 지표
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
                <td>친환경 제품 매출액</td>
                <td className="strong" data-source="AP-E-06__G0001">
                  {mt(metrics, "AP-E-06__G0001", mode)}
                </td>
                <td><span className="unit">연결</span></td>
              </tr>
              <tr>
                <td>매출 대비 친환경 비중</td>
                <td className="up" data-source="AP-E-06__G0003">
                  {mt(metrics, "AP-E-06__G0003", mode)}
                </td>
                <td><span className="unit">%</span></td>
              </tr>
              <tr>
                <td>제품 사용 회피 배출량</td>
                <td data-source="AP-E-06__G0004">
                  {mt(metrics, "AP-E-06__G0004", mode)}
                </td>
                <td><span className="unit">tCO₂eq</span></td>
              </tr>
              <tr>
                <td>사회적 비용 절감 효과</td>
                <td data-source="AP-E-06__G0005">
                  {mt(metrics, "AP-E-06__G0005", mode)}
                </td>
                <td><span className="unit">KRW</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c-side">
          {/* 친환경 매출 비중 게이지 */}
          <div className="sr-gauge">
            <div className="gl">매출 대비 친환경 비중</div>
            <div className="gv" data-source="AP-E-06__G0003">
              {mt(metrics, "AP-E-06__G0003", mode)}
            </div>
            <div className="sr-track">
              <div className="sr-fill" style={{ width: `${fillPct}%` }} />
            </div>
            <div className="sr-gx"><span>0%</span><span>100%</span></div>
          </div>

          {/* 친환경 인증·기준 */}
          <div className="sr-note-card" data-source="AP-E-06__QL0002">
            <div className="l">친환경 인증·기준</div>
            <div className="b" style={{ fontSize: 11 }}>
              {mt(metrics, "AP-E-06__QL0002", mode)}
            </div>
          </div>
        </div>
      </div>

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
      },
    },
  ],
};

export default ecoProduct;
