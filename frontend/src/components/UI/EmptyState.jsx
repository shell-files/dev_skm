/**
 * EmptyState.jsx
 * 레이어: Component (UI)
 * 역할: 데이터가 없거나 접근 불가 상태를 안내하는 공통 빈 상태 컴포넌트.
 *
 * Props:
 *   title   {string} — 주 안내 문구 (굵게 표시)
 *   desc    {string} — 보조 안내 문구 (회색, 선택)
 *   icon    {string} — 선택적 아이콘 이모지 또는 텍스트 (선택)
 */

const STYLES = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px 24px",
    textAlign: "center",
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
  },
  icon: {
    fontSize: "2.5rem",
    marginBottom: "12px",
    opacity: 0.6,
  },
  title: {
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#334155",
    margin: "0 0 8px 0",
  },
  desc: {
    fontSize: "0.9rem",
    color: "#64748b",
    lineHeight: 1.5,
    margin: 0,
  },
};

const EmptyState = ({ title, desc, icon }) => (
  <div style={STYLES.container}>
    {icon && <div style={STYLES.icon}>{icon}</div>}
    <p style={STYLES.title}>{title}</p>
    {desc && <p style={STYLES.desc}>{desc}</p>}
  </div>
);

export default EmptyState;
