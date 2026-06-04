import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import Observing from "@assets/icons/result_page/observe.png";
import Chain from "@assets/icons/result_page/valuechain.png";

import "@styles/result.css";
import "@styles/benchmarking.css";
import "@styles/media.css";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ReferenceArea,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ════════════════════════════════════════════════════════════════
// 이중 중대성 매트릭스 — 데이터
// ════════════════════════════════════════════════════════════════

// 카테고리별 색상/라벨 설정 — 새 카테고리 추가 시 여기만 수정
const CAT_CONFIG = {
  E: { label: "환경(E)",      bg: "rgba(34,197,94,0.92)",  badge: { bg: "#dcfce7", color: "#16a34a" } },
  S: { label: "사회(S)",      bg: "rgba(59,130,246,0.92)", badge: { bg: "#dbeafe", color: "#2563eb" } },
  G: { label: "거버넌스(G)",   bg: "rgba(245,43,43,0.88)",  badge: { bg: "#fee2e2", color: "#dc2626" } },
};

// 선정된 이슈 데이터 (x: 재무중요성, y: 영향중요성, 1~3 스케일)
const MATRIX_POINTS = [
  { x: 3,   y: 3,   rank: 1, label: "기후목표·전환계획",  cat: "E" },
  { x: 1,   y: 2,   rank: 2, label: "저탄소·친환경 제품", cat: "E" },
  { x: 2,   y: 1,   rank: 3, label: "교육훈련·역량개발",    cat: "S" },
  { x: 2,   y: 2,   rank: 4, label: "소비자 건강·제품안전", cat: "S" },
  { x: 2.9, y: 2.8, rank: 5, label: "공급망 감사·시정조치", cat: "S" },
  { x: 1,   y: 3,   rank: 6, label: "교육훈련·역량개발",    cat: "G" },
  { x: 1.8, y: 1,   rank: 7, label: "소비자 건강·제품안전", cat: "G" },
  { x: 3.9, y: 2.8, rank: 8, label: "공급망 감사·시정조치", cat: "G" },
];

const SELECTED_ISSUES = [
  { name: "기후변화 대응",              candRank: 1,  finalRank: 1,  reason: "양측 점수 High, 규제 및 시장 영향 큼, 이해관계자 관심도 높음" },
  { name: "지배구조 건전성 강화",        candRank: 2,  finalRank: 2,  reason: "재무적 영향 High, 투자자 요구 증가, 거버넌스 핵심 이슈" },
  { name: "공급망 지속가능성 관리",      candRank: 3,  finalRank: 3,  reason: "공급망 리스크 및 평판 영향 큼, 고객 요구 증가" },
  { name: "인재 확보 및 육성",           candRank: 4,  finalRank: 4,  reason: "사회적 영향 High, 인력 경쟁 심화" },
  { name: "그린 제품·서비스 혁신",       candRank: 6,  finalRank: 5,  reason: "기회 요인 크고, 매출 및 시장 확장과 연계" },
  { name: "에너지 효율 및 온실가스 관리", candRank: 5,  finalRank: 6,  reason: "온실가스 감축 목표 연계, 비용 절감 효과" },
  { name: "제품 안전·품질 강화",         candRank: 7,  finalRank: 7,  reason: "고객 신뢰 및 규제 영향 큼" },
  { name: "정보보안 및 데이터 보호",     candRank: 8,  finalRank: 8,  reason: "디지털 전환 가속, 정보보안 리스크 증가" },
  { name: "사업장 안전보건",             candRank: 9,  finalRank: 9,  reason: "임직원 안전과 직결, 규제 및 평판 영향" },
  { name: "생물다양성 보호",             candRank: 12, finalRank: 10, reason: "자연자본 영향 증가, 글로벌 이니셔티브 대응" },
];

const EXCLUDED_ISSUES = [
  { name: "수자원 관리",           candRank: 13, reason: "재무적 영향 Medium 이하, 분석축 반복 관측 부족" },
  { name: "지역사회 투자 및 공헌",  candRank: 18, reason: "사회적 영향은 있으나, 전략적 연계성 낮음" },
  { name: "폐기물 및 순환경제",    candRank: 21, reason: "영향도는 있으나, 우선순위 상대적으로 낮음" },
  { name: "동물복지",              candRank: 24, reason: "가치사슬 관련성 낮고, 이해관계자 관심도 낮음" },
  { name: "정치자금 및 로비 활동", candRank: 28, reason: "분석축 반복 관측 부족, 리스크 영향 낮음" },
];


// ════════════════════════════════════════════════════════════════
// 이중 중대성 매트릭스 — 서브 컴포넌트
// ════════════════════════════════════════════════════════════════

// 1. 동심원 배경 오버레이
//    chartRef로 컨테이너 크기를 직접 측정 → SVG를 absolute로 오버레이
//    Recharts Customized의 xAxisMap 방식보다 버전 무관하게 안정적
const ZoneOverlay = ({ containerRef }) => {
  const [dims, setDims] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 차트 내부 플롯 영역(recharts-plot-surface 또는 .recharts-cartesian-grid rect)을 찾아 좌표 추출
    const measure = () => {
      const wrap = containerRef.current;
      if (!wrap) return;
      const svg  = wrap.querySelector("svg.recharts-surface");
      const grid = wrap.querySelector(".recharts-cartesian-grid rect");
      if (!svg || !grid) return;

      const svgRect  = svg.getBoundingClientRect();
      const gridRect = grid.getBoundingClientRect();

      setDims({
        // SVG 전체 크기
        svgW: svgRect.width,
        svgH: svgRect.height,
        // 플롯 영역의 SVG 내 상대 좌표
        plotLeft:   gridRect.left   - svgRect.left,
        plotTop:    gridRect.top    - svgRect.top,
        plotWidth:  gridRect.width,
        plotHeight: gridRect.height,
      });
    };

    // 첫 측정 (약간 지연: 차트 렌더 완료 후)
    const t = setTimeout(measure, 60);

    // 리사이즈 대응
    const ro = new ResizeObserver(measure);
    ro.observe(containerRef.current);

    return () => { clearTimeout(t); ro.disconnect(); };
  }, [containerRef]);

  if (!dims) return null;

  const { svgW, svgH, plotLeft, plotTop, plotWidth, plotHeight } = dims;

  // 동심원 원점: 플롯 우측 상단 (High-High 코너)
  const ox   = plotLeft + plotWidth;
  const oy   = plotTop;
  const diag = Math.sqrt(plotWidth ** 2 + plotHeight ** 2);

  // 반지름 비율 (핵심/보고/잠재)
  const r1 = diag * 0.36;
  const r2 = diag * 0.60;
  const r3 = diag * 0.86;

  return (
    // SVG를 차트 컨테이너에 absolute로 오버레이 — pointer-events:none 으로 상호작용 통과
    <svg
      style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none", overflow: "visible" }}
      width={svgW}
      height={svgH}
    >
      <defs>
        {/* 플롯 영역 밖으로 원이 삐져나오지 않게 클리핑 */}
        <clipPath id="zone-clip">
          <rect x={plotLeft} y={plotTop} width={plotWidth} height={plotHeight} />
        </clipPath>
      </defs>
      <g clipPath="url(#zone-clip)">
        {/* 잠재 이슈 — 가장 연함 */}
        <circle cx={ox} cy={oy} r={r3} fill="rgba(187,247,208,0.35)" />
        {/* 보고 이슈 */}
        <circle cx={ox} cy={oy} r={r2} fill="rgba(134,239,172,0.45)" />
        {/* 핵심 이슈 — 가장 진함 */}
        <circle cx={ox} cy={oy} r={r1} fill="rgba(74,222,128,0.60)" />

        {/* 구역 텍스트 라벨 */}
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

// 2. 선정 이슈 번호 도트 — CAT_CONFIG에서 색상 조회
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




// 3. 커스텀 툴팁 — 회색 점(label 없음)은 미표시
const MatrixTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d?.label) return null;

  const lvl = (v) => (v < 1.5 ? "Low" : v < 2.5 ? "Middle" : "High");
  const cfg = CAT_CONFIG[d.cat] ?? { bg: "rgba(148,163,184,0.9)", badge: { bg: "#f1f5f9", color: "#475569" } };

  return (
    <div style={{
      background: "#fff", border: "1px solid #e2e8f0", borderRadius: "10px",
      padding: "10px 14px", fontSize: "12px", fontFamily: "Pretendard, sans-serif",
      boxShadow: "0 4px 16px rgba(0,0,0,0.10)", minWidth: "190px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
        <span style={{
          width: "24px", height: "24px", borderRadius: "50%", background: cfg.bg,
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontWeight: 800, fontSize: "11px", flexShrink: 0,
        }}>
          {d.rank}
        </span>
        <span style={{ fontWeight: 700, color: "#1e293b" }}>{d.label}</span>
        <span style={{
          padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700,
          background: cfg.badge.bg, color: cfg.badge.color, marginLeft: "auto",
        }}>
          {d.cat}
        </span>
      </div>
      <div style={{ display: "flex", gap: "14px", color: "#64748b", fontSize: "11px" }}>
        <div>재무중요성: <strong style={{ color: "#1e293b" }}>{lvl(d.x)}</strong></div>
        <div>영향중요성: <strong style={{ color: "#1e293b" }}>{lvl(d.y)}</strong></div>
      </div>
    </div>
  );
};

// ════════════════════════════════════════════════════════════════
// 이중 중대성 매트릭스 — 메인 컴포넌트
// ════════════════════════════════════════════════════════════════
const DoubleMaterialityMatrix = () => {
  const [hoveredKey, setHoveredKey] = useState(null);
  const chartWrapRef = useRef(null); // 배경 오버레이용 컨테이너 ref

  // 실제 데이터에 있는 카테고리만 렌더링 (CAT_CONFIG 선언 순서 유지)
  const activeCats = Object.keys(CAT_CONFIG).filter((cat) =>
    MATRIX_POINTS.some((p) => p.cat === cat)
  );

  return (
    <div style={{ fontFamily: "Pretendard, sans-serif" }}>

      {/* 차트 래퍼 — position:relative 필수 (ZoneOverlay absolute 기준점) */}
      <div ref={chartWrapRef} style={{ position: "relative" }}>
        {/* 동심원 배경 SVG 오버레이 */}
        <ZoneOverlay containerRef={chartWrapRef} />
        <div style={{ position: "relative" }}>
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 16, right: 28, bottom: 44, left: 20 }}>
             {/* 우상단: High Financial + High Impact (빨강) */}
              <ReferenceArea x1={2.35} x2={4.2} y1={2} y2={3.5} fill="rgba(239,68,68,0.08)" />   

              {/* 좌상단: Low Financial + High Impact (주황) */}
              <ReferenceArea x1={0.5} x2={2.35} y1={2} y2={3.5} fill="rgba(245,158,11,0.08)" />

              {/* 우하단: High Financial + Low Impact (파랑) */}
              <ReferenceArea x1={2.35} x2={4.2} y1={0.5} y2={2} fill="rgba(59,130,246,0.08)" />

              {/* 좌하단: Low Financial + Low Impact (회색) */}
              <ReferenceArea x1={0.5} x2={2.35} y1={0.5} y2={2} fill="rgba(148,163,184,0.08)" />  
            <ReferenceLine
              x={2.35}
              stroke="#94a3b8"
              strokeDasharray="6 5"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />
            <ReferenceLine
              y={2}
              stroke="#94a3b8"
              strokeDasharray="6 5"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />

              

            {/* 좌하단 모서리 Low 라벨 */}
              <ReferenceLine
                x={0.5}
                stroke="transparent"
                label={{
                  value: "Low",
                  position: "insideBottomLeft",
                  fontSize: 12,
                  fill: "#64748b",
                  fontFamily: "Pretendard, sans-serif",
                }}
              />



            {/* X축: 재무중요성 */}
            <XAxis
              type="number"
              dataKey="x"
              domain={[0.5, 4.2]}
              ticks={[2.35, 4.2]}
              tickFormatter={(v) => v < 3 ? "Middle" : "High"}
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

            {/* Y축: 영향중요성 */}
            <YAxis
              type="number"
              dataKey="y"
              domain={[0.5, 3.5]}
              ticks={[1, 2, 3]}
              tickFormatter={(v) => ({ 2: "Middle", 3: "High" }[v] ?? "")}
              label={{
                value: "Environmental & Social Materiality (영향중요성)",
                angle: -90, position: "insideLeft", offset: -5,
                dy:125,
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
                data={MATRIX_POINTS.filter((p) => p.cat === cat)}
                shape={<RankedDot />}
                fill={CAT_CONFIG[cat].bg}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
        </div>
      </div>

      {/* 하단 범례 */}
      <div style={{ display: "flex", gap: "20px", justifyContent: "center", marginTop: "4px", flexWrap: "wrap" }}>
        
        {activeCats.map((cat) => (
          <div key={cat} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#475569" }}>
            <span style={{ width: "12px", height: "12px", borderRadius: "50%", background: CAT_CONFIG[cat].bg, display: "inline-block" }} />
            {CAT_CONFIG[cat].label} 선정 이슈
          </div>
        ))}
      </div>

      {/* 선정 이슈 목록 */}
      <div style={{ marginTop: "14px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "4px 14px" }}>
        {MATRIX_POINTS.map((p) => {
          const cfg = CAT_CONFIG[p.cat] ?? { bg: "rgba(148,163,184,0.9)", badge: { bg: "#f1f5f9", color: "#475569" } };
          const key = `${p.cat}-${p.rank}`;
          return (
            <div
              key={key}
              onMouseEnter={() => setHoveredKey(key)}
              onMouseLeave={() => setHoveredKey(null)}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                fontSize: "12px", color: "#334155", padding: "5px 7px", borderRadius: "7px",
                background: hoveredKey === key ? "#f1f5f9" : "transparent",
                transition: "background 0.15s", cursor: "default",
              }}
            >
              <span style={{
                width: "22px", height: "22px", borderRadius: "50%", background: cfg.bg,
                color: "#fff", fontSize: "10px", fontWeight: 800,
                display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}>
                {p.rank}
              </span>
              <span style={{ fontWeight: 600, flex: 1 }}>{p.label}</span>
              <span style={{ padding: "1px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700, background: cfg.badge.bg, color: cfg.badge.color }}>
                {p.cat}
              </span>
            </div>
          );
        })}
      </div>

    </div>
  );
};

const CONTRIBUTION_DATA = [
  { rank: 1, rankColor: "#22c55e", name: "기후변화 대응",     bench: 45, media: 30, survey: 25 },
  { rank: 2, rankColor: "#f59e0b", name: "에너지 전환",       bench: 30, media: 20, survey: 50 },
  { rank: 3, rankColor: "#22c55e", name: "인적자본 개발",     bench: 25, media: 15, survey: 60 },
  { rank: 4, rankColor: "#f59e0b", name: "공급망 ESG 관리",   bench: 40, media: 25, survey: 35 },
  { rank: 5, rankColor: "#f59e0b", name: "제품 안전 및 품질", bench: 20, media: 30, survey: 50 },
];

const BLIND_SPOTS = [
  { rank: 1, rankColor: "#22c55e", name: "생물다양성 보호",   desc: "이해관계자(설문) 관심은 높으나, 외부 미디어 및 벤치마킹 반영 낮음", badge: "설문-벤치 격차 +1.8",  badgeBg: "#dcfce7", badgeColor: "#16a34a" },
  { rank: 2, rankColor: "#f59e0b", name: "데이터 프라이버시", desc: "미디어에서 주목도 높으나, 이해관계자 관심 및 벤치마킹 낮음",       badge: "미디어-설문 격차 +1.6", badgeBg: "#fef3c7", badgeColor: "#d97706" },
  { rank: 3, rankColor: "#3b82f6", name: "수자원 관리",       desc: "벤치마킹 반영도는 높으나, 이해관계자 관심 미흡",                   badge: "벤치-설문 격차 +1.2",   badgeBg: "#dbeafe", badgeColor: "#2563eb" },
];

const MATRIX_ZONES = [
  { label: "High - High 영역",               labelColor: "#ef4444", bg: "#fff5f5", border: "#fecaca",
    desc: "재무적 영향과 사회/환경적 영향이 모두 높은 핵심 이슈입니다. 최우선 대응 및 전략 자원 집중이 필요합니다." },
  { label: "High Impact / Medium Financial", labelColor: "#d97706", bg: "#fffbeb", border: "#fed7aa",
    desc: "사회-환경적 영향은 크지만 재무적 영향은 중간 수준입니다. 이해관계자 기대 관리 및 선제적 대응으로 리스크를 완화하세요." },
  { label: "High Financial / Medium Impact", labelColor: "#2563eb", bg: "#eff6ff", border: "#bfdbfe",
    desc: "재무적 영향은 크지만 사회-환경적 영향은 중간 수준입니다. 재무 리스크 관리와 함께 영향 개선을 병행하세요." },
];

const PRIORITY_ITEMS = [
  { rank: "1순위", color: "#ef4444", name: "기후변화 대응",            score: "4.6" },
  { rank: "2순위", color: "#f97316", name: "지속가능한 공급망 관리",    score: "4.3" },
  { rank: "3순위", color: "#f59e0b", name: "정보보호 및 데이터 보안",   score: "4.1" },
  { rank: "4순위", color: "#22c55e", name: "인재 육성 및 역량 강화",     score: "3.8" },
  { rank: "5순위", color: "#3b82f6", name: "친환경 제품 및 서비스 확대", score: "3.6" },
];

const ONBOARDING_ROWS = [
  { name: "기후변화 대응",             e: true,  s: true,  g: false, count: "8개", done: "3/8", doneColor: "#ef4444" },
  { name: "지속가능한 공급망 관리",     e: false, s: true,  g: true,  count: "6개", done: "2/6", doneColor: "#ef4444" },
  { name: "정보보호 및 데이터 보안",    e: false, s: false, g: true,  count: "5개", done: "1/5", doneColor: "#ef4444" },
  { name: "인재 육성 및 역량 강화",     e: false, s: true,  g: false, count: "6개", done: "4/6", doneColor: "#475569" },
  { name: "친환경 제품 및 서비스 확대", e: true,  s: false, g: false, count: "5개", done: "2/5", doneColor: "#ef4444" },
];

const MISSING_DATA_ROWS = [
  { name: "온실가스 배출량 (Scope 1,2,3)", missing: "Scope 3 카테고리 11, 12, 15", pct: "60", barColor: "#22c55e" },
  { name: "용수 사용량 및 재활용률",        missing: "사업장별 용수 사용량",        pct: "40", barColor: "#ef4444" },
  { name: "공급망 ESG 평가 비율",          missing: "1차 협력사 평가 데이터",       pct: "50", barColor: "#f59e0b" },
  { name: "정보보호 사고 건수",            missing: "연도별 사고 유형 및 건수",     pct: "30", barColor: "#ef4444" },
];

const SCATTER_TABLE_ROWS = [
  { rank: 1, cat: "E", name: "기후목표·전환계획",    type: "위기", period: "장기", fin: "3", impact: "3" },
  { rank: 2, cat: "E", name: "저탄소·친환경 제품",   type: "기회", period: "단기", fin: "2", impact: "3" },
  { rank: 3, cat: "S", name: "교육훈련·역량개발",    type: "위기", period: "장기", fin: "2", impact: "2" },
  { rank: 4, cat: "S", name: "소비자 건강·제품안전", type: "기회", period: "장기", fin: "2", impact: "1" },
  { rank: 5, cat: "S", name: "공급망 감사·시정조치", type: "위기", period: "단기", fin: "1", impact: "2" },
];

// ════════════════════════════════════════════════════════════════
// 중요도(Low/Middle/High) 배지 시스템
// ════════════════════════════════════════════════════════════════
const IMPORTANCE_LEVELS = {
  1: { text: "Low",    color: "#64748b", bg: "#f1f5f9" },
  2: { text: "Middle", color: "#d97706", bg: "#fffbeb" },
  3: { text: "High",   color: "#ef4444", bg: "#fff5f5" },
  low:    { text: "Low",    color: "#64748b", bg: "#f1f5f9" },
  medium: { text: "Middle", color: "#d97706", bg: "#fffbeb" },
  high:   { text: "High",   color: "#ef4444", bg: "#fff5f5" },
  기회 :   { text: "기회",    color: "#22c55e", bg: "#f1f5f9" },
  위기 :   { text: "위기",    color: "#ef4444", bg: "#f1f5f9" },
  장기 :   { text: "위기",    color: "#64748b", bg: "#f1f5f9" },
  단기 :   { text: "위기",    color: "#d97706", bg: "#f1f5f9" },
  
};

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

const LEVEL_COLORS = {
  1: "#1e293b",
  2: "#1e293b",
  3: "#1e293b",
};

const ImportanceBadge = ({ value }) => {
  const key = normalizeImportance(value);
  const filled = typeof key === "number" ? key : 0;
  const color = LEVEL_COLORS[filled] ?? "#94a3b8";

  return (
    <span style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            display: "inline-block",
            backgroundColor: i <= filled ? color : "transparent",
            border: `2px solid ${color}`,
          }}
        />
      ))}
    </span>
  );
};

const Result = () => {
  const navigate = useNavigate();
  const activeIndex = 3;

  const steps = [
    { id: 1, title: "벤치마킹 분석",   icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7"/><line x1="15.5" y1="15.5" x2="21" y2="21"/><line x1="7" y1="13" x2="7" y2="11"/><line x1="10" y1="13" x2="10" y2="8.5"/><line x1="13" y1="13" x2="13" y2="7"/><line x1="6" y1="13" x2="14" y2="13"/></svg>, path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/><polyline points="5,13 8,10 11,12 14,8 19,6"/></svg>, path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><polyline points="9,11 10.5,12.5 13,10"/><polyline points="9,16 10.5,17.5 13,15"/><line x1="13" y1="11" x2="16" y2="11"/><line x1="13" y1="16" x2="16" y2="16"/></svg>, path: "/survey" },
    { id: 4, title: "전체 결과", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="20" x2="21" y2="20"/><line x1="3" y1="4" x2="3" y2="20"/><rect x="5" y="13" width="3" height="7"/><rect x="10" y="10" width="3" height="10"/><rect x="15" y="8" width="3" height="12"/><circle cx="19" cy="4" r="3"/><polyline points="17.5,4 18.5,5 21,2.5"/></svg>, path: "/result" },
    { id: 5, title: "보고서 초안", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/></svg>, path: "/draft" },

  ];

  const [leftTab, setLeftTab]           = useState(0);
  const [rightTab, setRightTab]         = useState(0);
  const [openSections, setOpenSections] = useState({ 1: true, 2: true });

 
  const particleRef      = useRef(null);

  useEffect(() => {
    createParticles();
  }, []);

  const createParticles = () => {
    if (!particleRef.current) return;
    particleRef.current.innerHTML = "";
    for (let i = 0; i < 12; i++) {
      const p = document.createElement("div");
      p.className = "particle";
      const size = Math.random() * 5 + 3;
      p.style.width  = `${size}px`;
      p.style.height = `${size}px`;
      p.style.left   = `${Math.random() * 100}%`;
      p.style.top    = `${Math.random() * 100}%`;
      p.style.animationDelay = `${Math.random() * 2}s`;
      particleRef.current.appendChild(p);
    }
  };


  const moveStep = (index) => {
    if (index === activeIndex) return;
    navigate(steps[index].path);
  };

  const toggleSection = (id) => {
    setOpenSections(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="sr-container">
      <header className="sr-header">
        
        <div className="sr-stepper-row">
          {steps.map((step, index) => (
            <div key={step.id} style={{ display: "flex", alignItems: "center" }}>
              <div className={`step-box ${index === activeIndex ? "active" : ""}`} onClick={() => moveStep(index)}>
                <div className="step-icon-circle">{step.icon}</div>
                <div style={{ fontSize: "0.8rem", fontWeight: 850 }}>{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line"></div>}
            </div>
          ))}
        </div>
      </header>

      <main id="result-main" className="main-content">
        <div id="result-panels-wrap">

          {/* ── 왼쪽 패널 ── */}
          <section id="result-left-panel">
            <div className="result-tab-bar">
              {["최종선정요약","후보군 최종선정 과정", "점수 해석", "다음 단계 연결"].map((label, i) => (
                <button
                  key={i}
                  className={`result-tab-button ${leftTab === i ? "active" : ""}`}
                  onClick={() => setLeftTab(i)}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* 탭 0: 최종선정요약 */}
            {leftTab === 0 && (
              <div className="result-tab-pane">
                {/* 최종 선정 요약 */}
                <div className="card-container">
                  <div className="card-title-row">
                    <span className="card-title">최종 선정 요약</span>
                    
                  </div>
                  <div id="result-summary-grid" className="summary-grid">
                    {[
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>, label: "평가 대상", value: "62개", cls: "" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/></svg>, label: "최종 선정", value: "10개", cls: "success", valueClass: "text-green" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.8"><polyline points="17 11 12 6 7 11"/><polyline points="17 18 12 13 7 18"/></svg>, label: "High 영역", value: "5개", cls: "danger", valueClass: "text-red" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>, label: "후보군", value: "25개", cls: "" },
                    ].map((card, i) => (
                      <div key={i} className={`info-card ${card.cls}`}>
                        {card.icon}
                        <div className="card-label">{card.label}</div>
                        <div className={`card-value ${card.valueClass || ""}`}>{card.value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 최종 Top 이슈 점수 분해 */}
                <div className="card-container">
                  <div className="card-title">최종 Top 이슈 점수 분해</div>
                  <table className="result-table">
                    <thead>
                      <tr><th>이슈</th><th>최종점수</th><th>영향</th><th>재무</th><th>벤치마킹</th><th>미디어</th><th>설문</th></tr>
                    </thead>
                    <tbody>
                      <tr><td className="issue-name">기후변화 대응</td><td className="score-main">4.61</td><td>4.40</td><td>4.75</td><td>4.20</td><td>4.60</td><td>4.70</td></tr>
                      <tr><td className="issue-name">에너지 관리</td><td className="score-highlight">4.34</td><td>4.10</td><td>4.50</td><td>4.00</td><td>4.30</td><td>4.40</td></tr>
                    </tbody>
                  </table>
                </div>

                {/* 선정 사유 요약 */}
                <div className="card-container">
                  <div className="card-title">선정 사유 요약</div>
                  <div id="result-reason-list">
                    {[
                      { bg: "#f0fdf4", title: "영향 및 재무 동시 고점 이슈 우선", desc: "영향 중대성과 재무 중대성 모두 높은 이슈를 우선 최종 선정하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg> },
                      { bg: "#eff6ff", title: "이해관계자 의견 반영", desc: "설문 결과와 주요 이해관계자 인터뷰를 반영하여 중요 이슈를 확정하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg> },
                      { bg: "#f5f3ff", title: "지속가능경영 전략 연계", desc: "기업의 전략 방향 및 리스크/기회 관점에서 관리가 필요한 이슈를 포함하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> },
                    ].map((item, i) => (
                      <div key={i} className="result-reason-row">
                        <div className="result-reason-icon" style={{ background: item.bg }}>{item.icon}</div>
                        <div>
                          <div className="result-reason-title">{item.title}</div>
                          <p className="result-reason-desc">{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          
              {leftTab === 1 && (
              <div className="result-tab-pane" style={{ gap: "24px" }}>

    {/* 후보군 최종 선정 과정 */}
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "24px" }}>
      <div style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b", marginBottom: "20px" }}>후보군 최종 선정 과정</div>
      <div style={{ display: "flex", gap: "24px", alignItems: "flex-start" }}>

        {/* 플로우 카드 */}
        <div style={{ flex: 1.4, display: "flex", flexDirection: "column", gap: 0, alignItems: "stretch" }}>
          {[
            { count: "62개 평가 대상", desc: "벤치마킹, 미디어, 이해관계자 설문을 통해<br>도출된 전체 평가 이슈 수집", last: false,
              icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg> },
            { count: "25개 후보군", desc: "양축 점수 기준 충족 및 주요성 기준을<br>충족한 이슈", last: false,
              icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> },
            { count: "최종 10개 선정", desc: "이사회 및 ESG 실무 협의 기반<br>보고서 핵심 이슈로 최종 선정", last: true,
              icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> },
          ].map((card, i) => (
            <div key={i}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px", background: card.last ? "#f0fdf4" : "#f8fafc", border: `1px solid ${card.last ? "#bbf7d0" : "#e2e8f0"}`, borderRadius: "14px", padding: "18px 20px" }}>
                <div style={{ flexShrink: 0, width: "52px", height: "52px", background: "#dcfce7", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {card.icon}
                </div>
                <div>
                  <div style={{ fontSize: "1.15rem", fontWeight: 850, color: "#03A94D", marginBottom: "4px" }}>{card.count}</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.55 }} dangerouslySetInnerHTML={{ __html: card.desc }} />
                </div>
              </div>
              {!card.last && <div style={{ display: "flex", justifyContent: "center", padding: "6px 0", color: "#03A94D", fontSize: "1.3rem" }}>↓</div>}
            </div>
          ))}
        </div>

        {/* 선정 기준 */}
        <div style={{ flex: 1, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "20px 22px", alignSelf: "stretch", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: "1.5em", fontWeight: 850, color: "#03A94D", marginBottom: "16px" }}>선정 기준</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "14px", flex: 1, justifyContent: "space-between" }}>
            {[
              { icon: <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="4,6 5.5,7.5 8,5"/><line x1="10" y1="6" x2="20" y2="6"/><polyline points="4,12 5.5,13.5 8,11"/><line x1="10" y1="12" x2="20" y2="12"/><polyline points="4,18 5.5,19.5 8,17"/><line x1="10" y1="18" x2="18" y2="18"/></svg>, text: "양측 점수 기준 충족", sub: "(재무적·사회적 영향 모두 Medium 이상)" },
              { icon: <img src={Observing} width="80" height="80" alt="" style={{ objectFit: "contain" }} />, text: "2개 이상 분석축에서 반복 관측" },
              { icon: <img src={Chain} width="45" height="45" alt="" style={{ objectFit: "contain" }} />, text: "가치사슬 관련성 높음" },
              { icon: <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="2"/><circle cx="12" cy="4" r="2"/><circle cx="20" cy="16" r="2"/><circle cx="4" cy="16" r="2"/><line x1="12" y1="6" x2="12" y2="10"/><line x1="18.3" y1="15" x2="13.7" y2="13"/><line x1="5.7" y1="15" x2="10.3" y2="13"/></svg>, text: "이해관계자 관심도 높음" },
              { icon: <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><line x1="12" y1="3" x2="12" y2="21"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>, text: "리스크/기회 요인으로서의 중요성 고려" },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                <div style={{ flexShrink: 0, width: "32px", height: "32px", background: "#dcfce7", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.95rem" }}>{item.icon}</div>
                <div style={{ fontSize: "0.88rem", color: "#334155", lineHeight: 1.6 }}>
                  {item.text}{item.sub && <><br /><span style={{ color: "#64748b" }}>{item.sub}</span></>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>

    {/* 최종 선정 이슈 */}
    <div className="card-container">
      <div style={{ fontSize: "0.95rem", fontWeight: 850, color: "#1e293b", marginBottom: "14px" }}>최종 선정 이슈</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
        <thead>
          <tr style={{ background: "#f8fafc", borderBottom: "1.5px solid #e2e8f0" }}>
            <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 700, color: "#475569", width: "30%" }}>이슈</th>
            <th style={{ padding: "10px 8px", textAlign: "center", fontWeight: 700, color: "#475569", width: "12%" }}>후보순위</th>
            <th style={{ padding: "10px 8px", textAlign: "center", fontWeight: 700, color: "#475569", width: "12%" }}>최종순위</th>
            <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 700, color: "#475569" }}>포함 사유</th>
          </tr>
        </thead>
        <tbody>
          {SELECTED_ISSUES.map((row, i) => (
            <tr key={i} style={{ borderBottom: i < SELECTED_ISSUES.length - 1 ? "1px solid #f1f5f9" : "none" }}>
              <td style={{ padding: "10px 14px", fontWeight: 700, color: "#1e293b" }}>{row.name}</td>
              <td style={{ padding: "10px 8px", textAlign: "center", color: "#64748b" }}>{row.candRank}</td>
              <td style={{ padding: "10px 8px", textAlign: "center", fontWeight: 800, color: "#03A94D" }}>{row.finalRank}</td>
              <td style={{ padding: "10px 14px", color: "#475569" }}>{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {/* 후보였지만 제외된 이슈 */}
    <div className="card-container">
      <div style={{ fontSize: "0.95rem", fontWeight: 850, color: "#ef4444", marginBottom: "14px" }}>후보였지만 제외된 이슈</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
        <thead>
          <tr style={{ background: "#f8fafc", borderBottom: "1.5px solid #e2e8f0" }}>
            <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 700, color: "#475569", width: "30%" }}>이슈</th>
            <th style={{ padding: "10px 8px", textAlign: "center", fontWeight: 700, color: "#475569", width: "12%" }}>후보순위</th>
            <th style={{ padding: "10px 8px", textAlign: "center", fontWeight: 700, color: "#475569", width: "12%" }}>최종순위</th>
            <th style={{ padding: "10px 14px", textAlign: "left", fontWeight: 700, color: "#475569" }}>제외 사유</th>
          </tr>
        </thead>
        <tbody>
          {EXCLUDED_ISSUES.map((row, i) => (
            <tr key={i} style={{ borderBottom: i < EXCLUDED_ISSUES.length - 1 ? "1px solid #f1f5f9" : "none" }}>
              <td style={{ padding: "10px 14px", fontWeight: 700, color: "#1e293b" }}>{row.name}</td>
              <td style={{ padding: "10px 8px", textAlign: "center", color: "#64748b" }}>{row.candRank}</td>
              <td style={{ padding: "10px 8px", textAlign: "center", color: "#94a3b8" }}>-</td>
              <td style={{ padding: "10px 14px", color: "#475569" }}>{row.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

  </div>
)}  
            {/* 탭 1: 점수 해석 */}
            {leftTab === 2 && (
              <div className="card-container result-tab-pane">
                <div className="card-title-row">
                  <span className="card-title">점수 해석</span>
                  {/* <span className="info-mark">ⓘ</span> */}
                </div>

                {/* 1. 분석축 기여도 */}
                <section id="result-contribution">
                  <div className="section-title">1. 분석축 기여도</div>
                  <div className="section-desc">각 주요 이슈 점수에 대한 분석축(벤치마킹/미디어/설문) 기여도를 보여줍니다.</div>
                  <div id="legend-row">
                    {[["#22c55e", "벤치마킹"], ["#3b82f6", "미디어"], ["#f59e0b", "설문"]].map(([color, label]) => (
                      <div key={label} className="legend-item">
                        <span className="legend-dot" style={{ background: color }}></span>{label}
                      </div>
                    ))}
                  </div>
                  <div id="contribution-list">
                    {CONTRIBUTION_DATA.map((item) => (
                      <div key={item.rank} className="contribution-row">
                        <div className="contribution-label">
                          <span className="rank-circle" style={{ background: item.rankColor }}>{item.rank}</span>
                          <span className="contribution-name">{item.name}</span>
                        </div>
                        <div className="contribution-bar">
                          <div className="bar-seg bench"  style={{ width: `${item.bench}%` }}>{item.bench}%</div>
                          <div className="bar-seg media"  style={{ width: `${item.media}%` }}>{item.media}%</div>
                          <div className="bar-seg survey" style={{ width: `${item.survey}%` }}>{item.survey}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* 2. Blind Spot */}
                <section id="result-blind-spot">
                  <div className="section-title">2. 분석축 간 불일치 / Blind Spot</div>
                  <div className="section-desc">분석축 간 점수 편차가 큰 이슈를 확인하여 전략적 블라인드 스팟을 식별합니다.</div>
                  <div id="blind-spot-list">
                    {BLIND_SPOTS.map((item) => (
                      <div key={item.rank} className="blind-spot-row">
                        <span className="rank-circle sm" style={{ background: item.rankColor }}>{item.rank}</span>
                        <div className="blind-spot-info">
                          <div className="blind-spot-name">{item.name}</div>
                          <div className="blind-spot-desc">{item.desc}</div>
                        </div>
                        <span className="blind-spot-badge" style={{ background: item.badgeBg, color: item.badgeColor }}>{item.badge}</span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* 3. 매트릭스 해석 */}
                <section id="result-matrix-zones">
                  <div className="section-title">3. 매트릭스 해석</div>
                  <div className="section-desc">이중 중대성 매트릭스 영역별 의미를 안내합니다.</div>
                  <div id="matrix-zone-list">
                    {MATRIX_ZONES.map((zone, i) => (
                      <div
                        key={i}
                        className="matrix-zone-row"
                        style={{ background: zone.bg, borderColor: zone.border }}
                      >
                        <div className="matrix-zone-label">
                          <span style={{ color: zone.labelColor }}>{zone.label}</span>
                        </div>
                        <div className="matrix-zone-desc" dangerouslySetInnerHTML={{ __html: zone.desc.replace(/\n/g, "<br>") }} />
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}

            {/* 탭 2: 다음 단계 연결 */}
            {leftTab === 3 && (
              <div className="card-container result-tab-pane" id="result-next-steps">
                <div className="card-title">다음 단계 연결</div>

                {/* 섹션 1: 보고서 반영 우선순위 */}
                <div className="accordion">
                  <div className="accordion-head static">
                    <span className="accordion-title">1. 보고서 반영 우선순위</span>
                  </div>
                  <div className="accordion-body" id="priority-body">
                    {PRIORITY_ITEMS.map((item) => (
                      <div key={item.rank} className="priority-row">
                        <span className="priority-name">{item.name}</span>
                        <span className="priority-score">중요도 <strong>{item.score}</strong></span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 섹션 2: 필요 온보딩 지표 */}
                <div className="accordion">
                  <div className="accordion-head static">
                    <span className="accordion-title">2. 필요 온보딩 지표</span>
                  </div>
                  <div className="accordion-body">
                    <table id="onboarding-table">
                        <thead>
                          <tr>
                            {["이슈", "환경(E)", "사회(S)", "지배구조(G)", "필요 지표 수", "온보딩 완료"].map(h => (
                              <th key={h} className={h === "이슈" ? "left" : ""}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {ONBOARDING_ROWS.map((row, i) => (
                            <tr key={i}>
                              <td className="left">{row.name}</td>
                              {[row.e, row.s, row.g].map((v, j) => (
                                <td key={j} className={v ? "check on" : "check off"}>{v ? "✓" : "-"}</td>
                              ))}
                              <td className="muted">{row.count}</td>
                              <td className="done-cell" style={{ color: row.doneColor }}>{row.done}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                </div>

                {/* 섹션 3: 부족 데이터 현황 */}
                <div className="accordion">
                  <div className="accordion-head static">
                    <span className="accordion-title">3. 부족 데이터 현황</span>
                  </div>
                  <div className="accordion-body">
                    <table id="missing-table">
                      <thead>
                        <tr>
                          <th>항목</th>
                          <th>부족 데이터</th>
                          <th>완료율</th>
                        </tr>
                      </thead>
                      <tbody>
                        {MISSING_DATA_ROWS.map((row, i) => (
                          <tr key={i}>
                            <td className="missing-name">{row.name}</td>
                            <td>
                              <span className="missing-data-row">
                                <span className="warn-icon">⚠</span>
                                <span className="missing-text">{row.missing}</span>
                              </span>
                            </td>
                            {/* [TODO-동작] row.pct / row.barColor 로 프로그레스 바 그릴 수 있음 */}
                            <td>
                              <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ flex: 1, height: "8px", borderRadius: "4px", background: "#e5e7eb", overflow: "hidden" }}>
                              <span style={{ display: "block", width: `${row.pct}%`, height: "100%", background: row.barColor, borderRadius: "4px" }} />
                              </span>
                              <span style={{ minWidth: "34px", textAlign: "right", fontWeight: 600, color: row.barColor }}>
                                {row.pct}%
                              </span>
                            </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 섹션 4: 바로가기 */}
                <div className="accordion">
                  <div className="accordion-head static">
                    <span className="accordion-title">4. 바로가기</span>
                  </div>
                  <div id="shortcut-grid">
                    {[
                      { bg: "#dcfce7", title: "온보딩 지표 확인", desc: "지표 정의 및 입력 항목 보기", path: "/onboard",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg> },
                      // { bg: "#dbeafe", title: "부족 데이터 입력", desc: "필요 데이터 입력 및 관리", path: "/onboard",
                      //   icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg> },
                      { bg: "#ede9fe", title: "보고서 초안 생성", desc: "선택 이슈 기반 초안 생성", path: "/draft",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> },
                    ].map((item) => (
                      <div key={item.title} className="shortcut-card" onClick={() => navigate(item.path)}>
                        <div className="shortcut-icon" style={{ background: item.bg }}>{item.icon}</div>
                        <div className="shortcut-text">
                          <div className="shortcut-title">{item.title}</div>
                          <div className="shortcut-desc">{item.desc}</div>
                        </div>
                        
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* ── 오른쪽 패널 ── */}
          <section id="result-right-panel">
          
            {rightTab === 0 && (
              <div className="result-tab-pane">
                <div className="matrix-card">
                  <div id="matrix-card-title">이중 중대성 매트릭스</div>
                  <DoubleMaterialityMatrix />
                </div>
                <div id="table-card">
                  <div style={{ display: "flex", gap: "16px", marginBottom: "10px", fontSize: "0.8rem", color: "#475569", alignItems: "center" }}>
                    {[["Low,", 1], ["Middle,", 2], ["High,", 3]].map(([label, filled]) => (
                      <span key={label} style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                        <span style={{ display: "inline-flex", gap: "3px" }}>
                          {[1, 2, 3].map((i) => (
                            <span key={i} style={{ width: "9px", height: "9px", borderRadius: "50%", display: "inline-block", backgroundColor: i <= filled ? "#1e293b" : "transparent", border: "2px solid #1e293b" }} />
                          ))}
                        </span>
                        <span style={{ fontWeight: 600 }}>{label}</span>
                      </span>
                    ))}
                  </div>
                  <table className="result-table">
                    <thead>
                      <tr><th>순위</th><th>구분</th><th>탑 이슈</th><th>Type</th><th>Period</th><th>재무중요성</th><th>영향중요성</th></tr>
                    </thead>
                    <tbody>
                      {SCATTER_TABLE_ROWS.map((row) => (
                        <tr key={row.rank}>
                          <td className="score-main">{row.rank}</td>
                          <td><span className={`badge badge-${row.cat.toLowerCase()}`}>{row.cat}</span></td>
                          <td className="issue-name">{row.name}</td>
                          <td><span className={row.type === "위기" ? "type-badge-risk" : "type-badge-opp"}>{row.type}</span></td>
                          <td><span className={row.period === "장기" ? "period-badge-long" : "period-badge-short"}>{row.period}</span></td>
                          <td><ImportanceBadge value={row.fin} /></td>
                          <td><ImportanceBadge value={row.impact} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {rightTab === 1 && (
              <div className="result-result-dashboard" id="right-tab-empty">
                <div className="robot-view-container">
                  <div className="particle-field" ref={particleRef}></div>
                  <div className="robot-stage">
                    <div className="robot-float-wrap">
                      <img src={robot} className="robot-main-img" alt="robot" />
                    </div>
                  </div>
                  <h3 id="robot-empty-title">분석 미실행 상태</h3>
                  <p id="robot-empty-desc">하단의 '설문 결과 분석' 버튼을 작동시켜 주십시오.</p>
                </div>
              </div>
            )}
          </section>

        </div>
      </main>
    </div>
  );
};

export default Result;
