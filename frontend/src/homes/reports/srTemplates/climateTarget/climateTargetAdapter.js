// ============================================================
// climateTargetAdapter.js — 운영용 Adapter
// 기존 Draft.jsx의 report metric row(또는 API response)를
// SR 템플릿 props인 metrics Map(metric_id → MetricValue)으로 변환한다.
//
// 원칙 (prompt R1):
//  - 하드코딩된 더미 수치 금지
//  - metric_id 또는 atomicMetricId 기반 매핑
//  - displayValue가 있으면 우선 사용, 없으면 valueNumeric/valueText/unit으로 생성
//  - 값 누락 시 임의 숫자 생성 금지 → placeholder("—") 또는 미포함
//  - status가 있으면 보존
// ============================================================

/**
 * @typedef {import("./types").MetricsMap} MetricsMap
 */

/** 표시값 생성: API displayValue 우선 → 숫자/문자 → placeholder */
function buildDisplayValue(row) {
  if (row.displayValue != null && String(row.displayValue).trim() !== "") {
    return row.displayValue;
  }
  if (row.valueNumeric != null && !Number.isNaN(Number(row.valueNumeric))) {
    const n = Number(row.valueNumeric).toLocaleString("en-US");
    return row.unit ? `${n} ${row.unit}` : n;
  }
  if (row.valueText != null && String(row.valueText).trim() !== "") {
    return String(row.valueText);
  }
  return "—"; // 누락값: 임의 숫자 생성 금지
}

/** 차트 스케일·계산용 원천 숫자값 (없으면 null) */
function pickValue(row) {
  if (typeof row.valueNumeric === "number") return row.valueNumeric;
  if (typeof row.value === "number") return row.value;
  if (row.valueNumeric != null) {
    const n = parseFloat(String(row.valueNumeric).replace(/[^0-9.\-]/g, ""));
    if (!Number.isNaN(n)) return n;
  }
  return row.value ?? null;
}

/**
 * metric row 배열을 SR 템플릿 metrics Map으로 변환.
 * @param {Array<Object>} [metricRows=[]]
 * @returns {MetricsMap}
 */
export function toClimateTargetMetrics(metricRows = []) {
  /** @type {MetricsMap} */
  const map = {};
  if (!Array.isArray(metricRows)) return map;

  for (const row of metricRows) {
    if (!row) continue;
    const id =
      row.metricId ??
      row.metric_id ??
      row.atomicMetricId ??
      row.atomic_metric_id;
    if (!id) continue;

    map[id] = {
      value: pickValue(row),
      displayValue: buildDisplayValue(row),
      unit: row.unit,
      sourceType: row.sourceType ?? row.source_type,
      status: row.status, // 검수 상태 보존 (있으면)
      label: row.label,
    };
  }
  return map;
}

export default toClimateTargetMetrics;
