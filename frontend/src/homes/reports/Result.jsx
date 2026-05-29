import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/result.css";
import "@styles/benchmarking.css";
import "@styles/media.css";
import robot from "@assets/images/robot/robot_final_t.png";
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);



// ── 스캐터 차트 데이터 ──
const CHART_DATASETS = [
  {
    label: "환경(E)",
    data: [
      { x: 3,   y: 3,   label: "기후목표·전환계획",   rank: 1 },
      { x: 1,   y: 2,   label: "저탄소·친환경 제품",  rank: 2 },
    ],
    backgroundColor: "rgba(34,197,94,0.85)",
    borderColor: "#16a34a",
    borderWidth: 2, pointRadius: 18, pointHoverRadius: 22,
  },
  {
    label: "사회(S)",
    data: [
      { x: 2,   y: 1,   label: "교육훈련·역량개발",     rank: 3 },
      { x: 2,   y: 2,   label: "소비자 건강·제품안전",  rank: 4 },
      { x: 2.9, y: 2.8, label: "공급망 감사·시정조치",  rank: 5 },
    ],
    backgroundColor: "rgba(59,130,246,0.85)",
    borderColor: "#2563eb",
    borderWidth: 2, pointRadius: 18, pointHoverRadius: 22,
  },
];

const SELECTED_ISSUES = [
  { name: "기후변화 대응",        candRank: 1,  finalRank: 1,  reason: "양측 점수 High, 규제 및 시장 영향 큼, 이해관계자 관심도 높음" },
  { name: "지배구조 건전성 강화",  candRank: 2,  finalRank: 2,  reason: "재무적 영향 High, 투자자 요구 증가, 거버넌스 핵심 이슈" },
  { name: "공급망 지속가능성 관리", candRank: 3,  finalRank: 3,  reason: "공급망 리스크 및 평판 영향 큼, 고객 요구 증가" },
  { name: "인재 확보 및 육성",     candRank: 4,  finalRank: 4,  reason: "사회적 영향 High, 인력 경쟁 심화" },
  { name: "그린 제품·서비스 혁신", candRank: 6,  finalRank: 5,  reason: "기회 요인 크고, 매출 및 시장 확장과 연계" },
  { name: "에너지 효율 및 온실가스 관리", candRank: 5, finalRank: 6, reason: "온실가스 감축 목표 연계, 비용 절감 효과" },
  { name: "제품 안전·품질 강화",   candRank: 7,  finalRank: 7,  reason: "고객 신뢰 및 규제 영향 큼" },
  { name: "정보보안 및 데이터 보호", candRank: 8, finalRank: 8, reason: "디지털 전환 가속, 정보보안 리스크 증가" },
  { name: "사업장 안전보건",        candRank: 9,  finalRank: 9,  reason: "임직원 안전과 직결, 규제 및 평판 영향" },
  { name: "생물다양성 보호",        candRank: 12, finalRank: 10, reason: "자연자본 영향 증가, 글로벌 이니셔티브 대응" },
];

const EXCLUDED_ISSUES = [
  { name: "수자원 관리",          candRank: 13, reason: "재무적 영향 Medium 이하, 분석축 반복 관측 부족" },
  { name: "지역사회 투자 및 공헌", candRank: 18, reason: "사회적 영향은 있으나, 전략적 연계성 낮음" },
  { name: "폐기물 및 순환경제",   candRank: 21, reason: "영향도는 있으나, 우선순위 상대적으로 낮음" },
  { name: "동물복지",             candRank: 24, reason: "가치사슬 관련성 낮고, 이해관계자 관심도 낮음" },
  { name: "정치자금 및 로비 활동", candRank: 28, reason: "분석축 반복 관측 부족, 리스크 영향 낮음" },
];

const CONTRIBUTION_DATA = [
  { rank: 1, rankColor: "#22c55e", name: "기후변화 대응",  bench: 45, media: 30, survey: 25 },
  { rank: 2, rankColor: "#f59e0b", name: "에너지 전환",    bench: 30, media: 20, survey: 50 },
  { rank: 3, rankColor: "#22c55e", name: "인적자본 개발",  bench: 25, media: 15, survey: 60 },
  { rank: 4, rankColor: "#f59e0b", name: "공급망 ESG 관리", bench: 40, media: 25, survey: 35 },
  { rank: 5, rankColor: "#f59e0b", name: "제품 안전 및 품질", bench: 20, media: 30, survey: 50 },
];

const BLIND_SPOTS = [
  { rank: 1, rankColor: "#22c55e", name: "생물다양성 보호", desc: "이해관계자(설문) 관심은 높으나, 외부 미디어 및 벤치마킹 반영 낮음",  badge: "설문-벤치 격차 +1.8", badgeBg: "#dcfce7", badgeColor: "#16a34a" },
  { rank: 2, rankColor: "#f59e0b", name: "데이터 프라이버시", desc: "미디어에서 주목도 높으나, 이해관계자 관심 및 벤치마킹 낮음",        badge: "미디어-설문 격차 +1.6", badgeBg: "#fef3c7", badgeColor: "#d97706" },
  { rank: 3, rankColor: "#3b82f6", name: "수자원 관리",      desc: "벤치마킹 반영도는 높으나, 이해관계자 관심 미흡",                    badge: "벤치-설문 격차 +1.2",  badgeBg: "#dbeafe", badgeColor: "#2563eb" },
];

const MATRIX_ZONES = [
  { label: "High - High 영역",              labelColor: "#ef4444", bg: "#fff5f5", border: "#fecaca",
    desc: "재무적 영향과 사회/환경적 영향이 모두 높은 핵심 이슈입니다. 최우선 대응 및 전략 자원 집중이 필요합니다." },
  { label: "High Impact / Medium Financial", labelColor: "#d97706", bg: "#fffbeb", border: "#fed7aa",
    desc: "사회-환경적 영향은 크지만 재무적 영향은 중간 수준입니다. 이해관계자 기대 관리 및 선제적 대응으로 리스크를 완화하세요." },
  { label: "High Financial / Medium Impact", labelColor: "#2563eb", bg: "#eff6ff", border: "#bfdbfe",
    desc: "재무적 영향은 크지만 사회-환경적 영향은 중간 수준입니다. 재무 리스크 관리와 함께 영향 개선을 병행하세요." },
];

const PRIORITY_ITEMS = [
  { rank: "1순위", color: "#ef4444", name: "기후변화 대응",         score: "4.6" },
  { rank: "2순위", color: "#f97316", name: "지속가능한 공급망 관리", score: "4.3" },
  { rank: "3순위", color: "#f59e0b", name: "정보보호 및 데이터 보안", score: "4.1" },
  { rank: "4순위", color: "#22c55e", name: "인재 육성 및 역량 강화",  score: "3.8" },
  { rank: "5순위", color: "#3b82f6", name: "친환경 제품 및 서비스 확대", score: "3.6" },
];

const ONBOARDING_ROWS = [
  { name: "기후변화 대응",           e: true,  s: true,  g: false, count: "8개", done: "3/8",  doneColor: "#ef4444" },
  { name: "지속가능한 공급망 관리",   e: false, s: true,  g: true,  count: "6개", done: "2/6",  doneColor: "#ef4444" },
  { name: "정보보호 및 데이터 보안",  e: false, s: false, g: true,  count: "5개", done: "1/5",  doneColor: "#ef4444" },
  { name: "인재 육성 및 역량 강화",   e: false, s: true,  g: false, count: "6개", done: "4/6",  doneColor: "#475569" },
  { name: "친환경 제품 및 서비스 확대", e: true, s: false, g: false, count: "5개", done: "2/5", doneColor: "#ef4444" },
];

const MISSING_DATA_ROWS = [
  { name: "온실가스 배출량 (Scope 1,2,3)", missing: "Scope 3 카테고리 11, 12, 15",  pct: 60, barColor: "#22c55e" },
  { name: "용수 사용량 및 재활용률",        missing: "사업장별 용수 사용량",         pct: 40, barColor: "#ef4444" },
  { name: "공급망 ESG 평가 비율",          missing: "1차 협력사 평가 데이터",        pct: 50, barColor: "#f59e0b" },
  { name: "정보보호 사고 건수",            missing: "연도별 사고 유형 및 건수",       pct: 30, barColor: "#ef4444" },
];

const SCATTER_TABLE_ROWS = [
  { rank: 1, cat: "E", name: "기후목표·전환계획",   type: "위기", period: "장기", fin: "재무중요성", impact: "영향중요성" },
  { rank: 2, cat: "E", name: "저탄소·친환경 제품",  type: "기회", period: "단기", fin: "⚫⚪⚪",  impact: "⚫⚫⚪" },
  { rank: 3, cat: "S", name: "교육훈련·역량개발",   type: "위기", period: "장기", fin: "⚫⚫⚪",  impact: "⚫⚪⚪" },
  { rank: 4, cat: "S", name: "소비자 건강·제품안전", type: "기회", period: "장기", fin: "⚫⚫⚪",  impact: "⚫⚫⚪" },
  { rank: 5, cat: "S", name: "공급망 감사·시정조치", type: "위기", period: "단기", fin: "⚫⚫⚫",  impact: "⚫⚫⚫" },
];

const Result = () => {
  const navigate = useNavigate();
  const activeIndex = 3;

  const steps = [
    { id: 1, title: "벤치마킹 분석",  icon: "🎯", path: "/benchmk" },
    { id: 2, title: "미디어 분석",     icon: "📺", path: "/media"   },
    { id: 3, title: "이해관계자 설문", icon: "👥", path: "/survey"  },
    { id: 4, title: "전체 결과",       icon: "📊", path: "/result"  },
    { id: 5, title: "보고서 초안",     icon: "📄", path: "/draft"   },
  ];

  const [leftTab, setLeftTab]         = useState(0);
  const [rightTab, setRightTab]       = useState(0);
  const [openSections, setOpenSections] = useState({ 1: true, 2: true });

  const chartCanvasRef    = useRef(null);
  const chartInstanceRef  = useRef(null);
  const particleRef       = useRef(null);

  useEffect(() => {
    createParticles();
    initChart();
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
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

  const initChart = () => {
    if (!chartCanvasRef.current) return;
    const ctx = chartCanvasRef.current.getContext("2d");

    const quadrantPlugin = {
      id: "quadrantBg",
      beforeDraw(chart) {
        const { ctx: c, chartArea: { left, right, top, bottom, width, height } } = chart;
        const midX = left + width / 2;
        const midY = top + height / 2;
        c.save();
        c.fillStyle = "rgba(239,68,68,0.08)";  c.fillRect(midX, top,  right - midX, midY - top);
        c.fillStyle = "rgba(148,163,184,0.08)"; c.fillRect(left, midY, midX - left, bottom - midY);
        c.fillStyle = "rgba(245,158,11,0.08)";  c.fillRect(left, top,  midX - left, midY - top);
        c.fillStyle = "rgba(59,130,246,0.08)";  c.fillRect(midX, midY, right - midX, bottom - midY);
        c.beginPath(); c.setLineDash([6, 4]); c.lineWidth = 2; c.strokeStyle = "rgba(100,116,139,0.55)";
        c.moveTo(midX, top); c.lineTo(midX, bottom); c.stroke();
        c.beginPath(); c.moveTo(left, midY); c.lineTo(right, midY); c.stroke();
        c.restore();
      },
    };

    const rankLabelPlugin = {
      id: "rankLabels",
      afterDatasetsDraw(chart) {
        const { ctx: c } = chart;
        chart.data.datasets.forEach((dataset, di) => {
          const meta = chart.getDatasetMeta(di);
          dataset.data.forEach((point, i) => {
            const el = meta.data[i];
            if (!el) return;
            const { x, y } = el.getProps(["x", "y"], true);
            c.save();
            c.fillStyle = "#fff";
            c.font = "bold 12px Pretendard, sans-serif";
            c.textAlign = "center";
            c.textBaseline = "middle";
            c.fillText(point.rank, x, y);
            c.restore();
          });
        });
      },
    };

    chartInstanceRef.current = new Chart(ctx, {
      type: "scatter",
      data: { datasets: CHART_DATASETS },
      plugins: [quadrantPlugin, rankLabelPlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 8, right: 24, bottom: 8, left: 8 } },
        plugins: {
          legend: {
            position: "top",
            labels: { usePointStyle: true, pointStyle: "circle", font: { size: 12, family: "Pretendard, sans-serif" }, padding: 16 },
          },
          tooltip: {
            callbacks: {
              label(c) {
                const d = c.raw;
                const lvl = v => v < 1.5 ? "Low" : v < 2.5 ? "Middle" : "High";
                return ` ${d.rank}위  ${d.label}   재무: ${lvl(d.x)} / 영향: ${lvl(d.y)}`;
              },
            },
            bodyFont: { size: 12, family: "Pretendard, sans-serif" },
            padding: 10,
          },
        },
        scales: {
          x: { min: 0.5, max: 3.5, title: { display: true, text: "재무중요성 (Financial Materiality)", font: { size: 11, weight: "700" }, color: "#475569" },
            ticks: { stepSize: 1, callback: v => ({ 1: "Low", 2: "Middle", 3: "High" }[v] || ""), color: "#64748b" }, grid: { color: "#e2e8f0" } },
          y: { min: 0.5, max: 3.5, title: { display: true, text: "영향중요성 (Impact Materiality)", font: { size: 11, weight: "700" }, color: "#475569" },
            ticks: { stepSize: 1, callback: v => ({ 1: "Low", 2: "Middle", 3: "High" }[v] || ""), color: "#64748b" }, grid: { color: "#e2e8f0" } },
        },
      },
    });
  };

  const moveStep = (index) => {
    if (index === activeIndex) return;
    navigate(steps[index].path);
  };

  const toggleSection = (id) => {
    setOpenSections(prev => ({ ...prev, [id]: !prev[id] }));
  };

  /* 탭 버튼 스타일 함수 */
  const TAB_STYLE = (active) => ({
    padding: "8px 20px", border: "none", background: "none",
    fontWeight: 700, fontSize: "0.85rem", cursor: "pointer",
    color: active ? "#03A94D" : "#94a3b8",
    borderBottom: active ? "2px solid #03A94D" : "none",
    marginBottom: active ? "-2px" : "0",
  });

  return (
    <div className="sr-container">
      <header className="sr-header">
        <h1 className="sr-title">지속가능경영보고서 AI 자동 생성</h1>
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
    
    <main className="main-content" style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "20px", overflowY: "auto", justifyContent: "flex-start" }}>
      <div>
        <div style={{ display: "flex", flexDirection: "row", gap: "20px", alignItems: "stretch", flex: 1, minHeight: 0 }}>
                           {/* ── 왼쪽 패널 ── */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", borderBottom: "2px solid #e2e8f0", marginBottom: "16px" }}>
             {["최종선정요약", "후보군 최종 선정 과정", "점수 해석", "다음 단계 연결"].map((label, i) => (
              <button key={i} style={TAB_STYLE(leftTab === i)} onClick={() => setLeftTab(i)}>{label}</button>
                ))} 
            </div>
                

             {/* 탭 0: 최종선정요약  */}
            {leftTab === 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* 최종 선정 요약 */}
                <div className="card-container">
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "20px",minwidth: 0 }}>
                    <span style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b" }}>최종 선정 요약</span>
                    <span style={{ width: "18px", height: "18px", border: "1.5px solid #cbd5e1", borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "0.65rem", color: "#94a3b8" }}>ⓘ</span>
                  </div>
                  <div className="summary-grid">
                    {[
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>, label: "평가 대상", value: "62개", cls: "" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>, label: "후보군", value: "25개", cls: "" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/></svg>, label: "최종 선정", value: "10개", cls: "success", valueClass: "text-green" },
                      { icon: <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.8"><polyline points="17 11 12 6 7 11"/><polyline points="17 18 12 13 7 18"/></svg>, label: "High 영역", value: "5개", cls: "danger", valueClass: "text-red" },
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
                  <div style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b", marginBottom: "16px" }}>최종 Top 이슈 점수 분해</div>
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
                  <div style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b", marginBottom: "16px" }}>선정 사유 요약</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    {[
                      { bg: "#f0fdf4", stroke: "#03A94D", title: "영향 및 재무 동시 고점 이슈 우선", desc: "영향 중대성과 재무 중대성 모두 높은 이슈를 우선 최종 선정하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg> },
                      { bg: "#eff6ff", stroke: "#3b82f6", title: "이해관계자 의견 반영", desc: "설문 결과와 주요 이해관계자 인터뷰를 반영하여 중요 이슈를 확정하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg> },
                      { bg: "#f5f3ff", stroke: "#7c3aed", title: "지속가능경영 전략 연계", desc: "기업의 전략 방향 및 리스크/기회 관점에서 관리가 필요한 이슈를 포함하였습니다.",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> },
                    ].map((item, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
                        <div style={{ flexShrink: 0, width: "40px", height: "40px", background: item.bg, borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>{item.icon}</div>
                        <div>
                          <div style={{ fontSize: "0.88rem", fontWeight: 800, color: "#1e293b", marginBottom: "4px" }}>{item.title}</div>
                          <p style={{ fontSize: "0.78rem", color: "#64748b", margin: 0, lineHeight: 1.55 }}>{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            </div>

            {/* 탭 1: 후보군 최종 선정 과정 */}
            {leftTab === 1 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "24px" }}>
                  <div style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b", marginBottom: "20px" }}>후보군 최종 선정 과정</div>
                  <div style={{ display: "flex", gap: "24px", alignItems: "flex-start" }}>
                    {/* 플로우 카드 */}
                    <div style={{ flex: 1.4, display: "flex", flexDirection: "column", gap: 0 }}>
                      {[
                        { count: "62개 평가 대상", desc: "벤치마킹, 미디어, 이해관계자 설문을 통해<br>도출된 전체 평가 이슈 수",
                          icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>, last: false },
                        { count: "25개 후보군", desc: "양축 점수 기준 충족 및 주요성 기준을<br>충족한 이슈",
                          icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>, last: false },
                        { count: "최종 10개 선정", desc: "이사회 및 ESG 실무 협의 기반<br>보고서 핵심 이슈로 최종 선정",
                          icon: <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>, last: true },
                      ].map((card, i) => (
                        <div key={i}>
                          {/* <div style={{ display: "flex", alignItems: "center", gap: "16px", background: card.last ? "#f0fdf4" : "#f8fafc", border: `1px solid ${card.last ? "#bbf7d0" : "#e2e8f0"}`, borderRadius: "14px", padding: "18px 20px" }}>
                            <div style={{ flexShrink: 0, width: "52px", height: "52px", background: "#dcfce7", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>{card.icon}</div>
                            <div>
                              <div style={{ fontSize: "1.15rem", fontWeight: 850, color: "#03A94D", marginBottom: "4px" }}>{card.count}</div>
                              <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.55 }} dangerouslySetInnerHTML={{ __html: card.desc }} />
                            </div>
                          </div> */}
                          {!card.last && <div style={{ display: "flex", justifyContent: "center", padding: "6px 0", color: "#03A94D", fontSize: "1.3rem" }}>↓</div>}
                        </div>
                      ))}
                    </div>
                    {/* 선정 기준 */}
                    <div style={{ flex: 1, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "20px 22px", alignSelf: "stretch" }}>
                      <div style={{ fontSize: "0.92rem", fontWeight: 850, color: "#03A94D", marginBottom: "16px" }}>선정 기준</div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                        {[
                          { icon: "🎯", text: "양측 점수 기준 충족", sub: "(재무적·사회적 영향 모두 Medium 이상)" },
                          { icon: "📊", text: "2개 이상 분석축에서", sub: "반복 관측" },
                          { icon: "🔗", text: "가치사슬 관련성 높음" },
                          { icon: "👥", text: "이해관계자 관심도 높음" },
                          { icon: "🛡️", text: "리스크/기회 요인으로서의", sub: "중요성 고려" },
                        ].map((item, i) => (
                          <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                            <div style={{ flexShrink: 0, width: "32px", height: "32px", background: "#dcfce7", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.9rem" }}>{item.icon}</div>
                            <div style={{ fontSize: "0.78rem", color: "#334155", lineHeight: 1.6 }}>
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

                {/* 제외된 이슈 */}
                <div className="card-container">
                  <div style={{ fontSize: "0.95rem", fontWeight: 850, color: "#ef4444", marginBottom: "14px" }}>후보있지만 제외된 이슈</div>
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

            {/* 탭 2: 점수 해석 */}
            {leftTab === 2 && (
              <div className="card-container" style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b" }}>점수 해석</span>
                  <span style={{ width: "18px", height: "18px", border: "1.5px solid #cbd5e1", borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "0.65rem", color: "#94a3b8" }}>ⓘ</span>
                </div>

                {/* 1. 분석축 기여도 */}
                <div>
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#1e293b", marginBottom: "4px" }}>1. 분석축 기여도</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "14px" }}>각 주요 이슈 점수에 대한 분석축(벤치마킹/미디어/설문) 기여도를 보여줍니다.</div>
                  <div style={{ display: "flex", gap: "16px", marginBottom: "14px", fontSize: "0.78rem", color: "#475569" }}>
                    {[["#22c55e","벤치마킹"], ["#3b82f6","미디어"], ["#f59e0b","설문"]].map(([color, label]) => (
                      <div key={label} style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                        <span style={{ width: "11px", height: "11px", borderRadius: "50%", background: color, display: "inline-block" }}></span>{label}
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {CONTRIBUTION_DATA.map((item) => (
                      <div key={item.rank} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: "130px" }}>
                          <span style={{ width: "22px", height: "22px", borderRadius: "50%", background: item.rankColor, color: "#fff", fontSize: "0.7rem", fontWeight: 800, display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{item.rank}</span>
                          <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "#1e293b", whiteSpace: "nowrap" }}>{item.name}</span>
                        </div>
                        <div style={{ flex: 1, display: "flex", borderRadius: "6px", overflow: "hidden", height: "28px" }}>
                          <div style={{ width: `${item.bench}%`, background: "#22c55e", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.72rem", fontWeight: 700, color: "#fff" }}>{item.bench}%</div>
                          <div style={{ width: `${item.media}%`, background: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.72rem", fontWeight: 700, color: "#fff" }}>{item.media}%</div>
                          <div style={{ width: `${item.survey}%`, background: "#f59e0b", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.72rem", fontWeight: 700, color: "#fff" }}>{item.survey}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Blind Spot */}
                <div>
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#1e293b", marginBottom: "4px" }}>2. 분석축 간 불일치 / Blind Spot</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "14px" }}>분석축 간 점수 편차가 큰 이슈를 확인하여 전략적 블라인드 스팟을 식별합니다.</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {BLIND_SPOTS.map((item) => (
                    <div key={item.rank} style={{ display: "flex", alignItems: "center", gap: "10px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "12px 14px" }}>
                    <span style={{ width: "24px", height: "24px", borderRadius: "50%", background: item.rankColor, color: "#fff", fontSize: "0.72rem", fontWeight: 800, display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{item.rank}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#1e293b", marginBottom: "2px" }}>{item.name}</div>
                      <div style={{ fontSize: "0.74rem", color: "#64748b" }}>{item.desc}</div>
                    </div>
                    <span style={{ background: item.badgeBg, color: item.badgeColor, fontSize: "0.72rem", fontWeight: 700, padding: "4px 10px", borderRadius: "20px", whiteSpace: "nowrap", flexShrink: 0 }}>{item.badge}</span>
                  </div>
                ))}
                    </div>
                  </div>
                

                {/* 3: 매트릭스 해석 */}

                
                <div>
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#1e293b", marginBottom: "4px" }}>3. 매트릭스 해석</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "14px" }}>이중 중대성 매트릭스 영역별 의미를 안내합니다.</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {MATRIX_ZONES.map((zone, i) => (
                      <div key={i} style={{ display: "flex", gap: "14px", background: zone.bg, border: `1px solid ${zone.border}`, borderRadius: "10px", padding: "14px 16px", alignItems: "flex-start" }}>
                        <div style={{ minWidth: "130px" }}><span style={{ fontSize: "0.82rem", fontWeight: 800, color: zone.labelColor }}>{zone.label}</span></div>
                        <div style={{ fontSize: "0.78rem", color: "#475569", lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: zone.desc.replace(/\n/g, "<br>") }} />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              )}

            {/* 탭 3: 다음 단계 연결 */}
            {leftTab === 3 && (
              <div className="card-container" style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ fontSize: "1rem", fontWeight: 850, color: "#1e293b", marginBottom: "20px" }}>다음 단계 연결</div>

                {/* 섹션 1: 보고서 반영 우선순위 */}
                  <div style={{ border: "1px solid #e2e8f0", borderRadius: "12px", marginBottom: "14px", overflow: "hidden" }}>
                  <div onClick={() => toggleSection(1)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px", cursor: "pointer", userSelect: "none", background: "#f8fafc" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "0.88rem", fontWeight: 800, color: "#1e293b" }}>1. 보고서 반영 우선순위</span>
                      <span style={{ width: "17px", height: "17px", border: "1.5px solid #cbd5e1", borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "0.6rem", color: "#94a3b8" }}>ⓘ</span>
                    </div>
                    <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>{openSections[1] ? "∧" : "∨"}</span>
                  </div>
                  {openSections[1] && (
                    <div style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: "10px" }}>
                      {PRIORITY_ITEMS.map((item) => (
                        <div key={item.rank} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          
                          <span style={{ flex: 1, fontSize: "0.82rem", fontWeight: 600, color: "#1e293b" }}>{item.name}</span>
                          <span style={{ fontSize: "0.78rem", color: "#94a3b8", whiteSpace: "nowrap" }}>중요도 <strong style={{ color: "#1e293b" }}>{item.score}</strong></span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 섹션 2: 필요 온보딩 지표 */}
                <div style={{ border: "1px solid #e2e8f0", borderRadius: "12px", marginBottom: "14px", overflow: "hidden" }}>
                  <div onClick={() => toggleSection(2)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px", cursor: "pointer", userSelect: "none", background: "#f8fafc" }}>
                    <span style={{ fontSize: "0.88rem", fontWeight: 800, color: "#1e293b" }}>2. 필요 온보딩 지표</span>
                    <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>{openSections[2] ? "∧" : "∨"}</span>
                  </div>
                  {openSections[2] && (
                    <div style={{ padding: "0 18px 16px 18px" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" }}>
                        <thead>
                          <tr style={{ borderBottom: "1.5px solid #e2e8f0" }}>
                            {["이슈","환경(E)","사회(S)","지배구조(G)","필요 지표 수","온보딩 완료"].map(h => (
                              <th key={h} style={{ padding: "10px 6px", textAlign: h === "이슈" ? "left" : "center", fontWeight: 600, color: "#94a3b8" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {ONBOARDING_ROWS.map((row, i) => (
                            <tr key={i} style={{ borderBottom: i < ONBOARDING_ROWS.length - 1 ? "1px solid #f1f5f9" : "none" }}>
                              <td style={{ padding: "10px 8px", fontWeight: 600, color: "#1e293b" }}>{row.name}</td>
                              {[row.e, row.s, row.g].map((v, j) => (
                                <td key={j} style={{ padding: "10px 6px", textAlign: "center", color: v ? "#22c55e" : "#94a3b8", fontWeight: 700 }}>{v ? "✓" : "-"}</td>
                              ))}
                              <td style={{ padding: "10px 6px", textAlign: "center", color: "#475569" }}>{row.count}</td>
                              <td style={{ padding: "10px 8px", textAlign: "center", fontWeight: 700, color: row.doneColor }}>{row.done}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* 섹션 3: 부족 데이터 현황 */}
                <div style={{ border: "1px solid #e2e8f0", borderRadius: "12px", marginBottom: "14px", overflow: "hidden" }}>
                  <div style={{ padding: "14px 18px", background: "#f8fafc" }}>
                    <span style={{ fontSize: "0.88rem", fontWeight: 800, color: "#1e293b" }}>3. 부족 데이터 현황</span>
                  </div>
                  <div style={{ padding: "0 18px 16px 18px" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" }}>
                      <thead>
                        <tr style={{ borderBottom: "1.5px solid #e2e8f0" }}>
                          <th style={{ padding: "10px 8px", textAlign: "left", fontWeight: 600, color: "#94a3b8" }}>항목</th>
                          <th style={{ padding: "10px 8px", textAlign: "left", fontWeight: 600, color: "#94a3b8" }}>부족 데이터</th>
                          <th style={{ padding: "10px 8px", textAlign: "left", fontWeight: 600, color: "#94a3b8" }}>완료율</th>
                        </tr>
                      </thead>
                      <tbody>
                        {MISSING_DATA_ROWS.map((row, i) => (
                          <tr key={i} style={{ borderBottom: i < MISSING_DATA_ROWS.length - 1 ? "1px solid #f1f5f9" : "none" }}>
                            <td style={{ padding: "12px 8px", fontWeight: 600, color: "#1e293b", whiteSpace: "nowrap" }}>{row.name}</td>
                            <td style={{ padding: "12px 8px" }}>
                              <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                                <span style={{ color: "#f59e0b", fontSize: "0.82rem" }}>⚠</span>
                                <span style={{ color: "#475569" }}>{row.missing}</span>
                              </span>
                            </td>
                            <td style={{ padding: "12px 8px" }}>
                              
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 섹션 4: 바로가기 */}
                 <div style={{ border: "1px solid #e2e8f0", borderRadius: "12px", overflow: "hidden" }}>
                  <div style={{ padding: "14px 18px", background: "#f8fafc" }}>
                    <span style={{ fontSize: "0.88rem", fontWeight: 800, color: "#1e293b" }}>4. 바로가기</span>
                  </div>
                  <div style={{ padding: "14px 18px", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "12px" }}>
                    {[
                      { bg: "#dcfce7", stroke: "#16a34a", title: "온보딩 지표 확인", desc: "지표 정의 및 입력 항목 보기", path: "/onboard",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg> },
                      { bg: "#dbeafe", stroke: "#2563eb", title: "부족 데이터 입력", desc: "필요 데이터 입력 및 관리", path: "/onboard",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg> },
                      { bg: "#ede9fe", stroke: "#7c3aed", title: "보고서 초안 생성", desc: "선택 이슈 기반 초안 생성", path: "/draft",
                        icon: <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> },
                    ].map((item) => (
                      <div key={item.title} onClick={() => navigate(item.path)} style={{ display: "flex", alignItems: "center", gap: "10px", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "12px 14px", cursor: "pointer", background: "#fff" }}
                        onMouseOver={e => e.currentTarget.style.background = "#f8fafc"} onMouseOut={e => e.currentTarget.style.background = "#fff"}>
                        <div style={{ width: "36px", height: "36px", borderRadius: "9px", background: item.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{item.icon}</div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: "0.76rem", fontWeight: 700, color: "#1e293b", marginBottom: "2px" }}>{item.title}</div>
                          <div style={{ fontSize: "0.68rem", color: "#94a3b8", lineHeight: 1.4 }}>{item.desc}</div>
                        </div>
                        <span style={{ color: "#94a3b8", fontSize: "1rem", flexShrink: 0 }}>›</span>
                      </div>
                    ))}
                  </div>
                </div> 
            </div>
            )} 
          

              
          {/* ── 오른쪽 패널 ── */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", borderBottom: "2px solid #e2e8f0", marginBottom: "16px" }}>
              <button style={TAB_STYLE(rightTab === 0)} onClick={() => setRightTab(0)}>전체</button>
              <button style={TAB_STYLE(rightTab === 1)} onClick={() => setRightTab(1)}></button>
            </div>

            {rightTab === 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "26px" }}>
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "16px 20px" }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: 800, color: "#1e293b", marginBottom: "12px" }}>이중 중대성 매트릭스</div>
                  <div style={{ position: "relative", height: "320px", width: "100%" }}>
                    <canvas ref={chartCanvasRef}></canvas>
                  </div>
                </div>
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "20px" }}>
                  <p style={{ margin: "0 0 8px 0" }}>⚫ x 1 = low, ⚫ x 2 = middle, ⚫ x 3 = high</p>
                  <table border="1" style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr><th>순위</th><th>구분</th><th>탑 이슈</th><th>Type</th><th>Period</th><th>재무중요성</th><th>영향중요성</th></tr>
                    </thead>
                    <tbody>
                      {SCATTER_TABLE_ROWS.map((row) => (
                        <tr key={row.rank}>
                          <td>{row.rank}.</td><td>{row.cat}</td><td>{row.name}</td>
                          <td>{row.type}</td><td>{row.period}</td><td>{row.fin}</td><td>{row.impact}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {rightTab === 1 && (
              <div className="sr-result-dashboard" style={{ display: "block" }}>
                <div className="robot-view-container">
                  <div className="particle-field" ref={particleRef}></div>
                  <div className="robot-stage">
                    <div className="robot-float-wrap">
                      <img src={robot} className="robot-main-img" alt="robot" />
                    </div>
                  </div>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: 800, margin: "0 0 4px 0" }}>분석 미실행 상태</h3>
                  <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>하단의 '설문 결과 분석' 버튼을 작동시켜 주십시오.</p>
                </div>
              </div>
            )}
            </div>          
                      
        </div>        {/* row div 닫힘 */}
       </div>          {/* main 안쪽 div 닫힘 */}
      </main>
  </div>
  );
};

 export default Result;