import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/survey.css"; 
import "@styles/sr.css";

import robot from "@assets/images/robot/robot_servey_t.png";

import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

const TOP_ISSUES = [
  { rank: 1, name: "기후변화 대응",   totalImpact: 88.7, totalFin: 76.3, empImpact: 4.7, empFin: 4.5, execImpact: 4.6, execFin: 4.4, extImpact: 4.4, extFin: 4.2 },
  { rank: 2, name: "안전보건 관리",   totalImpact: 84.1, totalFin: 73.2, empImpact: 4.5, empFin: 4.3, execImpact: 4.4, execFin: 4.2, extImpact: 4.0, extFin: 3.9 },
  { rank: 3, name: "인적자본 개발",   totalImpact: 76.8, totalFin: 68.1, empImpact: 4.2, empFin: 4.0, execImpact: 3.9, execFin: 3.8, extImpact: 3.6, extFin: 3.5 },
  { rank: 4, name: "공급망 ESG 관리", totalImpact: 72.3, totalFin: 65.4, empImpact: 4.0, empFin: 3.9, execImpact: 3.8, execFin: 3.7, extImpact: 3.5, extFin: 3.4 },
  { rank: 5, name: "윤리·준법 경영",  totalImpact: 70.2, totalFin: 62.8, empImpact: 3.9, empFin: 3.8, execImpact: 3.7, execFin: 3.6, extImpact: 3.3, extFin: 3.2 },
];

const STAKEHOLDER_GROUPS = [
  {
    key: "emp",
    name: "임직원 Top3",
    topics: "기후변화 대응, 안전보건 관리, 인적자본 개발",
    desc: "임직원은 환경 대응과 안전, 그리고 인적 성장에 높은 관심을 보였습니다.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      </svg>
    ),
  },
  {
    key: "exec",
    name: "경영진 Top3",
    topics: "기후변화 대응, 기업가치 제고, 리스크 관리",
    desc: "경영진은 중장기 가치 창출과 리스크 관리에 초점을 두고 있습니다.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2">
        <rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      </svg>
    ),
  },
  {
    key: "ext",
    name: "외부 Top3",
    topics: "기후변화 대응, 공급망 ESG 관리, 투명한 정보 공개",
    desc: "외부 이해관계자는 투명성과 공급망 관리에 높은 중요성을 부여했습니다.",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2">
        <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    ),
  },
];


/**
 * 이해관계자 설문 페이지
 *
 * 주요 기능
 * 1. 설문 URL 복사
 * 2. KPI 목표 인원 입력
 * 3. 실시간 통계 집계 시뮬레이션
 * 4. AI 설문 분석 진행
 * 5. 단계별(step) 페이지 이동
 */
const Survey = () => {
  const navigate = useNavigate();

  /**
   * 현재 페이지 Step Index
   * benchmarking: 0
   * media: 1
   * survey: 2
   */
  const activeIndex = 2;

  /**
   * ESG 보고서 생성 프로세스 Step 정의
   */
  const steps = [
    {
      id: 1,
      title: "벤치마킹 분석",
      icon: "🎯",
      path: "/benchmk",
    },
    {
      id: 2,
      title: "미디어 분석",
      icon: "📺",
      path: "/media",
    },
    {
      id: 3,
      title: "이해관계자 설문",
      icon: "👥",
      path: "/survey",
    },
    {
      id: 4,
      title: "전체 결과",
      icon: "📊",
      path: "/result",
    },
    {
      id: 5,
      title: "보고서 초안",
      icon: "📄",
      path: "/draft",
    },
  ];

  /**
   * KPI 입력값 상태
   */
  const [kpiData, setKpiData] = useState({
    emp: 150,
    exec: 20,
    ext: 80,
  });

  /**
   * 실시간 집계 결과 상태
   */
  const [liveData, setLiveData] = useState({
    emp: 0,
    exec: 0,
    ext: 0,
  });

  /**
   * 진행률 상태
   */
  const [progress, setProgress] = useState(0);

  /**
   * AI 분석 진행 상태
   */
  const [isAnalyzing, setIsAnalyzing] =
    useState(false);

  /**
   * 대시보드 열림 상태
   */
  const [dashboardOpen, setDashboardOpen] =
    useState(false);

  /**
   * 결과 표시 상태
   */
  const [showResult, setShowResult] =
    useState(false);

  /**
   * KPI 집계 완료 여부
   */
  const [aggregationDone, setAggregationDone] =
    useState(false);

  /**
   * 실시간 요약 메시지
   */
  const [summaryText, setSummaryText] =
    useState(
      "하단의 '실시간 통계 집계' 버튼을 누르면 연동 데이터 파싱 결과 요약이 표시됩니다."
    );

  /**
   * 파티클 DOM Ref
   */
  const particleRef = useRef(null);

  /**
   * 최초 마운트 시 파티클 생성
   */
  useEffect(() => {
    createParticles();
  }, []);

  /**
   * AI 분석 진행 시 Progress 증가
   */
  useEffect(() => {
    let interval;

    if (isAnalyzing) {
      interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);

            setIsAnalyzing(false);
            setShowResult(true);

            return 100;
          }

          return prev + 2;
        });
      }, 30);
    }

    return () => clearInterval(interval);
  }, [isAnalyzing]);

  /**
   * 배경 파티클 생성 함수
   */
  const createParticles = () => {
    if (!particleRef.current) return;

    particleRef.current.innerHTML = "";

    for (let i = 0; i < 12; i++) {
      const particle =
        document.createElement("div");

      particle.className = "particle";

      const size = Math.random() * 5 + 3;

      particle.style.width = `${size}px`;
      particle.style.height = `${size}px`;

      particle.style.left = `${
        Math.random() * 100
      }%`;

      particle.style.top = `${
        Math.random() * 100
      }%`;

      particle.style.animationDelay = `${
        Math.random() * 2
      }s`;

      particleRef.current.appendChild(particle);
    }
  };

  /**
   * Step 클릭 이동 함수
   */
  const moveStep = (index) => {
    if (isAnalyzing) return;

    if (index === activeIndex) return;

    navigate(steps[index].path);
  };

  /**
   * KPI 값 변경 함수
   */
  const handleKpiChange = (type, value) => {
    setKpiData((prev) => ({
      ...prev,
      [type]: Number(value),
    }));
  };

  /**
   * URL 복사 함수
   */
  const copyUrl = async (url) => {
    try {
      await navigator.clipboard.writeText(url);

      showDefaultAlert(
        "복사 완료",
        "설문 주소가 클립보드에 복사되었습니다.",
        "success"
      );
    } catch (error) {
      showDefaultAlert(
        "복사 실패",
        "클립보드 복사 중 문제가 발생했습니다.",
        "error"
      );
    }
  };

  /**
   * 실시간 KPI 집계 실행
   *
   * 실제 서비스에서는
   * Google Sheet / DB / API 응답값 등을
   * 기반으로 실시간 집계 가능
   */
  const runLiveKpiAggregation = async () => {
    setLiveData({
      emp: 124,
      exec: 18,
      ext: 45,
    });

    setAggregationDone(true);

    setSummaryText(
      "AI 응답 데이터 동기화가 완료되었습니다. 외부이해관계자 그룹의 참여율이 상대적으로 낮아 추가 독려가 필요합니다."
    );

    await showDefaultAlert(
      "실시간 집계 완료",
      "우측 KPI 패널 데이터가 최신 상태로 업데이트되었습니다.",
      "success"
    );
  };

  /**
   * AI 설문 분석 실행
   */
  const runSurveyAnalysis = async () => {
    if (isAnalyzing) return;

    /**
     * KPI 집계 미실행 상태 방지
     */
    if (!aggregationDone) {
      showDefaultAlert(
        "집계 필요",
        "실시간 통계 집계를 먼저 실행해주세요.",
        "warning"
      );

      return;
    }

    const confirmed =
      await showConfirmAlert(
        "설문 결과 분석",
        "AI 기반 이중 중대성 분석을 시작하시겠습니까?",
        "question"
      );

    if (!confirmed) return;

    setDashboardOpen(true);

    setShowResult(false);

    setProgress(0);

    setIsAnalyzing(true);
  };

  /**
   * 대시보드 토글
   */
  const toggleDashboard = () => {
    setDashboardOpen((prev) => !prev);
  };

  /**
   * 퍼센트 계산 함수
   */
  const getPercent = (current, total) => {
    if (!total) return 0;

    return ((current / total) * 100).toFixed(1);
  };

  const totalResponded = liveData.emp + liveData.exec + liveData.ext;
  const totalKpi = kpiData.emp + kpiData.exec + kpiData.ext;


  return (
    <div className="sr-container">
      {/* =========================================================
          Header
      ========================================================== */}
      <header className="sr-header">
        <h1 className="sr-title">
          지속가능경영보고서 AI 자동 생성
        </h1>

        {/* =====================================================
            Stepper 영역
        ====================================================== */}
        <div className="sr-stepper-row">
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

                <div
                  style={{
                    fontSize: "0.8rem",
                    fontWeight: 800,
                  }}
                >
                  {step.title}
                </div>
              </div>

              {index < steps.length - 1 && (
                <div className="step-line"></div>
              )}
            </div>
          ))}
        </div>
      </header>

      {/* =========================================================
          Main Content
      ========================================================== */}
      <main className="main-content">
        <div className="input-card">
          <h2
            style={{
              fontSize: "1.4rem",
              fontWeight: 800,
              marginBottom: "6px",
            }}
          >
            이해관계자 설문
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "0.9rem",
              marginBottom: "4px",
            }}
          >
            각 이해관계자 그룹별 설문 발송 관리 및
            실시간 집계 결과를 매핑합니다.
          </p>

          {/* =====================================================
              설문 영역
          ====================================================== */}
          <div className="survey-section-grid">
            {/* =================================================
                설문 URL / KPI 관리
            ================================================== */}
            <div className="survey-wrapper">
              <div className="survey-badge white-badge">
                설문 URL & 발송 관리
              </div>

              <div className="survey-panel">
                <div className="survey-group-list">
                  {/* 임직원 */}
                  <div className="survey-row-box">
                    <label>임직원</label>

                    <div className="url-input-line">
                      <input
                        type="text"
                        value="https://forms.gle/emp_sample_skm"
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() =>
                          copyUrl(
                            "https://forms.gle/emp_sample_skm"
                          )
                        }
                      >
                        복사
                      </button>
                    </div>

                    <div className="kpi-input-line">
                      <span>
                        총 발송 인원 (KPI) :
                      </span>

                      <input
                        type="number"
                        value={kpiData.emp}
                        onChange={(e) =>
                          handleKpiChange(
                            "emp",
                            e.target.value
                          )
                        }
                      />

                      명
                    </div>
                  </div>

                  {/* 경영진 */}
                  <div className="survey-row-box">
                    <label>경영진</label>

                    <div className="url-input-line">
                      <input
                        type="text"
                        value="https://forms.gle/exec_sample_skm"
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() =>
                          copyUrl(
                            "https://forms.gle/exec_sample_skm"
                          )
                        }
                      >
                        복사
                      </button>
                    </div>

                    <div className="kpi-input-line">
                      <span>
                        총 발송 인원 (KPI) :
                      </span>

                      <input
                        type="number"
                        value={kpiData.exec}
                        onChange={(e) =>
                          handleKpiChange(
                            "exec",
                            e.target.value
                          )
                        }
                      />

                      명
                    </div>
                  </div>

                  {/* 외부 이해관계자 */}
                  <div className="survey-row-box">
                    <label>외부이해관계자</label>

                    <div className="url-input-line">
                      <input
                        type="text"
                        value="https://forms.gle/ext_sample_skm"
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() =>
                          copyUrl(
                            "https://forms.gle/ext_sample_skm"
                          )
                        }
                      >
                        복사
                      </button>
                    </div>

                    <div className="kpi-input-line">
                      <span>
                        총 발송 인원 (KPI) :
                      </span>

                      <input
                        type="number"
                        value={kpiData.ext}
                        onChange={(e) =>
                          handleKpiChange(
                            "ext",
                            e.target.value
                          )
                        }
                      />

                      명
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* =================================================
                실시간 KPI 통계 패널
            ================================================== */}
            <div className="survey-wrapper">
              <div className="survey-badge white-badge">
                실시간 통계 집계 (KPI 현황)
              </div>

              <div className="survey-panel">
                <div className="sheets-dashboard-grid">
                  {/* 임직원 */}
                  <div className="chart-status-card">
                    <div className="chart-header">
                      <span className="label">
                        임직원 제출 현황
                      </span>

                      <div className="value">
                        <span>
                          {liveData.emp}
                        </span>

                        {" / "}

                        <span>
                          {kpiData.emp}
                        </span>

                        <span>명</span>
                      </div>
                    </div>

                    <div className="api-progress-container">
                      <div
                        className="api-progress-bar"
                        style={{
                          width: `${getPercent(
                            liveData.emp,
                            kpiData.emp
                          )}%`,
                        }}
                      ></div>
                    </div>
                  </div>

                  {/* 경영진 */}
                  <div className="chart-status-card">
                    <div className="chart-header">
                      <span className="label">
                        경영진 제출 현황
                      </span>

                      <div className="value">
                        <span>
                          {liveData.exec}
                        </span>

                        {" / "}

                        <span>
                          {kpiData.exec}
                        </span>

                        <span>명</span>
                      </div>
                    </div>

                    <div className="api-progress-container">
                      <div
                        className="api-progress-bar"
                        style={{
                          width: `${getPercent(
                            liveData.exec,
                            kpiData.exec
                          )}%`,
                        }}
                      ></div>
                    </div>
                  </div>

                  {/* 외부 이해관계자 */}
                  <div className="chart-status-card">
                    <div className="chart-header">
                      <span className="label">
                        외부관계자 제출 현황
                      </span>

                      <div className="value">
                        <span>
                          {liveData.ext}
                        </span>

                        {" / "}

                        <span>
                          {kpiData.ext}
                        </span>

                        <span>명</span>
                      </div>
                    </div>

                    <div className="api-progress-container">
                      <div
                        className="api-progress-bar"
                        style={{
                          width: `${getPercent(
                            liveData.ext,
                            kpiData.ext
                          )}%`,
                          background: "#ffb300",
                        }}
                      ></div>
                    </div>
                  </div>
                </div>

                {/* =================================================
                    AI 메시지 박스
                ================================================== */}
                <div className="ai-message-box">
                  <strong
                    style={{
                      color:
                        "var(--sr-primary)",
                    }}
                  >
                    [AI 응답 데이터 분석 결과]
                  </strong>

                  <p
                    style={{
                      marginTop: "4px",
                      color: "#475569",
                    }}
                  >
                    {summaryText}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* =====================================================
              Action Buttons
          ====================================================== */}
          <div className="action-btn-group">
            <button
              className="sr-btn"
              onClick={runLiveKpiAggregation}
            >
              실시간 통계 집계
            </button>

            <button
              className="sr-btn secondary"
              onClick={runSurveyAnalysis}
              style={{marginBottom: "50px"}}
            >
              설문 결과 분석
            </button>
          </div>
        </div>
      </main>

      {/* =========================================================
          Result Dashboard
      ========================================================== */}
      <div
        className={`sr-result-dashboard ${
          dashboardOpen ? "open" : ""
        }`}
      >
        {/* Dashboard Handle */}
        <div
          className="dashboard-handle"
          onClick={toggleDashboard}
        >
          <div className="handle-pill">
            {isAnalyzing
              ? "AI 분석 진행 중..."
              : showResult
              ? "분석 완료 - 결과 요약 확인"
              : "실시간 분석 대기 중"}
          </div>
        </div>

        {/* =====================================================
            Robot View
        ====================================================== */}
        <div
          className={`robot-view-container ${
            isAnalyzing ? "analyzing" : ""
          }`}
        >
          {/* Particle */}
          <div
            className="particle-field"
            ref={particleRef}
          ></div>

          {/* =================================================
              Loading Content
          ================================================== */}
          {!showResult ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                width: "100%",
              }}
            >
              <div className="robot-stage">
                <div className="robot-float-wrap">
                  <img
                    src={robot}
                    className="robot-main-img"
                    alt="robot"
                  />
                </div>
              </div>

              <h3
                style={{
                  fontSize: "1.2rem",
                  fontWeight: 800,
                  margin: "0 0 4px 0",
                }}
              >
                {isAnalyzing
                  ? "Impact & Financial 평가 계산 중..."
                  : "분석 미실행 상태"}
              </h3>

              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#64748b",
                  margin: 0,
                }}
              >
                {isAnalyzing
                  ? "AI 기반 이중 중대성 매트릭스 알고리즘이 설문 응답을 분석 중입니다."
                  : "하단의 '설문 결과 분석' 버튼을 작동시켜 주십시오."}
              </p>

              {/* Progress */}
              {isAnalyzing && (
                <div className="progress-section">
                  <div className="progress-bar-wrap">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${progress}%`,
                      }}
                    ></div>
                  </div>

                  <div
                    style={{
                      marginTop: "6px",
                      fontWeight: 700,
                      fontSize: "0.85rem",
                      color:
                        "var(--sr-primary)",
                    }}
                  >
                    {progress}% 분석 중
                  </div>
                </div>
              )}
            </div>
          ) : (
            /**
             * ===================================================
             * 최종 결과 영역
             * ===================================================
             */
            <div className="result-layout">
              {/* 결과 배너 */}
              <div className="result-banner">
                <div style={{ display: "flex", alignItems: "center", gap: "16px", flex: 1 }}>
                  <div className="result-banner-title">📰 [AI 이해관계자 설문 분석 결과]</div>
                  <p className="result-banner-desc">
                    임직원, 경영진, 외부 이해관계자 응답을 종합한 결과<br />
                    <b>기후변화 대응과 안전보건 관리 이슈</b>가 가장 높은 우선순위로 도출되었습니다.
                  </p>
                </div>
                <img src={robot} alt="robot" className="result-banner-robot" />
              </div>

              {/* 통계 카드 4개 */}
              <div className="result-stats-row">
                <div className="result-stat-card survey-kpi-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">임직원 응답</div>
                    <div className="stat-value">{liveData.emp}명<span className="stat-target">(목표 {kpiData.emp}명)</span></div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${getPercent(liveData.emp, kpiData.emp)}%` }}></div>
                      <span className="kpi-bar-pct">{getPercent(liveData.emp, kpiData.emp)}%</span>
                    </div>
                  </div>
                </div>

                <div className="result-stat-card survey-kpi-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                      <line x1="12" y1="12" x2="12" y2="16" /><line x1="10" y1="14" x2="14" y2="14" />
                    </svg>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="stat-label">경영진 응답</div>
                    <div className="stat-value">{liveData.exec}명<span className="stat-target">(목표 {kpiData.exec}명)</span></div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${getPercent(liveData.exec, kpiData.exec)}%` }}></div>
                      <span className="kpi-bar-pct">{getPercent(liveData.exec, kpiData.exec)}%</span>
                    </div>
                  </div>
                </div>

                <div className="result-stat-card survey-kpi-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" />
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                    </svg>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="stat-label">외부 응답</div>
                    <div className="stat-value">{liveData.ext}명<span className="stat-target">(목표 {kpiData.ext}명)</span></div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${getPercent(liveData.ext, kpiData.ext)}%` }}></div>
                      <span className="kpi-bar-pct">{getPercent(liveData.ext, kpiData.ext)}%</span>
                    </div>
                  </div>
                </div>

                <div className="result-stat-card survey-kpi-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21.21 15.89A10 10 0 1 1 8 2.83" /><path d="M22 12A10 10 0 0 0 12 2v10z" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">전체응답률</div>
                    <div className="stat-value">
                      <span className="stat-target">{getPercent(totalResponded, totalKpi)}% ({totalResponded}/{totalKpi})</span>
                    </div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${getPercent(totalResponded, totalKpi)}%` }}></div>
                      <span className="kpi-bar-pct">{getPercent(totalResponded, totalKpi)}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 하단 패널 2개 */}
              <div className="result-panels-row survey-panels">
                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" style={{ verticalAlign: "middle", marginRight: "4px" }}>
                        <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
                      </svg>
                      설문 Top 이슈 점수
                    </span>
                  </div>
                  <table className="issue-table survey-complex-table">
                    <thead>
                      <tr>
                        <th rowSpan="2">순위</th>
                        <th rowSpan="2">Sub Issue</th>
                        <th rowSpan="2">Total Impact</th>
                        <th rowSpan="2">Total Financial</th>
                        <th colSpan="2" className="group-th">임직원</th>
                        <th colSpan="2" className="group-th">경영진</th>
                        <th colSpan="2" className="group-th">외부</th>
                      </tr>
                      <tr>
                        <th>Impact</th><th>Financial</th>
                        <th>Impact</th><th>Financial</th>
                        <th>Impact</th><th>Financial</th>
                      </tr>
                    </thead>
                    <tbody>
                      {TOP_ISSUES.map((item) => (
                        <tr key={item.rank}>
                          <td>{item.rank}</td><td>{item.name}</td>
                          <td>{item.totalImpact}</td><td>{item.totalFin}</td>
                          <td>{item.empImpact}</td><td>{item.empFin}</td>
                          <td>{item.execImpact}</td><td>{item.execFin}</td>
                          <td>{item.extImpact}</td><td>{item.extFin}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" style={{ verticalAlign: "middle", marginRight: "4px" }}>
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                      이해관계자 그룹별 관점 차이
                    </span>
                  </div>
                  <div className="stakeholder-group-list">
                    {STAKEHOLDER_GROUPS.map((group) => (
                      <div key={group.key} className="stakeholder-item">
                        <div className="stakeholder-header">
                          <div className="reflect-icon">{group.icon}</div>
                          <div>
                            <span className="stakeholder-name">{group.name}</span>
                            <span className="stakeholder-topics">{group.topics}</span>
                          </div>
                        </div>
                        <p className="stakeholder-desc">{group.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Survey;