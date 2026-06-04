import { useEffect, useRef, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import "@styles/media.css";
import robot from "@assets/images/robot/robot_media_t.png";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

// 정적 데이터 정의 (컴포넌트 외부에 두어 불필요한 재렌더링 방지)
const STEPS = [
  { id: 1, title: "벤치마킹 분석", icon: "🎯", path: "/benchmk" },
  { id: 2, title: "미디어 분석", icon: "📺", path: "/media" },
  { id: 3, title: "이해관계자 설문", icon: "👥", path: "/survey" },
  { id: 4, title: "전체 결과", icon: "📊", path: "/result" },
  { id: 5, title: "보고서 초안", icon: "📄", path: "/draft" },
];

const DASHBOARD_MOCK_DATA = {
  stats: {
    press: { count: "78건", sub: "관측 이슈 19건" },
    expert: { count: "4건", sub: "반영 이슈 6건" },
    regulation: { count: "4건", sub: "반영 이슈 6건" },
    total: { count: "29개" }
  },
  sourceTable: [
    { source: "언론 기사", count: "78건", issues: "19개", method: "실제 기사 기반" },
    { source: "전문 기관", count: "4건", issues: "6개", method: "고가중치 정성 보정" },
    { source: "규제 관례", count: "4건", issues: "12개", method: "고정 Rule Base" }
  ],
  topIssues: [
    { rank: 1, name: "온실가스 배출 감축", impact: "", financial: "9.7", source: "언론,규제" },
    { rank: 2, name: "에너지 전환/ 재생에너지 확대", impact: "9.7", financial: "7.6", source: "언론,전문가" },
    { rank: 3, name: "공급망 ESG 관리 강화", impact: "7.4", financial: "6.9", source: "언론,전문기관,규제" },
    { rank: 4, name: "정보공개 / 공시 투명성", impact: "7.2", financial: "4.3", source: "전문기관, 규제" },
    { rank: 5, name: "이사회 다양성 및 독립성", impact: "3.3", financial: "4.9", source: "전문기관" }
  ]
};

const REFLECT_METHODS = [
  {
    key: "press",
    title: "언론 기사",
    desc: "현대모비스/자동차부품 키워드 기반 기사 수집",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    )
  },
  {
    key: "expert",
    title: "전문기관",
    desc: "KCGS 등급 추세·기업지배구조보고서·KIS 자동차산업 평가방법론",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="3" y1="22" x2="21" y2="22" />
        <line x1="6" y1="18" x2="6" y2="11" />
        <line x1="10" y1="18" x2="10" y2="11" />
        <line x1="14" y1="18" x2="14" y2="11" />
        <line x1="18" y1="18" x2="18" y2="11" />
        <polygon points="12 2 2 7 22 7" />
      </svg>
    )
  },
  {
    key: "regulation",
    title: "규제",
    desc: "CSDDD·CBAM·CSRD·ESRS 기반 고정 점수 룰",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
    )
  }
];

const Media = () => {
  const navigate = useNavigate();
  const particleRef = useRef(null);
  const timerRef = useRef(null); // 분석용 타이머 Ref 선언

  const activeIndex = 1; // 미디어 분석 활성화

  // --- 상태 관리 (States) ---
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [loadingTitle, setLoadingTitle] = useState("미디어 수집 현황 대기 중");
  const [loadingDesc, setLoadingDesc] = useState("상단의 수집 시작 버튼을 누르면 실시간 크롤링 및 파싱이 가동됩니다.");
  const [selectedPress, setSelectedPress] = useState([]);
  const [selectedReg, setSelectedReg] = useState([]);
  const [selectedAge, setSelectedAge] = useState([]);





  const [status, setStatus] = useState({
    press: "ready",
    reg: "ready",
    expert: "ready",
  });

  const [formData, setFormData] = useState({
    pressKeyword: "",
    regOrg: "",
    expertOrg: "",
    pressStartDate: "",
    pressEndDate: "",
    regStartDate: "",
    regEndDate: "",
    expertStartDate: "",
    expertEndDate: "",
  });

  // --- 컴포넌트 언마운트 시 타이머 클리어 예방 조치 ---
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // --- 애니메이션 파티클 버블 효과 생성 함수 ---
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
      p.style.bottom = "0px";
      p.style.animationDelay = `${Math.random() * 2}s`;
      p.style.animationDuration = `${Math.random() * 2 + 2}s`;
      particleRef.current.appendChild(p);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const moveStep = (index) => {
    if (isAnalyzing) return;
    if (index === activeIndex) return;
    navigate(STEPS[index].path);
  };

  // --- 실시간 AI 분석 가동 프로세스 핸들러 ---
  const startMediaCollection = () => {
    if (isAnalyzing) return;

    // 데이터 유효성 검사 (Validation)
    if (selectedPress.length === 0) {
      showDefaultAlert("입력 오류", "언론사명 또는 키워드를 입력해주세요.", "warning");
      return;
    }
    if (selectedReg.length === 0) {
      showDefaultAlert("입력 오류", "규제 기관을 선택해주세요.", "warning");
      return;
    }
    if (selectedAge.length === 0) {
      showDefaultAlert("입력 오류", "평가 기관을 선택해주세요.", "warning");
      return;
    }

    // 수집 애니메이션 및 대시보드 상태 가동
    setIsAnalyzing(true);
    setDashboardOpen(true);
    setShowResult(false);
    createParticles(); // 파티클 실시간 재생성

    setStatus({
      press: "ing",
      reg: "ing",
      expert: "ready",
    });

    setLoadingTitle("실시간 크롤링 엔진 가동 중...");
    setLoadingDesc("네이버 뉴스 API 및 공공 데이터 포털 커넥터를 통해 웹 파싱을 실행하고 있습니다.");

    showDefaultAlert("분석 시작", "실시간 미디어 및 외부 데이터 수집을 시작합니다.", "success");

    // 2.5초 뒤 완료 시뮬레이션
    timerRef.current = setTimeout(() => {
      setStatus({
        press: "complete",
        reg: "complete",
        expert: "complete",
      });
      setShowResult(true);
      setIsAnalyzing(false);
    }, 2500);
  };

  const getStatusText = (type) => {
    if (type === "ready") return "수집 대기";
    if (type === "ing") return "수집 중";
    if (type === "complete") return "수집완료";
  };


  const addPress = (e) => {
    const val = e.target.value;
    if (val && !selectedPress.includes(val)) {
      setSelectedPress(prev => [...prev, val]);
    }
    e.target.value = ""; // 선택 후 드롭다운 초기화
  };

  const removePress = (name) => {
    setSelectedPress(prev => prev.filter(p => p !== name));
  };

  const addReg = (e) => {
    const val = e.target.value;
    if (val && !selectedReg.includes(val)) {
      setSelectedReg(prev => [...prev, val]);
    }
    e.target.value = "";
  };

  const removeReg = (name) => {
    setSelectedReg(prev => prev.filter(p => p !== name));
  };

  const addAge = (e) => {
    const val = e.target.value;
    if (val && !selectedAge.includes(val)) {
      setSelectedAge(prev => [...prev, val]);
    }
    e.target.value = "";
  };

  const removeAge = (name) => {
    setSelectedAge(prev => prev.filter(p => p !== name));
  };
  const today = new Date().toISOString().split("T")[0];

  return (
<<<<<<< HEAD
    <>
      <div className="media-container">
        {/* --- STEPPER HEADER --- */}
        <header className="media-header">
          <h1 className="media-title">지속가능경영보고서 AI 자동 생성</h1>
          <div className="media-stepper-row">
            {STEPS.map((step, index) => (
              <Fragment key={step.id}>
=======
    <div className="draft-container">
      <header className="draft-header">
        <h1 className="draft-title">
          지속가능경영보고서 AI 자동 생성
        </h1>

        <div className="draft-stepper-row">
          {steps.map((step, index) => (
            <div
              key={step.id}
              style={{
                display: "flex",
                alignItems: "center",
              }}
            >
              <div
                className={`step-box ${
                  index === activeIndex
                    ? "active"
                    : ""
                }`}
                onClick={() => moveStep(index)}
              >
                <div className="step-icon-circle">
                  {step.icon}
                </div>

>>>>>>> ea4795c (css&페이지 수정)
                <div
                  className={`step-box ${index === activeIndex ? "active" : ""}`}
                  onClick={() => moveStep(index)}
                  style={{ cursor: "pointer" }}
                >
                  <div className="step-icon-circle">{step.icon}</div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 800 }}>{step.title}</div>
                </div>
                {index < STEPS.length - 1 && <div className="step-line"></div>}
              </Fragment>
            ))}
          </div>
        </header>

        {/* --- FILTERS SETUP INPUT CARD --- */}
        <main className="main-content">
          <div className="media-input-card">
            <h2 style={{ fontSize: "1.4rem", fontWeight: 850, marginBottom: "6px", color: "#0f172a" }}>
              미디어 및 기관별 필터 수집 설정
            </h2>
            <p style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: "10px", lineHeight: 1.5 }}>
              언론사 뉴스, 정부 규제 데이터 및 ESG 전문기관의 평가 피드를 동기화하여 부정 위험성 및 공시 트렌드를 실시간 모니터링합니다.
            </p>

            <div className="media-setup-grid">
              {/* 카드 1: 언론 채널 */}
              <div className="media-card">
                <div className="media-badge">언론 채널</div>
                <div className="form-group" style={{ marginTop: "8px" }}>
                  <label>수집 언론사명</label>
                  <select className="media-select" onChange={addPress} defaultValue="">
                    <option value="">언론사 선택</option>
                    <option value="임팩트온">임팩트온</option>
                    <option value="ESG 경제">ESG 경제</option>
                  </select>
                  {selectedPress.length > 0 && (
                    <div style={{
                      display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px"
                    }}>
                      {selectedPress.map((name) => (
                        <span key={name} style={{
                          display: "inline-flex", alignItems: "center", gap: "4px",
                          padding: "3px 10px", background: "#f0fdf4",
                          border: "1px solid #bbf7d0", borderRadius: "20px",
                          fontSize: "0.78rem", fontWeight: 700, color: "#16a34a",
                        }}>
                          {name}
                          <button
                            onClick={() => removePress(name)}
                            style={{
                              background: "none", border: "none", cursor: "pointer",
                              color: "#94a3b8", fontSize: "0.75rem", padding: "0",
                              lineHeight: 1,
                            }}
                          >✕</button>
                        </span>
                      ))}
                    </div>
                  )}

                </div>
                <div className="form-group">
                  <label>수집 희망 기간</label>
                  <div className="date-range-group">
                    {/* 시작 날짜 - 2023-01-01 이후만 선택 가능 */}
                    <input type="date" name="pressStartDate" value={formData.pressStartDate} onChange={handleChange} min="2023-01-01" />
                    <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>~</span>
                    <input type="date" name="pressEndDate" value={formData.pressEndDate} onChange={handleChange} max={new Date().toISOString().split("T")[0]} />
                  </div>
                </div>
                <div className="status-container">
                  <span className="status-label">현재 상태</span>
                  <span className={`status-badge ${status.press}`}>{getStatusText(status.press)}</span>
                </div>
              </div>

              {/* 카드 2: 규제 기관 */}
              <div className="media-card">
                <div className="media-badge">규제 기관</div>
                <div className="form-group" style={{ marginTop: "8px" }}>
                  <label>정부 및 규제 데이터 소스</label>
                  <select className="media-select" onChange={addReg} defaultValue="">
                    <option value="">규제 기관 선택</option>
                    <option value="CBAM"> CBAM</option>
                    <option value="CSRS">CSRS</option>
                    <option value="ESRD">ESRD</option>
                    <option value="DPP">DPP</option>
                  </select>
                  {selectedReg.length > 0 && (
                    <div style={{
                      display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px"
                    }}>
                      {selectedReg.map((name) => (
                        <span key={name} style={{
                          display: "inline-flex", alignItems: "center", gap: "4px",
                          padding: "3px 10px", background: "#f0fdf4",
                          border: "1px solid #bbf7d0", borderRadius: "20px",
                          fontSize: "0.78rem", fontWeight: 700, color: "#16a34a",
                        }}>
                          {name}
                          <button
                            onClick={() => removeReg(name)}
                            style={{
                              background: "none", border: "none", cursor: "pointer",
                              color: "#94a3b8", fontSize: "0.75rem", padding: "0",
                              lineHeight: 1,
                            }}
                          >✕</button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* <div className="form-group">
                <label>대상 규제 제정 기간</label>
                <div className="date-range-group">
                  <input type="date" name="regStartDate" value={formData.regStartDate} onChange={handleChange} min="2023-01-01" />
                  <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>~</span>
                  <input type="date" name="regEndDate" value={formData.regEndDate} onChange={handleChange} max={new Date().toISOString().split("T")[0]}/>
                </div>
              </div> */}
                <div className="status-container">
                  <span className="status-label">현재 상태</span>
                  <span className={`status-badge ${status.reg}`}>{getStatusText(status.reg)}</span>
                </div>
              </div>

              {/* 카드 3: 전문 평가기관 */}
              <div className="media-card">
                <div className="media-badge">전문 평가기관</div>
                <div className="form-group" style={{ marginTop: "8px" }}>
                  <label>ESG 외부 평가/리서치 기관</label>
                  <select className="media-select" onChange={addAge} defaultValue="">
                    <option value="">평가 기관 선택</option>
                    <option value="MSCI">MSCI</option>
                    <option value="Sustainalytics">Sustainalytics</option>
                    <option value="한국ESG기준원">한국ESG기준원</option>
                  </select>
                  {selectedAge.length > 0 && (
                    <div style={{
                      display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px"
                    }}>
                      {selectedAge.map((name) => (
                        <span key={name} style={{
                          display: "inline-flex", alignItems: "center", gap: "4px",
                          padding: "3px 10px", background: "#f0fdf4",
                          border: "1px solid #bbf7d0", borderRadius: "20px",
                          fontSize: "0.78rem", fontWeight: 700, color: "#16a34a",
                        }}>
                          {name}
                          <button
                            onClick={() => removeAge(name)}
                            style={{
                              background: "none", border: "none", cursor: "pointer",
                              color: "#94a3b8", fontSize: "0.75rem", padding: "0",
                              lineHeight: 1,
                            }}
                          >✕</button>
                        </span>
                      ))}
                    </div>
                  )}

                </div>
                <div className="form-group">
                  <label>리포트 공시 기간</label>
                  <div className="date-range-group">
                    <input type="number" name="expertStartDate" value={formData.expertStartDate} onChange={handleChange} min="2020" max={new Date().getFullYear()} placeholder="시작 연도" style={{ width: "90px", padding: "6px 8px", border: "1px solid #e2e8f0", borderRadius: "8px", fontSize: "0.85rem" }} />
                    <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>~</span>
                    <input type="number" name="expertEndDate" value={formData.expertEndDate} onChange={handleChange} min="2020" max={new Date().getFullYear()} placeholder="종료 연도" style={{ width: "90px", padding: "6px 8px", border: "1px solid #e2e8f0", borderRadius: "8px", fontSize: "0.85rem" }} />
                  </div>
                </div>
                <div className="status-container">
                  <span className="status-label">현재 상태</span>
                  <span className={`status-badge ${status.expert}`}>{getStatusText(status.expert)}</span>
                </div>
              </div>
            </div>

<<<<<<< HEAD
            <div className="action-container">
              <button className="media-btn" onClick={startMediaCollection} style={{ marginBottom: "50px" }}>
                실시간 AI 분석 시작
              </button>
=======
          <div className="action-container">
            <button
              className="draft-btn"
              onClick={startMediaCollection}
              style={{marginBottom: "50px"}}
            >
              실시간 AI 분석 시작
            </button>
          </div>
        </div>
      </main>

      <div
        className={`draft-result-dashboard ${
          dashboardOpen ? "open" : ""
        }`}
      >
        <div
          className="dashboard-handle"
          onClick={() =>
            setDashboardOpen(
              !dashboardOpen
            )
          }
        >
          <div className="handle-pill">
            {isAnalyzing
              ? "AI 파이프라인 수집 가동 중..."
              : showResult
              ? "분석 완료 - 결과 요약 확인 (클릭)"
              : "빅데이터 연동 현황 확인하기 (클릭)"}
          </div>
        </div>

        <div className="robot-view-container">
          <div
            id="particle-field"
            ref={particleRef}
          ></div>

          <img
            src={robot}
            className="robot-main-img"
            alt="마스코트"
          />

          {!showResult ? (
            <div
              style={{
                textAlign: "center",
              }}
            >
              <h3
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 850,
                  margin: "0 0 4px 0",
                }}
              >
                {isAnalyzing
                  ? "실시간 크롤링 엔진 가동 중..."
                  : "미디어 수집 현황 대기 중"}
              </h3>

              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#64748b",
                  margin: 0,
                }}
              >
                {isAnalyzing
                  ? "AI 기반 외부 데이터 수집 엔진이 ESG 관련 미디어 및 기관 데이터를 분석하고 있습니다."
                  : "상단의 분석 시작 버튼을 누르면 AI 기반 외부 데이터 분석이 시작됩니다."}
              </p>
>>>>>>> ea4795c (css&페이지 수정)
            </div>
          </div>
        </main>

        <div className={`media-result-dashboard ${dashboardOpen ? "open" : ""} ${showResult ? "result-expanded" : ""}`}>

          {/* 핸들 버튼 - 항상 표시 */}
          <div
            className="dashboard-handle"
            onClick={() => setDashboardOpen(!dashboardOpen)}
            style={{ cursor: "pointer" }}
          >
            <div className={`handle-pill ${showResult ? "complete" : ""}`}>
              {isAnalyzing
                ? "AI 파이프라인 수집 가동 중..."
                : showResult
                  ? "분석 완료 - 결과 요약 확인 (클릭)"
                  : "빅데이터 연동 현황 확인하기"}
            </div>
          </div>

          {/* 대시보드 내용 - 분석 중이거나 결과 있을 때만 렌더링 */}
          {(dashboardOpen || isAnalyzing || showResult) && (
            <div className={`robot-view-container ${showResult ? "showing-result" : ""}`}>
              {/* 가동 애니메이션 파티클 필드 */}
              <div id="particle-field" ref={particleRef}></div>
              {!showResult && (
                <img src={robot} className="robot-main-img" alt="마스코트 로봇" style={{ alignSelf: "center" }} />
              )}
              {/* 수집 대기 및 로딩 중 안내판 */}
              {!showResult && (
                <div style={{ textAlign: "center" }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 850, margin: "0 0 4px 0" }}>{loadingTitle}</h3>
                  <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>{loadingDesc}</p>
                </div>
              )}

              {/* AI 분석 완료 후 노출될 데이터 레이아웃 영역 */}
              {showResult && (
                <div className="result-layout-content" style={{ width: "100%" }}>
                  {/* 결과 배너 */}
                  <div className="result-banner">
                    <div className="result-banner-left">
                      <div className="result-banner-title" style={{ textAlign: "center", alignSelf: "center" }}>
                        [AI 미디어 시그널 분석 결과]
                      </div>
                      <p className="result-banner-desc">
                        언론 기사, 전문기관 자료, 핵심규제 프레임을 종합 반영하여<br />
                        외부 시그널 기반의 주요 서브이슈를 도출했습니다.
                      </p>
                    </div>
                    {/* 로봇 이미지 우측 배치 */}
                    <img
                      src={robot}
                      alt="마스코트 로봇"
                      style={{ height: "120px", width: "auto", flexShrink: 0, marginLeft: "16px" }}
                    />
                  </div>

                  {/* 통계 카드 4개 */}

                  <div className="result-stats-row">
                    <div className="result-stat-card">
                      <div className="stat-icon-wrap">📰</div>
                      <div>
                        <div className="stat-label">언론 기사</div>
                        <div className="stat-value">{DASHBOARD_MOCK_DATA.stats.press.count}</div>
                        <div className="stat-sub">{DASHBOARD_MOCK_DATA.stats.press.sub}</div>
                      </div>
                    </div>
                    <div className="result-stat-card">
                      <div className="stat-icon-wrap">🏛️</div>
                      <div>
                        <div className="stat-label">전문기관 자료</div>
                        <div className="stat-value">{DASHBOARD_MOCK_DATA.stats.expert.count}</div>
                        <div className="stat-sub">{DASHBOARD_MOCK_DATA.stats.expert.sub}</div>
                      </div>
                    </div>
                    <div className="result-stat-card">
                      <div className="stat-icon-wrap">⚖️</div>
                      <div>
                        <div className="stat-label">규제 프레임</div>
                        <div className="stat-value">{DASHBOARD_MOCK_DATA.stats.regulation.count}</div>
                        <div className="stat-sub">{DASHBOARD_MOCK_DATA.stats.regulation.sub}</div>
                      </div>
                    </div>
                    <div className="result-stat-card">
                      <div className="stat-icon-wrap">🔗</div>
                      <div>
                        <div className="stat-label">반영 방식 안내</div>
                        <div className="stat-value">{DASHBOARD_MOCK_DATA.stats.total.count}</div>
                      </div>
                    </div>
                  </div>

                  {/* 하단 3패널 */}
                  <div className="result-panels-row">
                    {/* 패널1: Source 별 반영 현황 */}
                    <div className="result-panel">
                      <div className="panel-header-row">
                        <span className="panel-title">Source 별 반영 현황</span>
                        <span className="panel-info-btn">ⓘ</span>
                      </div>
                      <table className="issue-table">
                        <thead>
                          <tr>
                            <th>Source</th><th>수집·기준 건수</th><th>반영 이슈</th><th>적용 방식</th>
                          </tr>
                        </thead>
                        <tbody>
                          {DASHBOARD_MOCK_DATA.sourceTable.map((row, i) => (
                            <tr key={i}>
                              <td>{row.source}</td>
                              <td>{row.count}</td>
                              <td>{row.issues}</td>
                              <td>{row.method}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* 패널2: 미디어 TOP 이슈 점수 */}
                    <div className="result-panel">
                      <div className="panel-header-row">
                        <span className="panel-title">미디어 TOP 이슈 점수</span>
                        <span className="panel-info-btn">ⓘ</span>
                      </div>
                      <table className="issue-table">
                        <thead>

                        </thead>
                        <tbody>
                          {DASHBOARD_MOCK_DATA.topIssues.map((item) => (
                            <tr key={item.rank}>
                              <td>{item.rank}</td>
                              <td>{item.name}</td>
                              <td>{item.impact}</td>
                              <td>{item.financial}</td>
                              <td>{item.source}</td>
                              <td>

                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* 패널3: 반영 방식 안내 */}
                    <div className="result-panel">
                      <div className="panel-header-row">
                        <span className="panel-title">반영 방식 안내</span>
                        <span className="panel-info-btn">ⓘ</span>
                      </div>
                      <ul className="reflect-list">
                        {REFLECT_METHODS.map((item) => (
                          <li key={item.key} className="reflect-item">
                            <div className="reflect-icon">{item.icon}</div>
                            <div>
                              <div className="reflect-title">{item.title}</div>
                              <p className="reflect-desc">{item.desc}</p>
                            </div>
                          </li>
                        ))}
                      </ul>
                      <div className="reflect-note">ⓘ 향후 MSCI·S&P·EcoVadis 등 외부 평가기관 자료 확장 가능</div>
                    </div>
                  </div>

                  {/* 다음 단계 알림 가이드 가이드바 */}
                  {STEPS[activeIndex + 1] && (
                    <div style={{ textAlign: "center", marginTop: "25px", color: "#64748b", fontSize: "0.9rem" }}>
                      다음 단계 가이드: <strong>{STEPS[activeIndex + 1].title}</strong> 진행이 가능합니다.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>

  );
}
export default Media;