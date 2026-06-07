// subIssues/climateTarget/index.js
// ── 서브이슈 모듈 매니페스트 (표준 인터페이스) ──
// 새 서브이슈를 추가하려면 이와 동일한 형태의 index.js 를 가진 폴더를 만들고
// registry.js 에 한 줄 추가하면 Draft 화면/편집/PDF에 자동 반영된다.
import { ClimateTargetPageA } from "./pages/ClimateTargetPageA";
import { ClimateTargetPageB } from "./pages/ClimateTargetPageB";
import { toClimateTargetMetrics } from "./adapter";
import { metricFields } from "./metricFields";

const climateTarget = {
  id: "climate-target",          // 고유 식별자 (편집 상태 key, DOM id 등에 사용)
  label: "기후목표·전환계획",      // 목차/탭에 표시될 이름
  subLabel: "기후변화 대응",       // 상위 분류
  exportName: "climate-target",  // PDF 파일명 (climate-target.pdf)

  adapter: toClimateTargetMetrics, // metric rows → metrics Map
  metricFields,                    // 이 서브이슈의 편집 필드

  // 이 서브이슈가 가진 페이지들 (A안 시각화 / B안 표)
  pages: [
    {
      key: "climate-a",
      tabLabel: "기후변화 대응 · 시각화",
      tocTag: "시각화",
      Component: ClimateTargetPageA,
      props: {
        pageTitle: '기후목표 및 <span class="ac">전환계획</span>',
        pageTitleEn: "Climate Target & Transition Plan",
        sectionLabel: "전략 · CLIMATE TARGET",
        ghost: "STRATEGY",
        pageNumber: 42,
        sourceNote: "Narrative Template v1.0 · Auto-generated",
      },
    },
    {
      key: "climate-b",
      tabLabel: "기후변화 대응 · 표",
      tocTag: "데이터 표",
      Component: ClimateTargetPageB,
      props: {
        pageTitle: '기후목표 및 <span class="ac">전환계획</span>',
        pageTitleEn: "Climate Target & Transition Plan",
        sectionLabel: "데이터 · CLIMATE TARGET",
        ghost: "DATA",
        pageNumber: 43,
        sourceNote: "Narrative Template v1.0 · Auto-generated",
      },
    },
  ],
};

export default climateTarget;
