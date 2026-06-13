// srTemplates/subIssues/productSafety.jsx
// 소비자 건강·제품안전 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

// AI 생성 문단이 없을 때 폴백 — 숫자 지표만 참조
const TEMPLATE =
  "연결 기준 필드액션 건수는 {AP-S-01__G0001}, 리콜 건수는 {AP-S-01__G0002}이며, " +
  "제품안전 CAP 완료율은 {AP-S-01__G0005}이다.";

const metricFields = [
  { id: "AP-S-01__G0001", label: "필드액션 건수" },
  { id: "AP-S-01__G0002", label: "리콜 건수" },
  { id: "AP-S-01__G0005", label: "제품안전 CAP 완료율" },
  { id: "AP-S-01__QL0001", label: "제품안전 경영 방침" },
  { id: "AP-S-01__QL0002", label: "제품안전 거버넌스" },
  { id: "AP-S-01__QL0003", label: "주요 이슈 대응" },
];

function ProductSafetyPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const capRate = num(metrics, "AP-S-01__G0005");
  const fillPct = capRate != null ? Math.min(Math.max(capRate, 0), 100) : 0;

  return (
    <SRChrome {...props}>
      {/* 문단 + CAP 완료율 게이지 나란히 */}
      <div className="sr-cols" style={{ alignItems: "stretch" }}>
        <div className="c-main" style={{ display: "flex", flexDirection: "column" }}>
          <Narrative
            narrativeText={narrativeText}
            template={TEMPLATE}
            metrics={metrics}
            mode={mode}
            metricIds={aiMetricIds}
            onNarrativeChange={props.onNarrativeChange}
          />
        </div>
        <div className="c-side" style={{ display: "flex", alignItems: "center" }}>
          <div className="sr-gauge" style={{ width: "100%" }}>
            <div className="gl">제품안전 CAP 완료율</div>
            <div className="gv" data-source="AP-S-01__G0005">
              {mt(metrics, "AP-S-01__G0005", mode)}
            </div>
            <div className="sr-track">
              <div className="sr-fill" style={{ width: `${fillPct}%` }} />
            </div>
            <div className="sr-gx"><span>0%</span><span>100%</span></div>
          </div>
        </div>
      </div>

      {/* ── 제품안전 거버넌스 & 이슈 대응 ── */}
      <div className="sr-panel" style={{ marginTop: 16 }}>
        <div className="sr-panel-grid">

          {/* 좌: 거버넌스 */}
          <div className="sr-panel-l">
            <div>
              <div className="sr-panel-h">
                <span className="tagn">1</span> 제품안전 거버넌스 체계
              </div>
              <div className="sr-flow-note" data-source="AP-S-01__QL0002">
                {mt(metrics, "AP-S-01__QL0002", mode)}
              </div>
            </div>
            <div style={{ marginTop: 12, borderTop: "1px dashed var(--panel-line)", paddingTop: 10 }}>
              <div className="sr-panel-h" style={{ marginBottom: 6 }}>
                <span className="tagn">2</span> 주요 이슈 대응
              </div>
              <div className="sr-flow-note" data-source="AP-S-01__QL0003">
                {mt(metrics, "AP-S-01__QL0003", mode)}
              </div>
            </div>
          </div>

          {/* 우: 안전 사고 수치 */}
          <div className="sr-panel-r">
            <div className="sr-panel-h">안전 사고 현황</div>
            <div className="sr-stat hl">
              <span className="l">
                필드액션 건수<br />
                <small>연결 기준 발생</small>
              </span>
              <span className="v" data-source="AP-S-01__G0001">
                {mt(metrics, "AP-S-01__G0001", mode)}
              </span>
            </div>
            <div className="sr-stat">
              <span className="l">
                리콜 건수<br />
                <small>자발적 리콜 포함</small>
              </span>
              <span className="v" data-source="AP-S-01__G0002">
                {mt(metrics, "AP-S-01__G0002", mode)}
              </span>
            </div>
          </div>

        </div>
      </div>

      {/* ── 제품안전 경영 방침 ── */}
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
        footnotes: [
          "1) 필드액션: 안전·환경·규정 관련 시장 조치 (자발적 리콜 포함)",
          "2) CAP 완료율 = 시정조치 완료 건수 ÷ 전체 CAP 대상 건수",
        ],
        subNavItems: [
          { label: "기후변화 대응" },
          { label: "공급망 감사" },
          { label: "교육훈련" },
          { label: "친환경 제품" },
          { label: "제품안전", active: true },
        ],
      },
    },
  ],
};

export default productSafety;
