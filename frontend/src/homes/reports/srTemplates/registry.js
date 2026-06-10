// srTemplates/registry.js
// ── 서브이슈 레지스트리 ──
// 모든 서브이슈 모듈을 여기서 모은다. 새 서브이슈 추가 = import 한 줄 + 배열에 추가.
import climateTarget from "./subIssues/climateTarget.jsx";
// import supplyChain from "./subIssues/supplyChain";   // 예: 새 서브이슈
// import humanCapital from "./subIssues/humanCapital";

export const subIssues = [
  climateTarget,
  // supplyChain,
  // humanCapital,
];

// id 로 서브이슈 모듈 조회
export const getSubIssue = (id) => subIssues.find((s) => s.id === id);

// 모든 서브이슈의 페이지를 평탄화 (각 항목에 소속 서브이슈 정보 부착)
export const allPages = subIssues.flatMap((si) =>
  si.pages.map((p) => ({ ...p, subIssueId: si.id, subIssueLabel: si.label }))
);

export default subIssues;