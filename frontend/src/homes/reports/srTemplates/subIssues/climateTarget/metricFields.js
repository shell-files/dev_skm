// subIssues/climateTarget/metricFields.js
// 이 서브이슈(기후목표·전환계획)의 웹 편집 대상 지표 필드 (template이 참조하는 metric_id 스키마)
// 값은 비어 있는 상태로 시작 — 사용자가 입력. (하드코딩 더미 수치 아님)
export const metricFields = [
  { id: "E1-05__QL0002", label: "기준연도" },
  { id: "E1-05__G0003", label: "기준연도 Scope1·2 배출량" },
  { id: "E1-06__G0003", label: "보고연도 Scope1·2 배출량" },
  { id: "E1-06__G0004", label: "전년 대비 감축량" },
  { id: "E1-06__G0005", label: "감축률" },
  { id: "E1-07__G0003", label: "재생에너지 전환율" },
  { id: "E1-08__G0001", label: "탄소중립 목표연도" },
  { id: "E1-08__G0002", label: "재생E 100% 목표연도" },
  { id: "E1-08__QL0001", label: "탄소중립 범위" },
  { id: "E1-08__QL0002", label: "재생E 목표수준" },
  { id: "E1-05__G0001", label: "기준 Scope 1 (선택)" },
  { id: "E1-05__G0002", label: "기준 Scope 2 (선택)" },
  { id: "E1-06__G0001", label: "보고 Scope 1 (선택)" },
  { id: "E1-06__G0002", label: "보고 Scope 2 (선택)" },
];

export default metricFields;
