import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
// import "@styles/survey.css"; 
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
              {/* Filter */}
              <div className="filter-bar">
                <select className="filter-select">
                  <option value="all">
                    전체 이해관계자 그룹
                  </option>

                  <option value="emp">
                    임직원
                  </option>

                  <option value="exec">
                    경영진
                  </option>

                  <option value="ext">
                    외부이해관계자
                  </option>
                </select>

                <select className="filter-select">
                  <option value="score">
                    점수 높은 순 정렬
                  </option>

                  <option value="issue">
                    핵심 이슈 지표 필터링
                  </option>
                </select>
              </div>

              {/* Summary */}
              <div className="summary-grid">
                <div className="summary-card">
                  <span className="label">
                    🌍 Impact Materiality
                  </span>

                  <div className="score-flex">
                    <span className="value">
                      87.4
                      <span> / 100점</span>
                    </span>

                    <span
                      style={{
                        fontSize: "0.7rem",
                        color: "#03A94D",
                        fontWeight: 700,
                      }}
                    >
                      [상위 4.2% 중대이슈]
                    </span>
                  </div>
                </div>

                <div className="summary-card">
                  <span className="label">
                    💰 Financial
                    Materiality
                  </span>

                  <div className="score-flex">
                    <span
                      className="value"
                      style={{
                        color: "#334155",
                      }}
                    >
                      74.2
                      <span> / 100점</span>
                    </span>

                    <span
                      style={{
                        fontSize: "0.7rem",
                        color: "#64748b",
                        fontWeight: 700,
                      }}
                    >
                      [중기 리스크 관리 대상]
                    </span>
                  </div>
                </div>
              </div>

              {/* ESG 유형 결과 */}
              <div className="type-result-box">
                <div className="type-title">
                  📋 설문 유형별 종합 결과
                  <span>
                    (5점 만점 환산 산출)
                  </span>
                </div>

                <div className="type-grid">
                  <div className="type-mini-card">
                    <span>
                      Environment (환경)
                    </span>

                    <strong>
                      4.25 / 5.0
                    </strong>
                  </div>

                  <div className="type-mini-card">
                    <span>Social (사회)</span>

                    <strong>
                      3.91 / 5.0
                    </strong>
                  </div>

                  <div className="type-mini-card">
                    <span>
                      Governance (지배구조)
                    </span>

                    <strong>
                      4.55 / 5.0
                    </strong>
                  </div>
                </div>
              </div>

              {/* 핵심 이슈 */}
              <div className="issue-list-box">
                <div className="issue-item">
                  <span>
                    탄소 배출 저감 및 기후변화 대응
                    전략 수립 지표
                  </span>

                  <span className="badge-risk">
                    Impact 핵심
                  </span>
                </div>

                <div className="issue-item">
                  <span>
                    글로벌 공급망 ESG 평가 및
                    리스크 관리 체계 고도화
                  </span>

                  <span className="badge-risk">
                    Financial 위험
                  </span>
                </div>

                <div className="issue-item">
                  <span>
                    사내 안전 보건 관리 감독 및
                    직무 환경 만족도 개선
                  </span>

                  <span>일반 지표</span>
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