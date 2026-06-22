/**
 * DoubleMaterialityChart.jsx
 * 이중 중대성 매트릭스 차트 컴포넌트.
 * Result.jsx에서 분석 결과 scatter plot 시각화에 사용.
 *
 * 주요 구성:
 *   CAT_CONFIG           — E/S/G 카테고리별 색상/배지 설정
 *   ZoneOverlay          — SVG로 핵심/보고/잠재적 이슈 구역 원형 레이어 렌더
 *   RankedDot            — Recharts scatter 커스텀 도트 (순위 번호 표시)
 *   MatrixTooltip        — scatter 호버 툴팁 (이슈명/카테고리/중요성 레벨)
 *   DoubleMaterialityMatrix — 전체 매트릭스 차트 + 범례 + 이슈 그리드
 *
 * export default: DoubleMaterialityMatrix
 */

import { useState, useRef, useEffect } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ReferenceLine,
  ReferenceArea,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const CAT_CONFIG = {
  E: { label: "환경(E)", bg: "rgba(34,197,94,0.92)", badge: { bg: "#dcfce7", color: "#16a34a" } },
  S: { label: "사회(S)", bg: "rgba(59,130,246,0.92)", badge: { bg: "#dbeafe", color: "#2563eb" } },
  G: { label: "거버넌스(G)", bg: "rgba(245,43,43,0.88)", badge: { bg: "#fee2e2", color: "#dc2626" } },
};

/** 차트 플롯 영역에 핵심/보고/잠재적 구역 원형 그라데이션 오버레이 */
const ZoneOverlay = ({ containerRef }) => {
  const [dims, setDims] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const measure = () => {
      const wrap = containerRef.current;
      if (!wrap) return;
      const svg = wrap.querySelector("svg.recharts-surface");
      const grid = wrap.querySelector(".recharts-cartesian-grid rect");
      if (!svg || !grid) return;

      const svgRect = svg.getBoundingClientRect();
      const gridRect = grid.getBoundingClientRect();

      setDims({
        svgW: svgRect.width,
        svgH: svgRect.height,
        plotLeft: gridRect.left - svgRect.left,
        plotTop: gridRect.top - svgRect.top,
        plotWidth: gridRect.width,
        plotHeight: gridRect.height,
      });
    };

    const t = setTimeout(measure, 60);
    const ro = new ResizeObserver(measure);
    ro.observe(containerRef.current);

    return () => { clearTimeout(t); ro.disconnect(); };
  }, [containerRef]);

  if (!dims) return null;

  const { svgW, svgH, plotLeft, plotTop, plotWidth, plotHeight } = dims;
  const ox = plotLeft + plotWidth;
  const oy = plotTop;
  const diag = Math.sqrt(plotWidth ** 2 + plotHeight ** 2);
  const r1 = diag * 0.36;
  const r2 = diag * 0.60;
  const r3 = diag * 0.86;

  return (
    <svg
      style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none", overflow: "visible" }}
      width={svgW}
      height={svgH}
    >
      <defs>
        <clipPath id="zone-clip">
          <rect x={plotLeft} y={plotTop} width={plotWidth} height={plotHeight} />
        </clipPath>
      </defs>
      <g clipPath="url(#zone-clip)">
        <circle cx={ox} cy={oy} r={r3} fill="rgba(187,247,208,0.35)" />
        <circle cx={ox} cy={oy} r={r2} fill="rgba(134,239,172,0.45)" />
        <circle cx={ox} cy={oy} r={r1} fill="rgba(74,222,128,0.60)" />
        <text x={ox - r1 * 0.42} y={oy + r1 * 0.38}
          fontSize="11" fontWeight="700" fill="#15803d"
          textAnchor="middle" fontFamily="Pretendard, sans-serif">
          핵심 이슈
        </text>
        <text x={ox - r2 * 0.54} y={oy + r2 * 0.42}
          fontSize="10" fontWeight="600" fill="#166534"
          textAnchor="middle" opacity="0.85" fontFamily="Pretendard, sans-serif">
          보고 이슈
        </text>
        <text x={ox - r3 * 0.62} y={oy + r3 * 0.50}
          fontSize="10" fontWeight="600" fill="#166534"
          textAnchor="middle" opacity="0.55" fontFamily="Pretendard, sans-serif">
          잠재적 이슈
        </text>
      </g>
    </svg>
  );
};

/** Recharts scatter shape — 순위 번호를 원형 배지로 표시하는 커스텀 도트 */
const RankedDot = (props) => {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  const bg = CAT_CONFIG[payload.cat]?.bg ?? "rgba(148,163,184,0.9)";
  return (
    <g style={{ filter: "drop-shadow(0 2px 5px rgba(0,0,0,0.22))" }}>
      <circle cx={cx} cy={cy} r={16} fill={bg} opacity={0.18} />
      <circle cx={cx} cy={cy} r={13} fill={bg} stroke="#fff" strokeWidth={2.5} />
      <text x={cx} y={cy}
        textAnchor="middle" dominantBaseline="central"
        fontSize="11" fontWeight="800" fill="#fff"
        fontFamily="Pretendard, sans-serif">
        {payload.rank}
      </text>
    </g>
  );
};

/** 이슈 호버 시 재무/영향 중요성 레벨을 표시하는 커스텀 툴팁 */
const MatrixTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d?.label) return null;

  const lvl = (v) => (v < 4 ? "Low" : v < 7 ? "Middle" : "High");
  const cfg = CAT_CONFIG[d.cat] ?? { bg: "rgba(148,163,184,0.9)", badge: { bg: "#f1f5f9", color: "#475569" } };

  return (
    <div className="matrix-tooltip">
      <div className="matrix-tooltip-header">
        <span className="matrix-tooltip-rank" style={{ background: cfg.bg }}>
          {d.rank}
        </span>
        <span className="matrix-tooltip-name">{d.label}</span>
        <span className="matrix-tooltip-cat-badge" style={{ background: cfg.badge.bg, color: cfg.badge.color }}>
          {d.cat}
        </span>
      </div>
      <div className="matrix-tooltip-meta">
        <div>재무중요성: <strong style={{ color: "#1e293b" }}>{lvl(d.x)}</strong></div>
        <div>영향중요성: <strong style={{ color: "#1e293b" }}>{lvl(d.y)}</strong></div>
      </div>
    </div>
  );
};

/** 이중 중대성 매트릭스 차트 — scatter plot + 구역 오버레이 + 이슈 그리드 */
const DoubleMaterialityMatrix = ({ data = [] }) => {
  const [hoveredKey, setHoveredKey] = useState(null);
  const chartWrapRef = useRef(null);

  const activeCats = Object.keys(CAT_CONFIG).filter((cat) =>
    data.some((p) => p.cat === cat)
  );

  const allX = data.map((p) => p.x).filter((v) => v != null);
  const allY = data.map((p) => p.y).filter((v) => v != null);
  const xMin = allX.length ? Math.min(...allX) : 0;
  const xMax = allX.length ? Math.max(...allX) : 10;
  const yMin = allY.length ? Math.min(...allY) : 0;
  const yMax = allY.length ? Math.max(...allY) : 10;
  const xPad = Math.max((xMax - xMin) * 0.3, 0.8);
  const yPad = Math.max((yMax - yMin) * 0.3, 0.8);
  const xDomain = [Math.max(0, xMin - xPad), Math.min(10, xMax + xPad)];
  const yDomain = [Math.max(0, yMin - yPad), Math.min(10, yMax + yPad)];
  const HIGH = 7.0;

  return (
    <div className="dmat-wrap">
      <div ref={chartWrapRef} className="dmat-chart-wrap">
        <ZoneOverlay containerRef={chartWrapRef} />
        <div className="dmat-chart-wrap">
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ top: 16, right: 28, bottom: 44, left: 20 }}>
              <ReferenceArea x1={HIGH} x2={xDomain[1]} y1={HIGH} y2={yDomain[1]} fill="rgba(239,68,68,0.08)" />
              <ReferenceArea x1={xDomain[0]} x2={HIGH} y1={HIGH} y2={yDomain[1]} fill="rgba(245,158,11,0.08)" />
              <ReferenceArea x1={HIGH} x2={xDomain[1]} y1={yDomain[0]} y2={HIGH} fill="rgba(59,130,246,0.08)" />
              <ReferenceArea x1={xDomain[0]} x2={HIGH} y1={yDomain[0]} y2={HIGH} fill="rgba(148,163,184,0.08)" />

              <ReferenceLine x={HIGH} stroke="#94a3b8" strokeDasharray="6 5" strokeWidth={1.5} />
              <ReferenceLine y={HIGH} stroke="#94a3b8" strokeDasharray="6 5" strokeWidth={1.5} />

              <XAxis
                type="number"
                dataKey="x"
                domain={xDomain}
                ticks={[HIGH]}
                tickFormatter={() => "High (≥7)"}
                label={{
                  value: "Financial Materiality (재무중요성)",
                  position: "insideBottom", offset: -30,
                  fontSize: 11, fontWeight: 700,
                  fill: "#475569", fontFamily: "Pretendard, sans-serif",
                }}
                tick={{ fontSize: 11, fill: "#64748b", fontFamily: "Pretendard, sans-serif" }}
                axisLine={{ stroke: "#cbd5e1" }}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={yDomain}
                ticks={[HIGH]}
                tickFormatter={() => "High (≥7)"}
                label={{
                  value: "Environmental & Social Materiality (영향중요성)",
                  angle: -90, position: "insideLeft", offset: -5,
                  dy: 125,
                  fontSize: 11, fontWeight: 700,
                  fill: "#475569", fontFamily: "Pretendard, sans-serif",
                }}
                tick={{ fontSize: 11, fill: "#64748b", fontFamily: "Pretendard, sans-serif" }}
                axisLine={{ stroke: "#cbd5e1" }}
                tickLine={false}
              />

              <Tooltip content={<MatrixTooltip />} cursor={false} isAnimationActive={false} />

              {activeCats.map((cat) => (
                <Scatter
                  key={cat}
                  name={CAT_CONFIG[cat].label}
                  data={data.filter((p) => p.cat === cat)}
                  shape={<RankedDot />}
                  fill={CAT_CONFIG[cat].bg}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="dmat-cat-legend">
        {activeCats.map((cat) => (
          <div key={cat} className="dmat-cat-legend-item">
            <span className="dmat-cat-legend-dot" style={{ background: CAT_CONFIG[cat].bg }} />
            {CAT_CONFIG[cat].label} 선정 이슈
          </div>
        ))}
      </div>

      <div className="dmat-issue-grid">
        {data.slice(0, 10).map((p) => {
          const cfg = CAT_CONFIG[p.cat] ?? { bg: "rgba(148,163,184,0.9)", badge: { bg: "#f1f5f9", color: "#475569" } };
          const key = `${p.cat}-${p.rank}`;
          return (
            <div
              key={key}
              className="dmat-issue-item"
              onMouseEnter={() => setHoveredKey(key)}
              onMouseLeave={() => setHoveredKey(null)}
              style={{ background: hoveredKey === key ? "#f1f5f9" : "transparent" }}
            >
              <span className="dmat-rank-dot" style={{ background: cfg.bg }}>
                {p.rank}
              </span>
              <span className="dmat-issue-label">{p.label}</span>
              <span className="dmat-cat-badge" style={{ background: cfg.badge.bg, color: cfg.badge.color }}>
                {p.cat}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DoubleMaterialityMatrix;
