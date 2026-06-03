import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/survey.css";
import { useAuth } from "@hooks/AuthContext";

import robot from "@assets/images/robot/robot_servey_t.png";
import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

import { GET, POST } from "@utils/Network";

const IS_DUMMY = true;

/* =========================
   DUMMY DATA LAYER
========================= */

const DUMMY_TOP_ISSUES = [
  {
    rank: 1,
    name: "기후변화 대응",
    totalImpact: 4.82,
    totalFin: 4.51,
    empImpact: 4.91,
    empFin: 4.43,
    execImpact: 4.77,
    execFin: 4.88,
    extImpact: 4.69,
    extFin: 4.21,
  },
  {
    rank: 2,
    name: "공급망 ESG 관리",
    totalImpact: 4.63,
    totalFin: 4.72,
    empImpact: 4.34,
    empFin: 4.51,
    execImpact: 4.71,
    execFin: 4.83,
    extImpact: 4.84,
    extFin: 4.82,
  },
  {
    rank: 3,
    name: "안전보건 관리",
    totalImpact: 4.55,
    totalFin: 4.12,
    empImpact: 4.87,
    empFin: 4.01,
    execImpact: 4.32,
    execFin: 4.28,
    extImpact: 4.21,
    extFin: 4.05,
  },
];

const DUMMY_SURVEY_RESULT = {
  kpi: { emp: 124, exec: 18, ext: 45 },
  stakeholder: {
    emp: {
      top3: ["기후변화 대응", "안전보건 관리", "인적자본 개발"],
      desc: "임직원은 환경 대응과 안전, 인적 성장에 높은 관심을 보였습니다.",
    },
    exec: {
      top3: ["기후변화 대응", "기업가치 제고", "리스크 관리"],
      desc: "경영진은 중장기 가치 창출과 리스크 관리에 집중하고 있습니다.",
    },
    ext: {
      top3: ["기후변화 대응", "공급망 ESG 관리", "투명한 정보 공개"],
      desc: "외부 이해관계자는 공급망 ESG와 투명성에 높은 관심을 보였습니다.",
    },
  },
  issues: DUMMY_TOP_ISSUES,
};

const DUMMY_URLS = {
  emp: "https://forms.gle/emp_sample_skm",
  exec: "https://forms.gle/exec_sample_skm",
  ext: "https://forms.gle/ext_sample_skm",
};

const DUMMY_SUMMARY =
  "AI 응답 데이터 동기화가 완료되었습니다. 외부이해관계자 그룹의 참여율이 상대적으로 낮아 추가 독려가 필요합니다.";

/* =========================
   MAIN COMPONENT
========================= */

const Survey = () => {
  const navigate = useNavigate();
  const particleRef = useRef(null);
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.company_id;

  const activeIndex = 2;

  const steps = [
    { id: 1, title: "벤치마킹 분석", icon: "🎯", path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: "📺", path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: "👥", path: "/survey" },
    { id: 4, title: "전체 결과", icon: "📊", path: "/result" },
    { id: 5, title: "보고서 초안", icon: "📄", path: "/draft" },
  ];

  /* =========================
     STATE
  ========================= */

  const [kpiData, setKpiData] = useState({
    emp: 150,
    exec: 20,
    ext: 80,
  });
  const [surveyUrls, setSurveyUrls] = useState({
    emp: "",
    exec: "",
    ext: "",
  });

  const [isUrlCreated, setIsUrlCreated] = useState(false);
  const [liveData, setLiveData] = useState({ emp: 0, exec: 0, ext: 0 });
  const [topIssues, setTopIssues] = useState([]);
  const [surveyResult, setSurveyResult] = useState(null);

  const [progress, setProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [aggregationDone, setAggregationDone] = useState(false);
  const [summaryText, setSummaryText] = useState(DUMMY_SUMMARY);

  /* =========================
     API LAYER
  ========================= */

  const api = {
    getLiveKpi: async () => {
      if (IS_DUMMY) return { emp: 124, exec: 18, ext: 45 };
      return await GET("/survey/kpi/live");
    },

    getSurveyUrls: async () => {
      if (IS_DUMMY) return DUMMY_URLS;
      return await GET("/survey/urls");
    },

    getTopIssues: async () => {
      if (IS_DUMMY) return DUMMY_TOP_ISSUES;
      return await GET("/survey/issues");
    },

    getSurveyResult: async () => {
      if (IS_DUMMY) return DUMMY_SURVEY_RESULT;
      return await GET("/survey/result");
    },

    runSurveyAnalysis: async () => {
      if (IS_DUMMY) return { success: true };
      return await POST("/survey/analyze");
    },
    createSurvey: async (payload) => {
      return await POST("/survey", payload);
    },
  };

  /* =========================
     EFFECTS
  ========================= */

  useEffect(() => {
    createParticles();
  }, []);

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

  /* =========================
     FUNCTIONS
  ========================= */
  const createSurveyUrl = async () => {
    try {
      if (!selectedCompany?.company_id) {
        showDefaultAlert(
          "오류",
          "선택된 회사가 없습니다.",
          "error"
        );
        return;
      }

      const result = await POST("/survey", {
        companyId: selectedCompany.company_id.toString(),
      });

      console.log(result);

      setSurveyUrls({
        emp: result.urls.emp,
        exec: result.urls.exec,
        ext: result.urls.ext,
      });

      setIsUrlCreated(true);

      showDefaultAlert(
        "생성 완료",
        "설문 URL 생성 완료",
        "success"
      );
    } catch (err) {
      console.error(err);

      showDefaultAlert(
        "실패",
        "설문 생성 실패",
        "error"
      );
    }
  };
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
  const toggleDashboard = () => {
    setDashboardOpen((prev) => !prev);
  };
  const handleKpiChange = (type, value) => {
    setKpiData((prev) => ({
      ...prev,
      [type]: Number(value),
    }));
  };

  const copyUrl = async (url) => {
    try {
      if (!url) throw new Error("empty url");

      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        // fallback (구형 브라우저 대응)
        const textarea = document.createElement("textarea");
        textarea.value = url;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }

      showDefaultAlert("복사 완료", "클립보드 복사 완료", "success");
    } catch (e) {
      console.error("clipboard error:", e);
      showDefaultAlert("복사 실패", "오류 발생", "error");
    }
  };

  const runLiveKpiAggregation = async () => {
    const data = await api.getLiveKpi();
    setLiveData(data);
    setAggregationDone(true);
    if (!isUrlCreated) {
      showDefaultAlert(
        "필요",
        "먼저 설문 URL을 생성하세요.",
        "warning"
      );
      return;
    }
    setSummaryText(
      IS_DUMMY
        ? DUMMY_SUMMARY
        : "AI 분석 결과 업데이트 완료"
    );

    await showDefaultAlert(
      "완료",
      "KPI 업데이트 완료",
      "success"
    );
  };

  const runSurveyAnalysis = async () => {
    if (isAnalyzing) return;
    if (!isUrlCreated) {
      showDefaultAlert(
        "필요",
        "먼저 설문 URL을 생성하세요.",
        "warning"
      );
      return;
    }

    const confirmed = await showConfirmAlert(
      "분석 실행",
      "AI 분석을 시작할까요?",
      "question"
    );

    if (!confirmed) return;

    setDashboardOpen(true);
    setShowResult(false);
    setProgress(0);
    setIsAnalyzing(true);

    const [result, issues, urls] = await Promise.all([
      api.getSurveyResult(),
      api.getTopIssues(),
      api.getSurveyUrls(),
    ]);

    setSurveyResult(result);
    setTopIssues(issues);
    setSurveyUrls(urls);

    await api.runSurveyAnalysis();
  };

  const moveStep = (index) => {
    if (isAnalyzing) return;
    if (index === activeIndex) return;
    navigate(steps[index].path);
  };

  const getPercent = (current, total) => {
    if (!total) return 0;
    return ((current / total) * 100).toFixed(1);
  };
  return (
    <div className="survey-container">
      {/* =========================================================
          Header
      ========================================================== */}
      <header className="survey-header">
        <h1 className="survey-title">
          지속가능경영보고서 AI 자동 생성
        </h1>

        {/* =====================================================
            Stepper 영역
        ====================================================== */}
        <div className="survey-stepper-row">
          {steps.map((step, index) => (
            <div
              key={step.id}
              style={{
                display: "flex",
                alignItems: "center",
              }}
            >
              <div
                className={`step-box ${index === activeIndex
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
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "12px",
            }}
          >
            <button
              className="survey-btn"
              onClick={createSurveyUrl}
            >
              URL 생성
            </button>
          </div>
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
                        value={surveyUrls.emp || ""}
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() => copyUrl(surveyUrls.emp)}
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
                        value={surveyUrls.exec || ""}
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() => copyUrl(surveyUrls.exec)}
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
                        value={surveyUrls.ext || ""}
                        readOnly
                      />

                      <button
                        className="btn-url-copy"
                        onClick={() => copyUrl(surveyUrls.ext)}
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
                        "var(--survey-primary)",
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
              className="survey-btn"
              onClick={runLiveKpiAggregation}
            >
              실시간 통계 집계
            </button>

            <button
              className="survey-btn secondary"
              onClick={runSurveyAnalysis}
              style={{ marginBottom: "50px" }}
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
        className={`survey-result-dashboard ${dashboardOpen ? "open" : ""
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
          className={`survey-view-container
              ${isAnalyzing ? "analyzing" : ""}
              ${showResult ? "showing-result" : ""}
            `}
        >
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
              <div className="survey-stage">
                <div className="survey-float-wrap">
                  <img
                    src={robot}
                    className="survey-main-img"
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
                        "var(--survey-primary)",
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
            <div className="survey-result-layout">

              {/* KPI 카드 영역 */}
              <div className="survey-kpi-grid">
                <div className="survey-kpi-card">
                  <div className="stat-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22"
                      height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D"
                      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                      <circle cx="9" cy="7" r="4" />
                    </svg>
                    임직원 응답</div>

                  <div className="stat-value">
                    {liveData.emp}명
                    <span className="stat-target">
                      (목표 {kpiData.emp}명)
                    </span>
                  </div>

                  <div className="kpi-bar-wrap">
                    <div
                      className="kpi-bar-fill"
                      style={{
                        width: `${getPercent(
                          liveData.emp,
                          kpiData.emp
                        )}%`,
                      }}
                    />
                    <span className="kpi-bar-pct">
                      {getPercent(
                        liveData.emp,
                        kpiData.emp
                      )}
                      %
                    </span>
                  </div>
                </div>

                <div className="survey-kpi-card">
                  <div className="stat-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
                      viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="7" width="20" height="14" rx="2" />
                      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                      <line x1="12" y1="12" x2="12" y2="16" />
                      <line x1="10" y1="14" x2="14" y2="14" />
                    </svg>
                    경영진 응답
                  </div>

                  <div className="stat-value">
                    {liveData.exec}명
                    <span className="stat-target">
                      (목표 {kpiData.exec}명)
                    </span>
                  </div>

                  <div className="kpi-bar-wrap">
                    <div
                      className="kpi-bar-fill"
                      style={{
                        width: `${getPercent(
                          liveData.exec,
                          kpiData.exec
                        )}%`,
                      }}
                    />
                    <span className="kpi-bar-pct">
                      {getPercent(
                        liveData.exec,
                        kpiData.exec
                      )}
                      %
                    </span>
                  </div>
                </div>

                <div className="survey-kpi-card">
                  <div className="stat-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22"
                      height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D"
                      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="2" y1="12" x2="22" y2="12" />
                      <path
                        d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                    </svg>

                    외부 응답
                  </div>

                  <div className="stat-value">
                    {liveData.ext}명
                    <span className="stat-target">
                      (목표 {kpiData.ext}명)
                    </span>
                  </div>

                  <div className="kpi-bar-wrap">
                    <div
                      className="kpi-bar-fill"
                      style={{
                        width: `${getPercent(
                          liveData.ext,
                          kpiData.ext
                        )}%`,
                      }}
                    />
                    <span className="kpi-bar-pct">
                      {getPercent(
                        liveData.ext,
                        kpiData.ext
                      )}
                      %
                    </span>
                  </div>
                </div>

                <div className="survey-kpi-card">
                  <div className="stat-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
                      viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
                      <path d="M22 12A10 10 0 0 0 12 2v10z" />
                    </svg>
                    전체 응답률
                  </div>

                  <div className="stat-value">
                    {(
                      ((liveData.emp +
                        liveData.exec +
                        liveData.ext) /
                        (kpiData.emp +
                          kpiData.exec +
                          kpiData.ext)) *
                      100
                    ).toFixed(1)}
                    %

                    <span className="stat-target">
                      (
                      {liveData.emp +
                        liveData.exec +
                        liveData.ext}
                      /
                      {kpiData.emp +
                        kpiData.exec +
                        kpiData.ext}
                      )
                    </span>
                  </div>

                  <div className="kpi-bar-wrap">
                    <div
                      className="kpi-bar-fill"
                      style={{
                        width: `${((liveData.emp +
                          liveData.exec +
                          liveData.ext) /
                          (kpiData.emp +
                            kpiData.exec +
                            kpiData.ext)) *
                          100
                          }%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* 하단 2패널 */}
              <div className="survey-panels">

                {/* Top 이슈 */}
                <div className="survey-panel">

                  <div className="panel-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                      viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2"
                      style={{
                        verticalAlign: "middle",
                        marginRight: "4px"
                      }}>
                      <line x1="18" y1="20" x2="18" y2="10" />
                      <line x1="12" y1="20" x2="12" y2="4" />
                      <line x1="6" y1="20" x2="6" y2="14" />
                    </svg>
                    설문 Top 이슈 점수
                  </div>

                  <table className="survey-complex-table">
                    <thead>
                      <tr>
                        <th rowSpan="2">순위</th>
                        <th rowSpan="2">
                          Sub Issue
                        </th>
                        <th rowSpan="2">
                          Total Impact
                        </th>
                        <th rowSpan="2">
                          Total Financial
                        </th>
                        <th colSpan="2">
                          임직원
                        </th>
                        <th colSpan="2">
                          경영진
                        </th>
                        <th colSpan="2">
                          외부
                        </th>
                      </tr>

                      <tr>
                        <th>Impact</th>
                        <th>Financial</th>
                        <th>Impact</th>
                        <th>Financial</th>
                        <th>Impact</th>
                        <th>Financial</th>
                      </tr>
                    </thead>

                    <tbody>
                      {(surveyResult?.issues || []).map((issue) => (
                        <tr key={issue.rank}>
                          <td>{issue.rank}</td>
                          <td>{issue.name}</td>
                          <td>
                            {issue.totalImpact}
                          </td>
                          <td>
                            {issue.totalFin}
                          </td>
                          <td>
                            {issue.empImpact}
                          </td>
                          <td>
                            {issue.empFin}
                          </td>
                          <td>
                            {issue.execImpact}
                          </td>
                          <td>
                            {issue.execFin}
                          </td>
                          <td>
                            {issue.extImpact}
                          </td>
                          <td>
                            {issue.extFin}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 이해관계자별 관점 */}
                <div className="survey-panel">
                  <div className="panel-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                      viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2"
                      style={{
                        verticalAlign: "middle",
                        marginRight: "4px"
                      }}>
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                      <circle cx="9" cy="7" r="4" />
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                    </svg>
                    이해관계자 그룹별 관점 차이
                  </div>

                  <div className="stakeholder-group-list">

                    <div className="stakeholder-item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                        viewBox="0 0 24 24" fill="none" stroke="#03A94D"
                        strokeWidth="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                      </svg>
                      <div className="stakeholder-name">

                        임직원 Top3
                      </div>

                      <div className="stakeholder-topics">
                        {surveyResult?.stakeholder?.emp?.top3?.join(", ")}
                      </div>

                      <p>{surveyResult?.stakeholder?.emp?.desc}</p>
                    </div>

                    <div className="stakeholder-item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                        viewBox="0 0 24 24" fill="none" stroke="#03A94D"
                        strokeWidth="2">
                        <rect x="2" y="7" width="20" height="14" rx="2" />
                        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                      </svg>
                      <div className="stakeholder-name">
                        경영진 Top3
                      </div>

                      <div className="stakeholder-topics">
                        {surveyResult?.stakeholder?.exec?.top3?.join(", ")}
                      </div>

                      <p>{surveyResult?.stakeholder?.exec?.desc}</p>
                    </div>

                    <div className="stakeholder-item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                        viewBox="0 0 24 24" fill="none" stroke="#03A94D"
                        strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="2" y1="12" x2="22" y2="12" />
                        <path
                          d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                      </svg>
                      <div className="stakeholder-name">
                        외부 Top3
                      </div>

                      <div className="stakeholder-topics">
                        {surveyResult?.stakeholder?.ext?.top3?.join(", ")}
                      </div>

                      <p>{surveyResult?.stakeholder?.ext?.desc}</p>
                    </div>

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