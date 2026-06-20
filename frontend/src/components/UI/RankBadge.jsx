/**
 * RankBadge.jsx
 * 레이어: Component (UI)
 * 역할: 순위 숫자를 표시하는 배지 — 1~3위는 rank-top{N} 강조 클래스 적용.
 * Props: rank {number}
 */
const RankBadge = ({ rank }) => (
  <span className={`rank-badge${rank <= 3 ? ` rank-top${rank}` : ""}`}>
    {rank}
  </span>
);

export default RankBadge;
