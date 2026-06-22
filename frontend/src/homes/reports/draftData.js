/**
 * draftData.js
 * 레이어: Utils (reports)
 * 역할: 보고서 초안 페이지 레지스트리·필드맵 — srTemplates/registry 기반 정적 파생 데이터
 */
import { subIssues } from "./srTemplates/registry";

export const PAGES = subIssues.flatMap((si) =>
  si.pages.map((p) => ({
    ...p,
    tocTitle: si.label,
    subIssueId: si.id,
    subIssueLabel: si.label,
    exportName: si.exportName,
    adapter: si.adapter,
    metricFields: si.metricFields,
  }))
);

export const SR_FIELD_MAP = (() => {
  const map = {};
  subIssues.forEach((si) =>
    (si.metricFields || []).forEach((f) => {
      map[f.id] = { label: f.label, subIssueLabel: si.label };
    })
  );
  return map;
})();
