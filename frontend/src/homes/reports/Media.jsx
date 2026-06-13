import { useEffect, useRef, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import "@styles/media.css";
import robot from "@assets/images/robot/robot_media_t.png";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const IS_DUMMY = true;

// 정적 데이터 정의 (컴포넌트 외부에 두어 불필요한 재렌더링 방지)
const STEPS = [
  { id: 1, title: "벤치마킹 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7" /><line x1="15.5" y1="15.5" x2="21" y2="21" /><line x1="7" y1="13" x2="7" y2="11" /><line x1="10" y1="13" x2="10" y2="8.5" /><line x1="13" y1="13" x2="13" y2="7" /><line x1="6" y1="13" x2="14" y2="13" /></svg>, path: "/benchmk" },
  { id: 2, title: "미디어 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /><polyline points="5,13 8,10 11,12 14,8 19,6" /></svg>, path: "/media" },
  { id: 3, title: "이해관계자 설문", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" /><line x1="13" y1="11" x2="16" y2="11" /><line x1="13" y1="16" x2="16" y2="16" /></svg>, path: "/survey" },
  { id: 4, title: "전체 결과", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="20" x2="21" y2="20" /><line x1="3" y1="4" x2="3" y2="20" /><rect x="5" y="13" width="3" height="7" /><rect x="10" y="10" width="3" height="10" /><rect x="15" y="8" width="3" height="12" /><circle cx="19" cy="4" r="3" /><polyline points="17.5,4 18.5,5 21,2.5" /></svg>, path: "/result" },
  { id: 5, title: "보고서 초안", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" /></svg>, path: "/draft" },
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

// 규제 기관 Source 정의: CBAM / CSRD / DPP만 사용한다. CSRS/ESRD는 사용 금지.
const REGULATION_SOURCES = [
  { key: "CBAM", label: "CBAM", desc: "EU 탄소국경조정제도" },
  { key: "CSRD", label: "CSRD", desc: "EU 기업 지속가능성 공시지침\nESRS 기준 포함" },
  { key: "DPP", label: "DPP", desc: "EU 디지털 제품 여권" },
];

// 전문기관 설정: 현재 Rule Logic이 존재하는 KCGS와 KIS만 선택 가능하다. Sustainalytics/MSCI 제거.
const INSTITUTION_OPTIONS = [
  { key: "kcgs", label: "한국ESG기준원", desc: "KCGS ESG 등급 추이\nPre-Survey Boost" },
  { key: "kis", label: "한국신용평가", desc: "자동차산업 평가방법론\nFinancial Resilience Screening" },
];

// ── Tab Icon SVG Components ──
const TabIcons = {
  press: (color) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  regulation: (color) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  ),
  institution: (color) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="22" x2="21" y2="22" />
      <line x1="6" y1="18" x2="6" y2="11" />
      <line x1="10" y1="18" x2="10" y2="11" />
      <line x1="14" y1="18" x2="14" y2="11" />
      <line x1="18" y1="18" x2="18" y2="11" />
      <polygon points="12 2 2 7 22 7" />
    </svg>
  ),
};

const Media = () => {
  const navigate = useNavigate();
  const particleRef = useRef(null);
  const timerRef = useRef(null);

  const activeIndex = 1;

  // --- 상태 관리 (States) ---
  const [activeSourceTab, setActiveSourceTab] = useState("press");
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingTitle, setLoadingTitle] = useState("미디어 수집 현황 대기 중");
  const [loadingDesc, setLoadingDesc] = useState("상단의 수집 시작 버튼을 누르면 실시간 크롤링 및 파싱이 가동됩니다.");

  const [selectedPress, setSelectedPress] = useState([]);
  const [selectedReg, setSelectedReg] = useState([]);
  const [selectedInstitutions, setSelectedInstitutions] = useState([]);

  // KIS Modal State
  const [isKisModalOpen, setIsKisModalOpen] = useState(false);
  const [kisData, setKisData] = useState({
    company: "A_GROUP",
    provider: "KIS",
    analysisType: "재무 위험지표 Export",
    baseYear: "2025",
    indicators: [
      { id: 1, name: "부채비율", y2023: "138.0", y2024: "152.5", y2025: "166.2", unit: "%" },
      { id: 2, name: "이자보상배율", y2023: "5.2", y2024: "3.7", y2025: "2.9", unit: "x" },
      { id: 3, name: "영업이익률", y2023: "8.1", y2024: "6.4", y2025: "5.1", unit: "%" }
    ]
  });

  const handleKisDataChange = (field, value) => {
    setKisData(prev => ({ ...prev, [field]: value }));
  };

  const handleKisIndicatorChange = (id, year, value) => {
    setKisData(prev => ({
      ...prev,
      indicators: prev.indicators.map(ind =>
        ind.id === id ? { ...ind, [year]: value } : ind
      )
    }));
  };

  const handleKisSubmit = () => {
    setIsKisModalOpen(false);
    if (!selectedInstitutions.includes("kis")) {
      setSelectedInstitutions(prev => [...prev, "kis"]);
    }
  };

  // KCGS Modal State
  const [isKcgsModalOpen, setIsKcgsModalOpen] = useState(false);
  const [kcgsData, setKcgsData] = useState({
    company: "A_GROUP",
    provider: "KCGS",
    analysisType: "ESG 등급 추이",
    inputBasis: "최근 공표 기준 3개년",
    grades: [
      { year: "2023", total: "B+", e: "B+", s: "B", g: "A" },
      { year: "2024", total: "B+", e: "B", s: "B+", g: "A" },
      { year: "2025", total: "A", e: "A", s: "B+", g: "A" }
    ]
  });

  const handleKcgsDataChange = (field, value) => {
    setKcgsData(prev => ({ ...prev, [field]: value }));
  };

  const handleKcgsGradeChange = (year, field, value) => {
    setKcgsData(prev => ({
      ...prev,
      grades: prev.grades.map(grade =>
        grade.year === year ? { ...grade, [field]: value } : grade
      )
    }));
  };

  const handleKcgsSubmit = () => {
    setIsKcgsModalOpen(false);
    if (!selectedInstitutions.includes("kcgs")) {
      setSelectedInstitutions(prev => [...prev, "kcgs"]);
    }
  };

  const [status, setStatus] = useState({
    press: "ready",
    reg: "ready",
    expert: "ready",
  });

  const [formData, setFormData] = useState({
    pressStartDate: "",
    pressEndDate: "",
  });

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    let interval;
    if (isAnalyzing) {
      interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            setStatus({ press: "complete", reg: "complete", expert: "complete" });
            setShowResult(true);
            setIsAnalyzing(false);
            return 100;
          }
          return prev + 2;
        });
      }, 50);
    }
    return () => clearInterval(interval);
  }, [isAnalyzing]);

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

  const startMediaCollection = () => {
    if (isAnalyzing) return;

    if (selectedPress.length === 0) {
      showDefaultAlert("입력 오류", "수집 언론사를 선택해주세요.", "warning");
      return;
    }
    if (!formData.pressStartDate) {
      showDefaultAlert("입력 오류", "수집 시작일을 선택해주세요.", "warning");
      return;
    }
    if (!formData.pressEndDate) {
      showDefaultAlert("입력 오류", "수집 종료일을 선택해주세요.", "warning");
      return;
    }
    if (formData.pressStartDate > formData.pressEndDate) {
      showDefaultAlert("입력 오류", "수집 시작일이 종료일보다 늦습니다.", "warning");
      return;
    }
    if (selectedReg.length === 0) {
      showDefaultAlert("입력 오류", "규제 기관을 선택해주세요.", "warning");
      return;
    }
    if (selectedInstitutions.length === 0) {
      showDefaultAlert("입력 오류", "전문 평가기관을 선택해주세요.", "warning");
      return;
    }

    setIsAnalyzing(true);
    setDashboardOpen(true);
    setShowResult(false);
    createParticles();

    setStatus({
      press: "ing",
      reg: "ing",
      expert: "ready",
    });

    setLoadingTitle("실시간 크롤링 엔진 가동 중...");
    setLoadingDesc("네이버 뉴스 API 및 공공 데이터 포털 커넥터를 통해 웹 파싱을 실행하고 있습니다.");

    setProgress(0);
    showDefaultAlert("분석 시작", "실시간 미디어 및 외부 데이터 수집을 시작합니다.", "success");
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
    e.target.value = "";
  };

  const removePress = (name) => {
    setSelectedPress(prev => prev.filter(p => p !== name));
  };

  const toggleReg = (key) => {
    setSelectedReg(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const toggleInst = (key) => {
    if (key === "kis" && !selectedInstitutions.includes("kis")) {
      setIsKisModalOpen(true);
      return;
    }
    if (key === "kcgs" && !selectedInstitutions.includes("kcgs")) {
      setIsKcgsModalOpen(true);
      return;
    }
    setSelectedInstitutions(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const pressReady = selectedPress.length > 0 && formData.pressStartDate && formData.pressEndDate;
  const regulationReady = selectedReg.length > 0;
  const institutionReady = selectedInstitutions.length > 0;

  const today = new Date().toISOString().split("T")[0];

  const pressLabelMap = { impacton: "임팩트온", esgeconomy: "ESG경제" };
  const institutionLabelMap = {};
  INSTITUTION_OPTIONS.forEach(opt => { institutionLabelMap[opt.key] = opt.label; });

  return (
    <>
      <div className="media-container">
        <header className="media-header">
          <div className="media-stepper-row">
            {STEPS.map((step, index) => (
              <Fragment key={step.id}>
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

        <main className="media-main-content">
          {/* 전체 콘텐츠를 감싸고, 중앙 정렬 & 최대 너비 부여 */}
          <div className="media-input-card">
            <div style={{ marginBottom: "18px" }}>
              <h2 style={{ fontSize: "1.4rem", fontWeight: 850, marginBottom: "6px", color: "#0f172a" }}>
                미디어 및 기관별 필터 수집 설정
              </h2>
              <p style={{ color: "#64748b", fontSize: "0.9rem", margin: 0, lineHeight: 1.5 }}>
                언론사 뉴스, 정부 규제 데이터 및 ESG 전문기관의 평가 피드를 동기화하여 부정 위험성 및 공시 트렌드를 실시간 모니터링합니다.
              </p>
            </div>

            <div className="media-compact-workspace" style={{ width: "100%", textAlign: "left" }}>
              {/* 좌측 패널 */}
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                <div className="media-compact-tabs">
                  {[
                    { key: "press", label: "언론 채널", icon: TabIcons.press },
                    { key: "regulation", label: "규제 기관", icon: TabIcons.regulation },
                    { key: "institution", label: "전문 평가기관", icon: TabIcons.institution },
                  ].map(tab => {
                    const isActive = activeSourceTab === tab.key;
                    const color = isActive ? "#03A94D" : "#94a3b8";
                    return (
                      <button
                        key={tab.key}
                        type="button"
                        className={`media-compact-tab ${isActive ? "active" : ""}`}
                        onClick={() => setActiveSourceTab(tab.key)}
                      >
                        {tab.icon(color)}
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                {/* 언론 채널 폼 */}
                {activeSourceTab === "press" && (
                  <div className="media-compact-card">
                    <div className="media-press-layout">
                      <div className="form-group">
                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", fontWeight: 700, color: "#475569", marginBottom: "6px" }}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
                          1. 수집 언론사명
                        </label>
                        <select className="media-compact-input" onChange={addPress} defaultValue="">
                          <option value="">언론사 선택</option>
                          <option value="impacton">임팩트온</option>
                          <option value="esgeconomy">ESG경제</option>
                        </select>
                        {selectedPress.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                            {selectedPress.map((key) => (
                              <span key={key} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "3px 10px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "20px", fontSize: "0.78rem", fontWeight: 700, color: "#16a34a" }}>
                                {pressLabelMap[key] || key}
                                <button onClick={() => removePress(key)} style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8", fontSize: "0.75rem", padding: "0", lineHeight: 1 }}>✕</button>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="form-group">
                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", fontWeight: 700, color: "#475569", marginBottom: "6px" }}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
                          2. 수집 희망 기간
                        </label>
                        <div className="media-press-date-row">
                          <input className="media-compact-input" type="date" name="pressStartDate" value={formData.pressStartDate} onChange={handleChange} min="2023-01-01" max={today} />
                          <span style={{ color: "#94a3b8", fontSize: "0.8rem", textAlign: "center" }}>~</span>
                          <input className="media-compact-input" type="date" name="pressEndDate" value={formData.pressEndDate} onChange={handleChange} min="2023-01-01" max={today} />
                        </div>
                      </div>
                    </div>

                    <div className="status-container" style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px dashed #e2e8f0" }}>
                      <span className="status-label">현재 상태</span>
                      <span className={`status-badge ${status.press}`}>{getStatusText(status.press)}</span>
                    </div>
                  </div>
                )}

                {/* 규제 기관 폼 */}
                {activeSourceTab === "regulation" && (
                  <div className="media-compact-card">
                    <div className="form-group">
                      <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", fontWeight: 700, color: "#475569", marginBottom: "8px" }}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
                        1. 규제 기관 출처 선택
                        <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: 400 }}>(복수 선택 가능)</span>
                      </label>
                      <div className="media-toggle-grid-3">
                        {REGULATION_SOURCES.map(src => {
                          const isSelected = selectedReg.includes(src.key);
                          return (
                            <div
                              key={src.key}
                              className={`media-toggle-card ${isSelected ? "active" : ""}`}
                              onClick={() => toggleReg(src.key)}
                            >
                              <span className="media-toggle-card-label">{src.label}</span>
                              <span className="media-toggle-card-desc" style={{ whiteSpace: "pre-line" }}>{src.desc}</span>
                              {isSelected && <span className="media-toggle-check">✓</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="status-container" style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px dashed #e2e8f0" }}>
                      <span className="status-label">현재 상태</span>
                      <span className={`status-badge ${regulationReady ? "complete" : "ready"}`}>
                        {regulationReady ? "규제 선택 완료" : "규제 선택 대기"}
                      </span>
                    </div>
                  </div>
                )}

                {/* 전문 평가기관 폼 */}
                {activeSourceTab === "institution" && (
                  <div className="media-compact-card">
                    <div className="form-group">
                      <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", fontWeight: 700, color: "#475569", marginBottom: "8px" }}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="22" x2="21" y2="22" /><line x1="6" y1="18" x2="6" y2="11" /><line x1="10" y1="18" x2="10" y2="11" /><line x1="14" y1="18" x2="14" y2="11" /><line x1="18" y1="18" x2="18" y2="11" /><polygon points="12 2 2 7 22 7" /></svg>
                        1. 평가 기관 선택
                        <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: 400 }}>(복수 선택 가능)</span>
                      </label>
                      <div className="media-toggle-grid-2">
                        {INSTITUTION_OPTIONS.map(src => {
                          const isSelected = selectedInstitutions.includes(src.key);
                          return (
                            <div
                              key={src.key}
                              className={`media-toggle-card ${isSelected ? "active" : ""}`}
                              onClick={() => toggleInst(src.key)}
                            >
                              <span className="media-toggle-card-label">{src.label}</span>
                              <span className="media-toggle-card-desc" style={{ whiteSpace: "pre-line" }}>{src.desc}</span>
                              {isSelected && <span className="media-toggle-check">✓</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="status-container" style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px dashed #e2e8f0" }}>
                      <span className="status-label">현재 상태</span>
                      <span className={`status-badge ${institutionReady ? "complete" : "ready"}`}>
                        {institutionReady ? "기관 선택 완료" : "기관 선택 대기"}
                      </span>
                    </div>
                  </div>
                )}

                {/* 체크리스트 및 CTA 버튼 */}
                <div className="media-checklist-wrapper" style={{ marginTop: "auto", marginBottom: "0" }}>
                  <div className="media-checklist-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" /></svg>
                    분석 준비 체크리스트
                  </div>
                  <div style={{ display: "flex", gap: "12px", alignItems: "stretch" }}>
                    <div className="media-checklist-grid" style={{ flex: 1 }}>
                      {[
                        { label: "언론사 선택", done: selectedPress.length > 0 },
                        { label: "수집 기간 설정", done: !!(formData.pressStartDate && formData.pressEndDate) },
                        { label: "규제 데이터 소스", done: regulationReady },
                        { label: "전문 평가기관 선택", done: institutionReady },
                      ].map(item => (
                        <div key={item.label} className={`media-checklist-card ${item.done ? "done" : "pending"}`}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={item.done ? "#03A94D" : "#94a3b8"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          <span className="checklist-card-label" style={{ color: item.done ? "#1e293b" : "#94a3b8" }}>{item.label}</span>
                          <span className={`checklist-card-badge ${item.done ? "done" : "pending"}`}>
                            {item.done ? "완료" : "설정 필요"}
                          </span>
                        </div>
                      ))}
                    </div>
                    {/* CTA 버튼 (체크리스트 바로 우측) */}
                    <div className="media-cta-wrapper" style={{ margin: 0, display: "flex", alignItems: "stretch" }}>
                      <button className="Bench-btn" onClick={startMediaCollection} style={{ margin: 0, height: "100%", padding: "0 24px", whiteSpace: "nowrap" }}>
                        실시간 AI 분석 시작
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* 우측 패널 */}
              <div className="media-summary-col">
                <div className="media-summary-card">
                  <div className="media-summary-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /></svg>
                    선택 요약
                  </div>
                  <div className="media-summary-row">
                    <span style={{ color: "#64748b", fontWeight: 600 }}>언론 채널</span>
                    <span style={{ color: "#1e293b", fontWeight: 700 }}>
                      {selectedPress.length > 0 ? selectedPress.map(k => pressLabelMap[k] || k).join(", ") : <span style={{ color: "#94a3b8" }}>미선택</span>}
                    </span>
                  </div>
                  <div className="media-summary-row">
                    <span style={{ color: "#64748b", fontWeight: 600 }}>수집 기간</span>
                    <span style={{ color: "#1e293b", fontWeight: 700 }}>
                      {formData.pressStartDate && formData.pressEndDate ? `${formData.pressStartDate} ~ ${formData.pressEndDate}` : <span style={{ color: "#94a3b8" }}>미설정</span>}
                    </span>
                  </div>
                  <div className="media-summary-row">
                    <span style={{ color: "#64748b", fontWeight: 600 }}>규제 기관</span>
                    <span style={{ color: "#1e293b", fontWeight: 700, display: "flex", flexWrap: "wrap", gap: "4px", justifyContent: "flex-end" }}>
                      {selectedReg.length > 0 ? selectedReg.map(k => <span key={k} style={{ padding: "2px 8px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "10px", fontSize: "0.72rem", color: "#16a34a" }}>{k}</span>) : <span style={{ color: "#94a3b8" }}>미선택</span>}
                    </span>
                  </div>
                  <div className="media-summary-row">
                    <span style={{ color: "#64748b", fontWeight: 600 }}>전문 평가기관</span>
                    <span style={{ color: "#1e293b", fontWeight: 700, display: "flex", flexWrap: "wrap", gap: "4px", justifyContent: "flex-end" }}>
                      {selectedInstitutions.length > 0 ? selectedInstitutions.map(k => <span key={k} style={{ padding: "2px 8px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "10px", fontSize: "0.72rem", color: "#16a34a" }}>{institutionLabelMap[k] || k}</span>) : <span style={{ color: "#94a3b8" }}>미선택</span>}
                    </span>
                  </div>
                </div>

                <div className="media-summary-card">
                  <div className="media-summary-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                    미디어 분석 진행 상태
                  </div>

                  <div className="media-summary-row">
                    <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569", fontWeight: 600 }}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={(isAnalyzing || showResult) ? "#03A94D" : (pressReady && regulationReady && institutionReady ? "#03A94D" : "#94a3b8")} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      준비 단계
                    </span>
                    <span style={{ fontWeight: 700, color: (isAnalyzing || showResult) ? "#15803d" : (pressReady && regulationReady && institutionReady ? "#15803d" : "#94a3b8") }}>
                      {(isAnalyzing || showResult) ? "완료" : (pressReady && regulationReady && institutionReady ? "준비 완료" : "대기 중")}
                    </span>
                  </div>

                  <div className="media-summary-row">
                    <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569", fontWeight: 600 }}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={status.press === "complete" ? "#03A94D" : status.press === "ing" ? "#0284c7" : "#94a3b8"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      기사 수집 단계
                    </span>
                    <span style={{ fontWeight: 700, color: status.press === "complete" ? "#15803d" : status.press === "ing" ? "#0284c7" : "#94a3b8" }}>
                      {status.press === "complete" ? "완료" : status.press === "ing" ? "수집 중" : "대기 중"}
                    </span>
                  </div>

                  <div className="media-summary-row">
                    <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569", fontWeight: 600 }}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={status.reg === "complete" ? "#03A94D" : status.reg === "ing" ? "#0284c7" : "#94a3b8"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      규제 분석 상태
                    </span>
                    <span style={{ fontWeight: 700, color: status.reg === "complete" ? "#15803d" : status.reg === "ing" ? "#0284c7" : "#94a3b8" }}>
                      {status.reg === "complete" ? "완료" : status.reg === "ing" ? "분석 중" : "대기 중"}
                    </span>
                  </div>

                  <div className="media-summary-row">
                    <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569", fontWeight: 600 }}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={status.expert === "complete" ? "#03A94D" : status.expert === "ing" ? "#0284c7" : "#94a3b8"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      전문 평가기관 분석 상태
                    </span>
                    <span style={{ fontWeight: 700, color: status.expert === "complete" ? "#15803d" : status.expert === "ing" ? "#0284c7" : "#94a3b8" }}>
                      {status.expert === "complete" ? "완료" : status.expert === "ing" ? "분석 중" : "대기 중"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>

        {/* ── 기존 Bottom Result Dashboard (유지) ── */}
        <div className={`media-result-dashboard ${dashboardOpen ? "open" : ""} ${showResult ? "result-expanded" : ""}`}>
          <div className="dashboard-handle" onClick={() => setDashboardOpen(!dashboardOpen)}>
            <div className={`handle-pill ${showResult ? "complete" : ""}`}>
              {isAnalyzing ? "AI 파이프라인 수집 가동 중..." : showResult ? "분석 완료 - 결과 요약 확인 (클릭)" : "실시간 분석 대기 중"}
            </div>
          </div>
          {(dashboardOpen || isAnalyzing || showResult) && (
            <div className={`robot-view-container ${showResult ? "showing-result" : ""}`}>
              <div id="particle-field" ref={particleRef}></div>
              {!showResult && <img src={robot} className="robot-media-main-img" alt="마스코트 로봇" />}
              {!showResult && (
                <div style={{ textAlign: "center", zIndex: 3 }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 850, margin: "0 0 4px 0" }}>{loadingTitle}</h3>
                  <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>{loadingDesc}</p>
                  {isAnalyzing && (
                    <div className="progress-section" style={{ margin: "12px auto 0" }}>
                      <div className="progress-bar-wrap">
                        <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
                      </div>
                      <div style={{ marginTop: "6px", fontWeight: 900, fontSize: "0.85rem", color: "var(--media-primary)" }}>
                        {progress}% 분석 중
                      </div>
                    </div>
                  )}
                </div>
              )}
              {showResult && (
                <div className="result-layout-content" style={{ width: "100%", zIndex: 3 }}>
                  <div className="result-banner" style={{ background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div className="result-banner-left">
                      <div className="result-banner-title" style={{ textAlign: "center", alignSelf: "center" }}>
                        [AI 미디어 시그널 분석 결과]
                      </div>
                      <p className="result-banner-desc">
                        언론 기사, 전문기관 자료, 핵심규제 프레임을 종합 반영하여<br />
                        외부 시그널 기반의 주요 서브이슈를 도출했습니다.
                      </p>
                    </div>
                  </div>
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
                  <div className="result-panels-row">
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
                    <div className="result-panel">
                      <div className="panel-header-row">
                        <span className="panel-title">미디어 TOP 이슈 점수</span>
                        <span className="panel-info-btn">ⓘ</span>
                      </div>
                      <table className="issue-table">
                        <thead></thead>
                        <tbody>
                          {DASHBOARD_MOCK_DATA.topIssues.map((item) => (
                            <tr key={item.rank}>
                              <td>{item.rank}</td>
                              <td>{item.name}</td>
                              <td>{item.impact}</td>
                              <td>{item.financial}</td>
                              <td>{item.source}</td>
                              <td></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
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

        {isKisModalOpen && (
          <div className="media-modal-overlay">
            <div className="media-modal-content">
              <div className="media-modal-header">
                <button className="media-modal-close" onClick={() => setIsKisModalOpen(false)}>✕</button>
                <h3 className="media-modal-title">한국신용평가 입력</h3>
              </div>

              <div className="media-modal-body">
                <div className="media-modal-section">
                  <div className="media-modal-section-title">1. 기본 정보</div>
                  <div className="media-modal-grid">
                    <div className="media-modal-field">
                      <label className="media-modal-label">회사</label>
                      <input type="text" className="media-modal-input" value={kisData.company} onChange={(e) => handleKisDataChange("company", e.target.value)} />
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">제공기관</label>
                      <input type="text" className="media-modal-input" value={kisData.provider} readOnly />
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">분석 유형</label>
                      <select className="media-modal-select" value={kisData.analysisType} onChange={(e) => handleKisDataChange("analysisType", e.target.value)}>
                        <option value="재무 위험지표 Export">재무 위험지표 Export</option>
                      </select>
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">기준연도</label>
                      <input type="number" className="media-modal-input" value={kisData.baseYear} onChange={(e) => handleKisDataChange("baseYear", e.target.value)} />
                    </div>
                  </div>
                </div>

                <div className="media-modal-section">
                  <div className="media-modal-section-title">2. 재무 위험지표 입력</div>
                  <table className="media-modal-table">
                    <thead>
                      <tr>
                        <th style={{ width: "25%", textAlign: "left", paddingLeft: "16px" }}>지표명</th>
                        <th>2023</th>
                        <th>2024</th>
                        <th>2025</th>
                        <th style={{ width: "15%" }}>단위</th>
                      </tr>
                    </thead>
                    <tbody>
                      {kisData.indicators.map(ind => (
                        <tr key={ind.id}>
                          <td style={{ textAlign: "left", fontWeight: "600", color: "#475569", paddingLeft: "16px" }}>{ind.name}</td>
                          <td><input type="number" step="0.1" className="media-table-input" value={ind.y2023} onChange={(e) => handleKisIndicatorChange(ind.id, "y2023", e.target.value)} /></td>
                          <td><input type="number" step="0.1" className="media-table-input" value={ind.y2024} onChange={(e) => handleKisIndicatorChange(ind.id, "y2024", e.target.value)} /></td>
                          <td><input type="number" step="0.1" className="media-table-input" value={ind.y2025} onChange={(e) => handleKisIndicatorChange(ind.id, "y2025", e.target.value)} /></td>
                          <td className="media-table-unit">{ind.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="media-modal-footer">
                <button className="media-modal-btn cancel" onClick={() => setIsKisModalOpen(false)}>취소</button>
                <button className="media-modal-btn draft">임시저장</button>
                <button className="media-modal-btn submit" onClick={handleKisSubmit}>입력 완료</button>
              </div>
            </div>
          </div>
        )}

        {isKcgsModalOpen && (
          <div className="media-modal-overlay">
            <div className="media-modal-content">
              <div className="media-modal-header">
                <button className="media-modal-close" onClick={() => setIsKcgsModalOpen(false)}>✕</button>
                <h3 className="media-modal-title">한국ESG기준원 입력</h3>
                <p className="media-modal-subtitle">KCGS ESG 등급 추이</p>
              </div>

              <div className="media-modal-body">
                <div className="media-modal-section">
                  <div className="media-modal-section-title">1. 기본 정보</div>
                  <div className="media-modal-grid">
                    <div className="media-modal-field">
                      <label className="media-modal-label">회사</label>
                      <input type="text" className="media-modal-input" value={kcgsData.company} onChange={(e) => handleKcgsDataChange("company", e.target.value)} />
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">제공기관</label>
                      <input type="text" className="media-modal-input" value={kcgsData.provider} readOnly />
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">분석 유형</label>
                      <select className="media-modal-select" value={kcgsData.analysisType} onChange={(e) => handleKcgsDataChange("analysisType", e.target.value)}>
                        <option value="ESG 등급 추이">ESG 등급 추이</option>
                      </select>
                    </div>
                    <div className="media-modal-field">
                      <label className="media-modal-label">입력 기준</label>
                      <select className="media-modal-select" value={kcgsData.inputBasis} onChange={(e) => handleKcgsDataChange("inputBasis", e.target.value)}>
                        <option value="최근 공표 기준 3개년">최근 공표 기준 3개년</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="media-modal-section">
                  <div className="media-modal-section-title">2. 등급 입력</div>
                  <table className="media-modal-table">
                    <thead>
                      <tr>
                        <th style={{ width: "20%", paddingLeft: "16px" }}>평가연도</th>
                        <th style={{ width: "20%" }}>종합</th>
                        <th style={{ width: "20%" }}>E</th>
                        <th style={{ width: "20%" }}>S</th>
                        <th style={{ width: "20%" }}>G</th>
                      </tr>
                    </thead>
                    <tbody>
                      {kcgsData.grades.map(grade => (
                        <tr key={grade.year}>
                          <td style={{ fontWeight: "600", color: "#475569", paddingLeft: "16px" }}>{grade.year}</td>
                          <td>
                            <select className="media-table-select" value={grade.total} onChange={(e) => handleKcgsGradeChange(grade.year, "total", e.target.value)}>
                              {["S", "A+", "A", "B+", "B", "C", "D"].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          </td>
                          <td>
                            <select className="media-table-select" value={grade.e} onChange={(e) => handleKcgsGradeChange(grade.year, "e", e.target.value)}>
                              {["S", "A+", "A", "B+", "B", "C", "D"].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          </td>
                          <td>
                            <select className="media-table-select" value={grade.s} onChange={(e) => handleKcgsGradeChange(grade.year, "s", e.target.value)}>
                              {["S", "A+", "A", "B+", "B", "C", "D"].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          </td>
                          <td>
                            <select className="media-table-select" value={grade.g} onChange={(e) => handleKcgsGradeChange(grade.year, "g", e.target.value)}>
                              {["S", "A+", "A", "B+", "B", "C", "D"].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="reflect-note" style={{ marginTop: "12px", color: "#16a34a", fontSize: "0.85rem", paddingLeft: "16px" }}>ⓘ 최신연도 등급과 직전연도 비교를 기준으로 추세 보정값이 계산됩니다.</div>
                </div>
              </div>

              <div className="media-modal-footer">
                <button className="media-modal-btn cancel" onClick={() => setIsKcgsModalOpen(false)}>취소</button>
                <button className="media-modal-btn draft">임시저장</button>
                <button className="media-modal-btn submit" onClick={handleKcgsSubmit}>입력 완료</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default Media;