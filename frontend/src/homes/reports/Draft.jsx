import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/draft.css";

const paragraphData = {
  p1: {
    tag: "전략 및 방향", tagType: "blue", id: "P-03-01",
    tooltipTitle: "● 사업 개요 지표",
    tooltipRows: [
      { key: "metric_id", val: "G0-02__G0001" },
      { key: "연결 매출액", val: "17.8조 KRW" },
      { key: "G0-03__G0001", val: "22개 사업장" },
      { key: "보고기간", val: "2024.01.01~12.31" },
    ],
    preview: "SKM은 과학기반 감축목표 이니셔티브(SBTi)의 1.5°C 시나리오에 부합하는 넷제로 목표를 수립하고...",
    metricCount: 1,
    metrics: [{
      name: "연결 Scope 1-2 총배출량", badge: "그룹 통합 지표", badgeType: "green",
      metricId: "E1-06", atomicId: "E1-06-G0003", unit: "tCO₂eq", dataType: "정량(Rollup)",
      desc: "지주사와 자회사 설비 데이터를 합산하여 산출한 연결 기준 총배출량",
      latest: "112,500 tCO₂eq",
      trend: [{ y: 2022, v: 130890 }, { y: 2023, v: 117400 }, { y: 2024, v: 112500 }],
      breakdown: [{ l: "A_GROUP", v: "66,000" }, { l: "B_SUB_KR", v: "26,000" }, { l: "C_SUB_EU", v: "18,000" }, { l: "D_SUB_US", v: "2,500" }],
      formula: "Scope 1 + Scope 2\nE1-05__G0001 + E1-05__G0002",
    }],
    aiDesc: "넷제로 전환 방향을 나타내는 핵심 전략 지표로, 과학기반 감축목표 이행 현황을 정량적으로 보여줍니다.",
    related: { id: "P-03-02", label: "핵심 데이터" },
  },
  p2: {
    tag: "주요 성과", tagType: "green", id: "S-03-02",
    tooltipTitle: "● E1-06 Scope 1·2 배출량",
    tooltipRows: [
      { key: "metric_id", val: "E1-06__G0003" },
      { key: "2024 배출량", val: "112,500 tCO₂eq" },
      { key: "감축량", val: "4,402 tCO₂eq" },
      { key: "감축률", val: "3.91%" },
      { key: "재생E 전환율", val: "9.49%" },
    ],
    preview: "2024년 온실가스 배출량(스코프 1·2)은 96.7만 tCO₂e로, 2022년 대비 11.0% 감소하였습니다.",
    metricCount: 1,
    metrics: [{
      name: "온실가스 배출량 (스코프 1·2)", badge: "핵심 지표", badgeType: "blue",
      metricId: "M-ENV-045", atomicId: "AM-ENV-045-01", unit: "만 tCO₂e", dataType: "정량",
      desc: "스코프 1과 스코프 2 배출량을 합산한 온실가스 총배출량",
      latest: "96.7만 tCO₂e",
      trend: [{ y: 2022, v: 101.4 }, { y: 2023, v: 94.2 }, { y: 2024, v: 96.7 }],
      breakdown: [{ l: "스코프 1", v: "33.6" }, { l: "스코프 2", v: "53.1" }],
      formula: "스코프 1 + 스코프 2",
    }],
    aiDesc: "온실가스 배출량 추이를 나타내는 핵심 지표로, 감축 목표 대비 이행 현황을 정량적으로 보여줍니다.",
    related: { id: "P-03-01", label: "전략 및 방향" },
  },
  p3: {
    tag: "전략 및 접근", tagType: "orange", id: "S-03-03",
    tooltipTitle: "● S6-04 공급망 감사",
    tooltipRows: [
      { key: "감사 이행률", val: "71.90%" },
      { key: "고위험 업체 수", val: "64개사" },
      { key: "CAP 완료율", val: "68.09%" },
    ],
    preview: "SKM은 2030년까지 2022년 대비 온실가스 배출량(스코프 1·2) 42% 감축을 목표로 하며...",
    metricCount: 1,
    metrics: [{
      name: "온실가스 감축 목표", badge: "목표 지표", badgeType: "green",
      metricId: "E1-05", atomicId: "E1-05-G0001", unit: "%", dataType: "정량(목표)",
      desc: "2030년까지 2022년 대비 온실가스 배출량 42% 감축 목표치",
      latest: "42% (2030년 목표)",
      trend: [{ y: 2022, v: 0 }, { y: 2023, v: 11 }, { y: 2024, v: 11 }],
      breakdown: [{ l: "에너지 전환", v: "20%p" }, { l: "공정 효율화", v: "12%p" }, { l: "공급망 관리", v: "10%p" }],
      formula: "(기준연도 - 목표연도) / 기준연도 × 100",
    }],
    aiDesc: "온실가스 감축 목표 및 3대 전략 축에 관한 내용으로, 2030 로드맵의 핵심 실행 방향을 제시합니다.",
    related: { id: "S-03-02", label: "주요 성과" },
  },
  p4: {
    tag: "인재 개발", tagType: "blue", id: "S3-02",
    tooltipTitle: "● S3-02 교육 지표",
    tooltipRows: [
      { key: "임직원 수", val: "8,367명" },
      { key: "1인당 교육시간", val: "33.42시간" },
      { key: "핵심직무 달성률", val: "72.01%" },
    ],
    preview: "연결 임직원 8,367명, 1인당 교육시간 33.42시간, 핵심직무 달성률 72.01%...",
    metricCount: 2,
    metrics: [{
      name: "교육 훈련 현황", badge: "인적자본 지표", badgeType: "blue",
      metricId: "S3-02__G0002", atomicId: "S3-02__G0003", unit: "시간/명", dataType: "정량",
      desc: "연결 임직원 교육시간 및 핵심직무 교육 달성률",
      latest: "33.42시간/명",
      trend: [{ y: 2022, v: 28.1 }, { y: 2023, v: 31.5 }, { y: 2024, v: 33.42 }],
      breakdown: [{ l: "임직원 수", v: "8,367명" }, { l: "1인당 교육시간", v: "33.42h" }, { l: "핵심직무 달성률", v: "72.01%" }],
      formula: "총 교육시간 / 전체 임직원 수 (S1-02__G0001)",
    }],
    aiDesc: "미래 모빌리티 전환을 위한 인적 역량 개발 수준을 나타내는 핵심 지표입니다.",
    related: { id: "S3-01", label: "인재 개발 전략" },
  },
  p5: {
    tag: "친환경 제품", tagType: "green", id: "AP-E-06",
    tooltipTitle: "● AP-E-06 친환경제품",
    tooltipRows: [
      { key: "친환경 매출", val: "4.3조 KRW" },
      { key: "매출 비중", val: "24.15%" },
      { key: "회피 배출량", val: "1,245,000 tCO₂eq" },
      { key: "비용 절감", val: "689.7억 KRW" },
    ],
    preview: "친환경 제품 매출 4.3조 KRW (매출 대비 24.15%), 회피배출 1,245,000 tCO₂eq...",
    metricCount: 1,
    metrics: [{
      name: "친환경 제품 매출", badge: "제품 지속가능성", badgeType: "green",
      metricId: "AP-E-06__G0001", atomicId: "AP-E-06__G0003", unit: "KRW", dataType: "정량",
      desc: "연결 기준 친환경 제품 매출액 및 회피 온실가스 배출량",
      latest: "4,298,000,000,000 KRW",
      trend: [{ y: 2022, v: 3100 }, { y: 2023, v: 3750 }, { y: 2024, v: 4298 }],
      breakdown: [{ l: "친환경 매출", v: "4.3조 KRW" }, { l: "매출 비중", v: "24.15%" }, { l: "회피 배출량", v: "1,245,000 tCO₂eq" }, { l: "비용 절감", v: "689.7억 KRW" }],
      formula: "AP-E-06__G0001 / 연결 총매출 × 100 = AP-E-06__G0003",
    }],
    aiDesc: "친환경 제품 포트폴리오의 재무적·환경적 성과를 동시에 보여주는 핵심 지표입니다.",
    related: { id: "AP-E-06", label: "제품 환경성과" },
  },
  p6: {
    tag: "제품 안전", tagType: "orange", id: "AP-S-01",
    tooltipTitle: "● AP-S-01 제품안전",
    tooltipRows: [
      { key: "리콜 건수", val: "3건" },
      { key: "CAP 완료율", val: "70.37%" },
    ],
    preview: "리콜 건수 3건, 제품안전 CAP 완료율 70.37%...",
    metricCount: 1,
    metrics: [{
      name: "제품안전 관리 현황", badge: "품질 지표", badgeType: "blue",
      metricId: "AP-S-01__G0001", atomicId: "AP-S-01__G0005", unit: "건", dataType: "정량",
      desc: "연결 기준 리콜 및 제품안전 시정조치(CAP) 완료 현황",
      latest: "CAP 완료율 70.37%",
      trend: [{ y: 2022, v: 65 }, { y: 2023, v: 68 }, { y: 2024, v: 70.37 }],
      breakdown: [{ l: "리콜 건수", v: "3건" }, { l: "CAP 완료율", v: "70.37%" }, { l: "전체 대상", v: "10건" }],
      formula: "CAP 완료 건수 / AP-S-01__G0002 × 100",
    }],
    aiDesc: "제품 품질과 안전 관리 수준을 정량적으로 보여주는 핵심 리스크 지표입니다.",
    related: { id: "AP-S-01", label: "제품안전 정책" },
  },
};

const paragraphTexts = {
  p1: (
    <>
      A_GROUP의 자동차 부품과 전동화 부품 사업을 총괄하는 지주회사로, 국내외 자회사와 함께 모빌리티 부품 사업을 이룬다.
      보고기간은 2024.01.01~2024.12.31이며, 연결 공시 범위는 A_GROUP 본인 사업장과 B_SUB_KR, C_SUB_EU, D_SUB_US를 포함한다.
      연결 매출액은 17,800,000,000,000 KRW, 연결 사업장 수는 22개이다.
    </>
  ),
  p2: (
    <>
      A_GROUP의 2045년 넷제로립과 2040년 재생에너지 100% 전환을 목표로 Scope 1·2 배출 감축과 전환계획을 관리한다.
      기준연도는 2019이며 기준연도 연결 Scope 1·2 배출량은 130,890 tCO₂eq이다.
      보고연도 연결 Scope 1·2 배출량은 112,500 tCO₂eq, 전년 대비 감축량은 4,402 tCO₂eq, 감축률은 3.91%이다.
      재생에너지 전환율은 9.49%이다.
    </>
  ),
  p3: (
    <>
      A_GROUP의 주요 협력사의 환경·인권·윤리 리스크가 조달 안정성과 브랜드 신뢰에 미치는 영향을 고려해
      공급망 지속가능성 리스크를 관리한다. 연결 기준 공급업체 감사 이행률은 71.90%, 고위험 공급업체 수는
      64개사이다. 공급망 CAP 완료율은 68.09%이다.
    </>
  ),
  p4: (
    <>
      전동화·자율주행·디지털화 전환에 대응하기 위해 미래 모빌리티 기술 인재 확보와 내부 역량 강화가 중요하다.
      연결 임직원 수는 8,367명이며, 1인당 교육시간은 33.42시간/명, 핵심직무 교육 달성률은 72.01%이다.
    </>
  ),
  p5: (
    <>
      전동화 부품과 경량화·고효율 부품은 제품 사용 단계의 온실가스 감축과 환경영향 저감에 기여한다.
      연결 친환경 제품 매출액은 4,298,000,000,000 KRW이며, 연결 매출 대비 비중은 24.15%이다.
      회피 배출량은 1,245,000 tCO₂eq, 재화적 비용 절감 효과는 68,973,000,000 KRW로 추산된다.
    </>
  ),
  p6: (
    <>
      제품 품질과 안전은 고객 신뢰 확보와 규제 대응, 리콜 리스크 관리와 직접 연결되는 핵심 주제다.
      연결 기준 리콜 건수는 10건, 리콜 건수는 3건이며, 제품안전 CAP 완료율은 70.37%이다.
    </>
  ),
};

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

const Draft = () => {
  const [currentPid, setCurrentPid] = useState(null);
  const [metricOpen, setMetricOpen] = useState(true);
  const particleRef = useRef(null);
  const navigate = useNavigate();

  const steps = [
    { id: 1, title: "벤치마킹 분석", icon: "🎯", path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: "📺", path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: "👥", path: "/survey" },
    { id: 4, title: "전체 결과", icon: "📊", path: "/result" },
    { id: 5, title: "보고서 초안", icon: "📄", path: "/draft" },
  ];
  const activeIndex = 4;

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
      p.style.width = `${size}px`;
      p.style.height = `${size}px`;
      p.style.left = `${Math.random() * 100}%`;
      p.style.top = `${Math.random() * 100}%`;
      p.style.animationDelay = `${Math.random() * 2}s`;
      particleRef.current.appendChild(p);
    }
  };

  const selectParagraph = (pid) => {
    if (currentPid === pid) {
      setCurrentPid(null);
      return;
    }
    setCurrentPid(pid);
    setMetricOpen(true);
  };

  const data = currentPid ? paragraphData[currentPid] : null;
  const metric = data ? data.metrics[0] : null;

  return (
    <div className="sr-container">
      <header className="sr-header">
        <h1 className="sr-title">지속가능경영보고서 AI 자동 생성</h1>
        <div className="sr-stepper-row">
          {steps.map((step, index) => (
            <div key={step.id} style={{ display: "flex", alignItems: "center" }}>
              <div
                className={`step-box ${index === activeIndex ? "active" : ""}`}
                onClick={() => { if (index !== activeIndex) navigate(step.path); }}
              >
                <div className="step-icon-circle">{step.icon}</div>
                <div style={{ fontSize: "0.8rem", fontWeight: 850 }}>{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line"></div>}
            </div>
          ))}
        </div>
      </header>

      <main className="main-content">
        <div className="draft-wrapper">
          <div className="draft-body">

            {/* 문서 영역 */}
            <div className="draft-doc" id="draftDoc">
              <div className="doc-toolbar">
                <div className="doc-breadcrumb">
                  <span>🏠</span><span className="bc-sep">›</span>
                  <span className="bc-item">환경경영</span><span className="bc-sep">›</span>
                  <span className="bc-item">기후변화와 대응</span><span className="bc-sep">›</span>
                  <span className="bc-item active">기후목표·전환계획</span>
                </div>
                <div className="doc-page-info">페이지 1 / 5</div>
                <div className="doc-actions">
                  <button className="doc-btn">✏ 수정</button>
                  <button className="doc-btn">✓ 저장</button>
                  <button className="doc-btn">💬 코멘트</button>
                  <button className="doc-btn-more">···</button>
                </div>
              </div>

              <div className="doc-content">
                <h1 className="doc-title">기후목표·전환계획</h1>
                <p className="doc-subtitle">전환 리스크에 선제적으로 대응하는 넷제로 로드맵</p>

                {Object.keys(paragraphData).map((pid) => {
                  const d = paragraphData[pid];
                  return (
                    <div
                      key={pid}
                      className={`dp-wrap${currentPid === pid ? " selected" : ""}`}
                      onClick={() => selectParagraph(pid)}
                    >
                      <p className="dp-text">{paragraphTexts[pid]}</p>
                      <div className="dp-tooltip">
                        <div className="dp-tooltip-title">{d.tooltipTitle}</div>
                        {d.tooltipRows.map((row, i) => (
                          <div key={i} className="dp-tooltip-row">
                            <span className="dp-tooltip-key">{row.key}</span>
                            <span className="dp-tooltip-val">{row.val}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 우측 데이터 추적 패널 */}
            <div className={`draft-panel${currentPid ? " open" : ""}`} id="draftPanel">
              {data && metric && (
                <div className="panel-inner">
                  <div className="panel-hd">
                    <span className="panel-hd-title">데이터 추적</span>
                    <button className="panel-close-btn" onClick={() => setCurrentPid(null)}>✕</button>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">선택 문단</div>
                    <span className={`para-chip ${data.tagType}`}>{data.tag}</span>
                    <p className="para-preview-text">{data.preview}</p>
                    <span className="para-id-link">문단 ID: {data.id}</span>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">참조 지표 ({data.metricCount})</div>
                    <div className="metric-accordion">
                      <div
                        className={`metric-acc-header${metricOpen ? " open" : ""}`}
                        onClick={() => setMetricOpen((v) => !v)}
                      >
                        <div className="metric-acc-header-left">
                          <span className="metric-acc-name">{metric.name}</span>
                          <span className={`metric-badge ${metric.badgeType}`}>{metric.badge}</span>
                        </div>
                        <span className="metric-acc-chevron">›</span>
                      </div>

                      {metricOpen && (
                        <div className="metric-acc-body">
                          <div className="metric-row">
                            <span className="metric-row-key">metric_id</span>
                            <span className="metric-row-val">{metric.metricId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">atomic_metric_id</span>
                            <span className="metric-row-val">{metric.atomicId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">지표명</span>
                            <span className="metric-row-val">{metric.name}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">단위</span>
                            <span className="metric-row-val">{metric.unit}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">데이터 유형</span>
                            <span className="metric-row-val">{metric.dataType}</span>
                          </div>
                          <hr className="metric-divider" />
                          <div className="metric-row">
                            <span className="metric-row-key">설명</span>
                            <span className="metric-row-val metric-row-val--muted">{metric.desc}</span>
                          </div>
                          <div className="metric-latest-box">
                            <span className="metric-latest-label">최신 데이터 (2024)</span>
                            <span className="metric-latest-val">{metric.latest}</span>
                          </div>

                          <div className="trend-section">
                            <div className="trend-section-title">감추이</div>
                            <div className="trend-chart-wrap">
                              <TrendChart trend={metric.trend} />
                            </div>
                          </div>

                          <div className="panel-subsection">
                            <div className="trend-section-title">
                              데이터 구성 ({metric.trend[metric.trend.length - 1].y})
                            </div>
                            <table className="breakdown-table">
                              <thead>
                                <tr>
                                  <th>구분</th>
                                  <th className="breakdown-val">값 ({metric.unit})</th>
                                </tr>
                              </thead>
                              <tbody>
                                {metric.breakdown.map((b, i) => (
                                  <tr key={i}>
                                    <td>{b.l}</td>
                                    <td className="breakdown-val">{b.v}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>

                          <div className="panel-subsection">
                            <div className="trend-section-title">계산식/산출 방식</div>
                            <div className="formula-box">
                              {metric.formula.split("\n").map((line, i, arr) => (
                                <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">AI 근거 생성</div>
                    <div className="ai-desc-box">{data.aiDesc}</div>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">관련 문단</div>
                    <div className="related-para-link">
                      <span className="related-para-label">{data.related.id} {data.related.label}</span>
                      <button className="related-para-btn">이동</button>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </main>

      <div className="sr-result-dashboard" id="dashboard">
        <div className="robot-view-container">
          <div id="particle-field" className="particle-field" ref={particleRef}></div>
        </div>
      </div>
    </div>
  );
};

export default Draft;
