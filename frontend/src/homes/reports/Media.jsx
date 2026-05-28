import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import "@styles/media.css";

import robot from "@assets/images/robot/robot_media_t.png";

import {
  showDefaultAlert,
} from "@components/UI/ServiceAlert";

import { POST } from "@utils/Network";

const MEDIA_SOURCE_OPTIONS = [
  { value: "impacton", label: "임팩트온" },
  { value: "esgeconomy", label: "ESG경제" },
];

const Media = () => {
  const particleRef = useRef(null);

  const [dashboardOpen, setDashboardOpen] =
    useState(false);

  const [isAnalyzing, setIsAnalyzing] =
    useState(false);

  const [showResult, setShowResult] =
    useState(false);

  const [status, setStatus] = useState({
    press: "ready",
    reg: "ready",
    expert: "ready",
  });

  const [analysisResult, setAnalysisResult] = useState({
    articleCount: 0,
    collectedArticleCount: 0,
    filteredArticleCount: 0,
    observedSubIssueCount: 0,
    savedSignalCount: 0,
    sourceBreakdown: [],
    topIssues: []
  });

  const [formData, setFormData] = useState({
    pressSource: "impacton",

    regOrg: "",

    expertOrg: "",

    pressStartDate: "",
    pressEndDate: "",

    regStartDate: "",
    regEndDate: "",

    expertStartDate: "",
    expertEndDate: "",
  });

  const navigate = useNavigate();

  /**
   * 현재 페이지 Step Index
   * benchmarking: 0
   * media: 1
   * survey: 2
   */
  const activeIndex = 1;

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
   * Step 클릭 이동 함수
   */
  const moveStep = (index) => {
    if (isAnalyzing) return;

    if (index === activeIndex) return;

    navigate(steps[index].path);
  };

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
      p.style.bottom = "0px";
      p.style.animationDelay = `${Math.random() * 2}s`;
      p.style.animationDuration = `${
        Math.random() * 2 + 2
      }s`;

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

  const startMediaCollection = async () => {
    if (isAnalyzing) return;

    if (!formData.pressSource) {
      showDefaultAlert(
        "입력 오류",
        "수집 언론사를 선택해주세요.",
        "warning"
      );
      return;
    }

    if (!formData.pressStartDate || !formData.pressEndDate) {
      showDefaultAlert(
        "입력 오류",
        "수집 희망 기간을 선택해주세요.",
        "warning"
      );
      return;
    }

    setIsAnalyzing(true);
    setDashboardOpen(true);
    setShowResult(false);

    setStatus({
      press: "ing",
      reg: "ing",
      expert: "ready",
    });

    showDefaultAlert(
      "분석 시작",
      "실시간 미디어 및 외부 데이터 수집을 시작합니다.",
      "success"
    );

    try {
      const response = await POST("/api/v1/media/news/crawl-and-analyze", {
        runId: 1, // 테스트용 하드코딩된 runId
        sources: [formData.pressSource],
        dateFrom: formData.pressStartDate,
        dateTo: formData.pressEndDate,
      });

      if (response && response.status !== false) {
        setAnalysisResult(response.data || response);
      }
    } catch (e) {
      console.error(e);
      showDefaultAlert("통신 오류", "미디어 분석 중 서버 에러가 발생했습니다.", "error");
    }

    // UX용 딜레이
    setTimeout(() => {
      setStatus({
        press: "complete",
        reg: "ready",
        expert: "ready",
      });

      setShowResult(true);
      setIsAnalyzing(false);
    }, 1000);
  };

  const getStatusText = (type) => {
    if (type === "ready") return "수집 대기";

    if (type === "ing") return "수집 중";

    if (type === "complete")
      return "수집완료";
  };

  return (
    <div className="sr-container">
      <header className="sr-header">
        <h1 className="sr-title">
          지속가능경영보고서 AI 자동 생성
        </h1>

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

      <main className="main-content">
        <div className="input-card">
          <h2
            style={{
              fontSize: "1.4rem",
              fontWeight: 850,
              marginBottom: "6px",
              color: "#0f172a",
            }}
          >
            미디어 및 기관별 필터 수집 설정
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "0.9rem",
              marginBottom: "10px",
              lineHeight: 1.5,
            }}
          >
            언론사 뉴스, 정부 규제 데이터 및 ESG
            전문기관의 평가 피드를 동기화하여 부정
            위험성 및 공시 트렌드를 실시간
            모니터링합니다.
          </p>

          <div className="media-setup-grid">
            <div className="media-card">
              <div className="media-badge">
                언론 채널
              </div>

              <div
                className="form-group"
                style={{ marginTop: "8px" }}
              >
                <label>
                  수집 언론사
                </label>

                <select
                  className="media-select"
                  name="pressSource"
                  value={
                    formData.pressSource
                  }
                  onChange={handleChange}
                >
                  {MEDIA_SOURCE_OPTIONS.map((source) => (
                    <option
                      key={source.value}
                      value={source.value}
                    >
                      {source.label}
                    </option>
                  ))}
                </select>

                <div
                  style={{
                    marginTop: "6px",
                    padding: "6px 10px",
                    borderRadius: "8px",
                    background: "#f0fdf4",
                    color: "#15803d",
                    fontSize: "0.76rem",
                    fontWeight: 700,
                    lineHeight: 1.4,
                  }}
                >
                  자동 적용 필터: 현대자동차 · 자동차부품산업
                </div>
              </div>

              <div className="form-group">
                <label>
                  수집 희망 기간
                </label>

                <div className="date-range-group">
                  <input
                    type="date"
                    name="pressStartDate"
                    value={
                      formData.pressStartDate
                    }
                    onChange={handleChange}
                  />

                  <span
                    style={{
                      color: "#94a3b8",
                      fontSize: "0.8rem",
                    }}
                  >
                    ~
                  </span>

                  <input
                    type="date"
                    name="pressEndDate"
                    value={
                      formData.pressEndDate
                    }
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className="status-container">
                <span className="status-label">
                  현재 상태
                </span>

                <span
                  className={`status-badge ${status.press}`}
                >
                  {getStatusText(status.press)}
                </span>
              </div>
            </div>

            <div className="media-card">
              <div className="media-badge">
                규제 기관
              </div>

              <div
                className="form-group"
                style={{ marginTop: "8px" }}
              >
                <label>
                  정부 및 규제 데이터 소스
                </label>

                <select
                  className="media-select"
                  name="regOrg"
                  value={formData.regOrg}
                  onChange={handleChange}
                >
                  <option value="">
                    규제 기관 선택
                  </option>

                  <option value="환경부">
                    환경부
                  </option>

                  <option value="금융위원회">
                    금융위원회
                  </option>

                  <option value="공정거래위원회">
                    공정거래위원회
                  </option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  대상 규제 제정 기간
                </label>

                <div className="date-range-group">
                  <input
                    type="date"
                    name="regStartDate"
                    value={
                      formData.regStartDate
                    }
                    onChange={handleChange}
                  />

                  <span
                    style={{
                      color: "#94a3b8",
                      fontSize: "0.8rem",
                    }}
                  >
                    ~
                  </span>

                  <input
                    type="date"
                    name="regEndDate"
                    value={
                      formData.regEndDate
                    }
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className="status-container">
                <span className="status-label">
                  현재 상태
                </span>

                <span
                  className={`status-badge ${status.reg}`}
                >
                  {getStatusText(status.reg)}
                </span>
              </div>
            </div>

            <div className="media-card">
              <div className="media-badge">
                전문 평가기관
              </div>

              <div
                className="form-group"
                style={{ marginTop: "8px" }}
              >
                <label>
                  ESG 외부 평가/리서치 기관
                </label>

                <select
                  className="media-select"
                  name="expertOrg"
                  value={formData.expertOrg}
                  onChange={handleChange}
                >
                  <option value="">
                    평가 기관 선택
                  </option>

                  <option value="MSCI">
                    MSCI
                  </option>

                  <option value="Sustainalytics">
                    Sustainalytics
                  </option>

                  <option value="한국ESG기준원">
                    한국ESG기준원
                  </option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  리포트 공시 기간
                </label>

                <div className="date-range-group">
                  <input
                    type="date"
                    name="expertStartDate"
                    value={
                      formData.expertStartDate
                    }
                    onChange={handleChange}
                  />

                  <span
                    style={{
                      color: "#94a3b8",
                      fontSize: "0.8rem",
                    }}
                  >
                    ~
                  </span>

                  <input
                    type="date"
                    name="expertEndDate"
                    value={
                      formData.expertEndDate
                    }
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className="status-container">
                <span className="status-label">
                  현재 상태
                </span>

                <span
                  className={`status-badge ${status.expert}`}
                >
                  {getStatusText(
                    status.expert
                  )}
                </span>
              </div>
            </div>
          </div>

          <div className="action-container">
            <button
              className="sr-btn"
              onClick={startMediaCollection}
              style={{marginBottom: "50px"}}
            >
              실시간 AI 분석 시작
            </button>
          </div>
        </div>
      </main>

      <div
        className={`sr-result-dashboard ${
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
            </div>
          ) : (
            <div
              style={{
                textAlign: "center",
              }}
            >
              <h3
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 850,
                  margin: "0 0 8px 0",
                  color: "#03A94D",
                }}
              >
                ✓ 실시간 데이터 파이프라인 분석 완료 (언론 분석)
              </h3>

              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#334155",
                  margin: 0,
                  lineHeight: 1.6,
                }}
              >
                선택된 타임라인 범위 내 총{" "}
                <span
                  style={{
                    fontWeight: 700,
                    color: "#ef4444",
                  }}
                >
                  {analysisResult.collectedArticleCount || analysisResult.articleCount || 0}건
                </span>
                의 수집 기사 중{" "}
                <span
                  style={{
                    fontWeight: 700,
                    color: "#03A94D",
                  }}
                >
                  {analysisResult.filteredArticleCount || 0}건
                </span>
                이 자동 필터를 통과했고, {analysisResult.savedSignalCount || 0}건의 관련 시그널이 식별되었습니다. (관측된 서브이슈: {analysisResult.observedSubIssueCount || 0}개)
                <br />
                <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
                  * 규제·전문기관 분석은 현재 준비 중입니다.
                </span>
                <br /><br />
                다음 스텝인{" "}
                <span
                  style={{
                    fontWeight: 700,
                  }}
                >
                  {
                    steps[
                      activeIndex + 1
                    ]?.title
                  }
                </span>{" "}
                단계 분석으로 이동해 주세요.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Media;
