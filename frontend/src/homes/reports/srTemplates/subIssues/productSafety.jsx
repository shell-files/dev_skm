// srTemplates/subIssues/productSafety.jsx
// 소비자 건강·제품안전 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

const TEMPLATE =
  "{AP-S-01__QL0001} {AP-S-01__QL0002} {AP-S-01__QL0003} " +
  "연결 기준 필드액션 건수는 {AP-S-01__G0001}, 리콜 건수는 {AP-S-01__G0002}이며, " +
  "제품안전 CAP 완료율은 {AP-S-01__G0005}이다.";

const metricFields = [
  { id: "AP-S-01__QL0001", label: "제품안전 경영 방침" },
  { id: "AP-S-01__QL0002", label: "제품안전 거버넌스" },
  { id: "AP-S-01__QL0003", label: "제품안전 주요 이슈 대응" },
  { id: "AP-S-01__G0001", label: "필드액션 건수" },
  { id: "AP-S-01__G0002", label: "리콜 건수" },
  { id: "AP-S-01__G0005", label: "제품안전 CAP 완료율" },
];

function ProductSafetyPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const capRate = num(metrics, "AP-S-01__G0005");
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
          <div className="kl">필드액션 건수</div>
          <div className="kv" data-source="AP-S-01__G0001">{mt(metrics, "AP-S-01__G0001", mode)}</div>
          <div className="kd flat">연결 기준</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">리콜 건수</div>
          <div className="kv" data-source="AP-S-01__G0002">{mt(metrics, "AP-S-01__G0002", mode)}</div>
          <div className="kd down">자발적 포함</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">CAP 완료율</div>
          <div className="kv" data-source="AP-S-01__G0005">{mt(metrics, "AP-S-01__G0005", mode)}</div>
          <div className="kd up">제품안전 시정조치</div>
        </div>
      </div>

      {/* 제품안전 지표 상세 */}
      <div className="sr-cols" style={{ marginTop: 16 }}>
        <div className="c-main">
          <div className="sr-tcap">
            <span className="num">1</span>제품안전 핵심 성과 지표
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
                <td>필드액션 건수</td>
                <td data-source="AP-S-01__G0001">
                  {mt(metrics, "AP-S-01__G0001", mode)}
                </td>
                <td><span className="unit">건</span></td>
              </tr>
              <tr>
                <td>리콜 건수</td>
                <td data-source="AP-S-01__G0002">
                  {mt(metrics, "AP-S-01__G0002", mode)}
                </td>
                <td><span className="unit">건(자발적 포함)</span></td>
              </tr>
              <tr>
                <td>제품안전 CAP 완료율</td>
                <td className="up" data-source="AP-S-01__G0005">
                  {mt(metrics, "AP-S-01__G0005", mode)}
                </td>
                <td><span className="unit">시정 이행</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c-side">
          {/* CAP 완료율 게이지 */}
          <div className="sr-gauge">
            <div className="gl">제품안전 CAP 완료율</div>
            <div className="gv" data-source="AP-S-01__G0005">
              {mt(metrics, "AP-S-01__G0005", mode)}
            </div>
            <div className="sr-track">
              <div className="sr-fill" style={{ width: `${fillPct}%` }} />
            </div>
            <div className="sr-gx"><span>0%</span><span>100%</span></div>
          </div>

          {/* 주요 이슈 대응 */}
          <div className="sr-note-card" data-source="AP-S-01__QL0003">
            <div className="l">주요 이슈 대응</div>
            <div className="b" style={{ fontSize: 11 }}>
              {mt(metrics, "AP-S-01__QL0003", mode)}
            </div>
          </div>
        </div>
      </div>

      <div className="sr-measures" data-source="AP-S-01__QL0001">
        <span className="ml">제품안전 경영 방침</span>
        <span className="mv">{mt(metrics, "AP-S-01__QL0001", mode)}</span>
      </div>
    </SRChrome>
  );
}

const productSafety = {
  id: "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY",
  label: "소비자 건강·제품안전",
  subLabel: "제품 책임",
  exportName: "product-safety",
  adapter: buildMetricsMap,
  metricFields,
  pages: [
    {
      key: "product-safety-a",
      tabLabel: "제품안전",
      tocTag: "AP-S",
      Component: ProductSafetyPage,
      props: {
        pageTitle: "소비자 건강·제품안전",
        pageTitleEn: "Consumer Health & Product Safety",
        sourceNote: "SKM SR Template v1.0 · Auto-generated",
      },
    },
  ],
};

export default productSafety;
