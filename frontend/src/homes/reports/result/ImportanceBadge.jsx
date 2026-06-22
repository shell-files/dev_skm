/**
 * ImportanceBadge.jsx
 * 중요도 값을 색상 뱃지로 표시하는 순수 표시 컴포넌트.
 * Result.jsx 테이블 셀에서 재무/환경사회 중요도 표시용으로 사용.
 *
 * props:
 *   value — 숫자(1/2/3), 문자열(low/medium/high), ⚫ 개수, 또는 기회/위기/장기/단기
 *
 * export default: ImportanceBadge
 */

/** 중요도 키 → 표시 텍스트/색상/배경색 설정 */
const IMPORTANCE_LEVELS = {
  1: { text: "Low", color: "#64748b", bg: "#f1f5f9" },
  2: { text: "Middle", color: "#d97706", bg: "#fffbeb" },
  3: { text: "High", color: "#ef4444", bg: "#fff5f5" },
  low: { text: "Low", color: "#64748b", bg: "#f1f5f9" },
  medium: { text: "Middle", color: "#d97706", bg: "#fffbeb" },
  high: { text: "High", color: "#ef4444", bg: "#fff5f5" },
  기회: { text: "기회", color: "#22c55e", bg: "#f1f5f9" },
  위기: { text: "위기", color: "#ef4444", bg: "#f1f5f9" },
  장기: { text: "위기", color: "#64748b", bg: "#f1f5f9" },
  단기: { text: "위기", color: "#d97706", bg: "#f1f5f9" },
};

/** 다양한 입력 형식(숫자/문자열/⚫ 개수)을 IMPORTANCE_LEVELS 키로 정규화 */
const normalizeImportance = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  if (num === 1 || num === 2 || num === 3) return num;
  if (typeof value === "string") {
    const lower = value.toLowerCase().trim();
    if (lower === "low" || lower === "medium" || lower === "high") return lower;
    const dotCount = (value.match(/⚫/g) || []).length;
    if (dotCount >= 1 && dotCount <= 3) return dotCount;
  }
  return null;
};

const ImportanceBadge = ({ value }) => {
  const key = normalizeImportance(value);
  const level = key != null ? IMPORTANCE_LEVELS[key] : null;

  if (!level) {
    return (
      <span style={{ color: "#94a3b8", fontSize: "0.78rem" }}>-</span>
    );
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "3px",
        padding: "2px 8px",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        background: level.bg,
        color: level.color,
        whiteSpace: "nowrap",
      }}
    >
      {level.text}
    </span>
  );
};

export default ImportanceBadge;
