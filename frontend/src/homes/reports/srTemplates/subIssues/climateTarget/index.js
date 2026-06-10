// subIssues/climateTarget/index.js
// ── 서브이슈 모듈 매니페스트 (표준 인터페이스) ──
// 새 서브이슈를 추가하려면 이와 동일한 형태의 index.js 를 가진 폴더를 만들고
// registry.js 에 한 줄 추가하면 Draft 화면/편집/PDF에 자동 반영된다.
import { ClimateTargetPageA } from "./pages/ClimateTargetPageA";
import { ClimateTargetPageB } from "./pages/ClimateTargetPageB";
import { toClimateTargetMetrics } from "./adapter";
import { metricFields } from "./metricFields";

const climateTarget = {
  id: "climate-target",          // 서브이슈 코드 or id (ESG_SUB_ISSUE_MASTRE)
  label: "기후목표·전환계획",      // 서브이슈 이름_kr
  subLabel: "기후변화 대응",       // 이슈 그룹 이름
  exportName: "climate-target",  // PDF 파일명 (climate-target.pdf)

  adapter: toClimateTargetMetrics, // metric rows → metrics Map  차트 변경? 

  metricFields,                    
  // ESG_SUB_ISSUE_ATOMIC_MAP atomic_metric_id,  
  // ESG_SUB_ISSUE_MASTRE join 해서 서브이슈 네임 

  // 이 서브이슈가 가진 페이지들 (A안 시각화 / B안 표)
  pages: [
    {
      key: "climate-a", //그래프 
      tabLabel: "asd", //climateTarget.subLabel, 이런 느낌
      Component: ClimateTargetPageA,
      props: {
        pageTitle: 'label', //label
        pageTitleEn: "Climate Target & Transition Plan", //서브이슈마스터 서브이슈 영어 이름
        sourceNote: "SKM SR Template v1.0 · Auto-generated", // 고정 상수 예정
      },
    },
    {
      key: "climate-b", //표
      tabLabel: "기후변화 대응 · 표",
      Component: ClimateTargetPageB,
      props: {
        pageTitle: '기후목표 및 <span class="ac">전환계획</span>',
        pageTitleEn: "Climate Target & Transition Plan",
        sourceNote: "Narrative Template v1.0 · Auto-generated",
      },
    },
  ],
};

export default climateTarget;
