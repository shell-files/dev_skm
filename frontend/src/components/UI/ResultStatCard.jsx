/**
 * ResultStatCard.jsx
 * 레이어: Component (UI)
 * 역할: 분석 결과 대시보드의 통계 카드 — 아이콘·레이블·값·서브텍스트를 표시하는 공통 컴포넌트.
 *
 * Props:
 *   label      {string}    — 통계 항목 레이블
 *   value      {string}    — 통계 값 (단위 포함 문자열)
 *   sub        {string}    — 보조 텍스트 (선택)
 *   icon       {ReactNode} — 아이콘 JSX (선택)
 *   colorClass {string}    — 색상 변형 클래스 (예: "stat-card-blue", 선택)
 */
const ResultStatCard = ({ label, value, sub, icon, colorClass }) => {
  const iconColorClass = colorClass
    ? `stat-icon-${colorClass.replace("stat-card-", "")}`
    : "";
  return (
    <div className={["result-stat-card", colorClass].filter(Boolean).join(" ")}>
      {icon && (
        <div className={["stat-icon-wrap", iconColorClass].filter(Boolean).join(" ")}>
          {icon}
        </div>
      )}
      <div>
        <div className="stat-label">{label}</div>
        {sub ? (
          <div className="stat-value-row">
            <div className="stat-value">{value}</div>
            <div className="stat-sub">{sub}</div>
          </div>
        ) : (
          <div className="stat-value">{value}</div>
        )}
      </div>
    </div>
  );
};

export default ResultStatCard;
