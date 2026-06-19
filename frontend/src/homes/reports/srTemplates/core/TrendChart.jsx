/**
 * TrendChart.jsx
 * 레이어: Component (srTemplates/core)
 * 역할: 지표의 연도별 추이 데이터를 SVG 꺾은선 그래프로 렌더링하는 미니 트렌드 차트
 *
 * Props:
 *   trend — 연도·값 배열 [{ y: string, v: number }, ...]
 */
const TrendChart = ({ trend }) => {
  const W = 280, H = 60, pad = 20;
  const vals = trend.map((t) => t.v);
  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const range = maxV - minV || 1;
  const pts = trend.map((t, i) => ({
    x: pad + (i / (trend.length - 1)) * (W - pad * 2),
    y: H - pad - ((t.v - minV) / range) * (H - pad * 2),
    year: t.y,
    val: t.v,
  }));
  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <svg className="trend-svg" viewBox={`0 0 ${W} ${H}`} xmlns="http://www.w3.org/2000/svg">
      <path d={pathD} fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="4" fill="#03A94D" stroke="#fff" strokeWidth="2" />
          <text x={p.x} y={p.y - 9} textAnchor="middle" fontSize="9" fontWeight="700" fill="#334155">
            {p.val.toLocaleString()}
          </text>
          <text x={p.x} y={H - 4} textAnchor="middle" fontSize="9" fill="#94a3b8">
            {p.year}
          </text>
        </g>
      ))}
    </svg>
  );
};

export default TrendChart;
