import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/benchmarking.css";
import robot from "@assets/images/robot/robot_repoting_transparent.png";
import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

import axios from 'axios';

const Benchmarking = () => {
  const [fileStorage, setFileStorage] = useState({
    leader: [],
    peer: [],
    sub: [],
  });

  const [companyNames, setCompanyNames] = useState({
    leader: "",
    peer: "",
    sub: "",
  });

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [showResult, setShowResult] = useState(false);

  const particleRef = useRef(null);
  const navigate = useNavigate();
  /**
   * ESG 보고서 생성 프로세스 단계 정의
   * path 기준으로 페이지 이동 처리
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

  const activeIndex = 0;
  /**
   * Step 이동 처리 함수
   * 분석 중에는 다른 페이지 이동 제한
   */
  const moveStep = (index) => {
    if (isAnalyzing) return;

    if (index === activeIndex) return;

    navigate(steps[index].path);
  };
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

  const handleCompanyNameChange = (group, value) => {
    setCompanyNames((prev) => ({
      ...prev,
      [group]: value,
    }));
  };

  const handleFileChange = (e, groupKey) => {
    const newFiles = Array.from(e.target.files);

    if (newFiles.length === 0) return;

    const totalCount =
      fileStorage[groupKey].length + newFiles.length;

    if (totalCount > 3) {
      showDefaultAlert(
        "파일 업로드 제한",
        `3개년치(3개) 파일만 등록할 수 있습니다.<br/>
        현재 등록된 파일 수: ${fileStorage[groupKey].length}개`,
        "warning"
      );

      e.target.value = "";
      return;
    }

    for (let file of newFiles) {
      if (
        file.name.split(".").pop().toLowerCase() !== "pdf"
      ) {
        showDefaultAlert(
          "파일 형식 오류",
          `오직 PDF 형식의 문서만 업로드 가능합니다.<br/>
          대상 파일: ${file.name}`,
          "error"
        );

        e.target.value = "";
        return;
      }
    }

    setFileStorage((prev) => ({
      ...prev,
      [groupKey]: [...prev[groupKey], ...newFiles],
    }));

    e.target.value = "";
  };

  const removeFile = (groupKey, index) => {
    setFileStorage((prev) => ({
      ...prev,
      [groupKey]: prev[groupKey].filter(
        (_, i) => i !== index
      ),
    }));
  };

  const runAnalysis = async() => {
    if (isAnalyzing) return;

    if (!companyNames.leader.trim()) {
      showDefaultAlert(
        "입력 오류",
        "리더 그룹의 회사 이름을 입력해주세요.",
        "warning"
      );
      return;
    }

    if (!companyNames.peer.trim()) {
      showDefaultAlert(
        "입력 오류",
        "피어 그룹의 회사 이름을 입력해주세요.",
        "warning"
      );
      return;
    }

    if (!companyNames.sub.trim()) {
      showDefaultAlert(
        "입력 오류",
        "자회사 이름을 입력해주세요.",
        "warning"
      );
      return;
    }

    if (fileStorage.leader.length !== 3) {
      showDefaultAlert(
        "파일 수 부족",
        `[${companyNames.leader}] 그룹은 정확히 3개의 파일이 필요합니다.`,
        "warning"
      );
      return;
    }

    if (fileStorage.peer.length !== 3) {
      showDefaultAlert(
        "파일 수 부족",
        `[${companyNames.peer}] 그룹은 정확히 3개의 파일이 필요합니다.`,
        "warning"
      );
      return;
    }

    if (fileStorage.sub.length !== 3) {
      showDefaultAlert(
        "파일 수 부족",
        `[${companyNames.sub}] 그룹은 정확히 3개의 파일이 필요합니다.`,
        "warning"
      );
      return;
    }

    setDashboardOpen(true);
    setShowResult(false);
    setProgress(0);
    setIsAnalyzing(true);
    showDefaultAlert(
      "분석 시작",
      "AI 벤치마킹 분석이 시작되었습니다.",
      "success"
    );
  };

  const renderUploadGroup = (
    groupKey,
    label,
    placeholder
  ) => {
    const files = fileStorage[groupKey];
    const companyName =
      companyNames[groupKey] || "회사이름";

    return (
      <div
        className="upload-group-container"
        id={`group-${groupKey}`}
      >
        <div className="upload-group-badge">
          {label}
        </div>

        <div className="company-top-input-row">
          <input
            type="text"
            className="company-name-input"
            placeholder={placeholder}
            value={companyNames[groupKey]}
            onChange={(e) =>
              handleCompanyNameChange(
                groupKey,
                e.target.value
              )
            }
          />

          <label className="inline-upload-btn">
            업로드

            <input
              type="file"
              hidden
              multiple
              accept=".pdf"
              onChange={(e) =>
                handleFileChange(e, groupKey)
              }
            />
          </label>
        </div>

        <div className="file-list-container">
          {files.length === 0 ? (
            <div className="empty-file-text">
              3개년치 파일 필수 업로드 (정확히 3개)
            </div>
          ) : (
            files.map((file, index) => (
              <div
                className="file-item-box"
                key={index}
              >
                <div className="file-info-text">
                  <div className="mock-label">
                    {companyName}
                  </div>

                  <div
                    className="file-status-text"
                    title={file.name}
                  >
                    업로드 파일 : {file.name}
                  </div>
                </div>

                <button
                  className="file-cancel-btn"
                  onClick={async () => {
                    const confirmed = await showConfirmAlert(
                      "파일 삭제",
                      "선택한 파일을 삭제하시겠습니까?",
                      "warning"
                    );

                    if (confirmed) {
                      removeFile(groupKey, index);
                    }
                  }}
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    );
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
                    fontWeight: 850,
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
            }}
          >
            벤치마킹 분석
          </h2>

          <p
            style={{
              color: "#64748b",
              fontSize: "0.9rem",
              marginBottom: "4px",
              lineHeight: 1.5,
            }}
          >
            산업군 리더 기업들의 공시 지표를 수집하고
            우리 기업과의 격차 분석을 시작합니다.
          </p>

          <p
            style={{
              color: "#64748b",
              fontSize: "0.9rem",
              marginBottom: "4px",
              lineHeight: 1.5,
            }}
          >
            업로드된 지속가능경영보고서(SR)를 기반으로
            산업군별 ESG 공시 전략, 핵심 지표 및
            중대 이슈 대응 수준을 AI가 비교 분석합니다.
          </p>

          <div className="upload-section-grid">
            {renderUploadGroup(
              "leader",
              "리더",
              "회사이름 필수 입력"
            )}

            {renderUploadGroup(
              "peer",
              "피어",
              "회사이름 필수 입력"
            )}

            {renderUploadGroup(
              "sub",
              "자회사",
              "회사이름 필수 입력"
            )}
          </div>

          <button
            className="sr-btn"
            onClick={runAnalysis}
          >
            ⚡ 실시간 AI 분석 시작
          </button>
        </div>
      </main>

      <div
        className={`sr-result-dashboard ${
          dashboardOpen ? "open" : ""
        }`}
        id="dashboard"
      >
        <div
          className="dashboard-handle"
          onClick={() =>
            setDashboardOpen(!dashboardOpen)
          }
        >
          <div className="handle-pill">
            {isAnalyzing
              ? "AI 분석 진행 중..."
              : showResult
              ? "분석 완료 - 결과 요약 확인"
              : "실시간 분석 대기 중"}
          </div>
        </div>

        <div
          className={`robot-view-container ${
            isAnalyzing ? "analyzing" : ""
          }`}
        >
          <div
            id="particle-field"
            className="particle-field"
            ref={particleRef}
          ></div>

          {!showResult ? (
            <div
              id="loading-content"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div className="robot-stage">
                <div className="robot-float-wrap">
                  <img
                    src={robot}
                    className="robot-main-img mascot-entrance-pop"
                    alt="robot"
                  />
                </div>
              </div>

              <h3
                style={{
                  fontSize: "1.2rem",
                  fontWeight: 850,
                  margin: "0 0 4px 0",
                }}
              >
                {isAnalyzing
                  ? "벤치마킹 분석 진행 중..."
                  : "분석 준비가 완료되었습니다"}
              </h3>

              <p
                style={{
                  fontSize: "0.85rem",
                  color: "#64748b",
                  margin: 0,
                }}
              >
                {isAnalyzing
                  ? "업로드한 3개년 지속가능경영보고서(SR) 통합 대조 분석 중입니다."
                  : "상단의 분석 시작 버튼을 눌러주세요."}
              </p>

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
                      fontWeight: 900,
                      fontSize: "0.85rem",
                      color: "var(--sr-primary)",
                    }}
                  >
                    {progress}% 분석 중
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="result-layout">
              <div className="summary-grid">
                <div className="summary-card">
                  <span className="label">
                    분석 단계
                  </span>

                  <div className="value">
                    벤치마킹
                  </div>
                </div>

                <div className="summary-card">
                  <span className="label">
                    AI 인사이트
                  </span>

                  <div className="value">
                    우수 <span>(Positive)</span>
                  </div>
                </div>

                <div className="summary-card">
                  <span className="label">
                    리스크 지수
                  </span>

                  <div
                    className="value"
                    style={{
                      color:
                        "var(--sr-primary)",
                    }}
                  >
                    Low <span>(12.5)</span>
                  </div>
                </div>
              </div>

              <div className="ai-message-box">
                <strong
                  style={{
                    color: "var(--sr-primary)",
                    fontWeight: 850,
                  }}
                >
                  [AI 인사이트 요약]
                </strong>

                <p
                  style={{
                    margin: "8px 0 0",
                    color: "#334155",
                    fontWeight: 500,
                  }}
                >
                  현재 단계를 분석한 결과, 업계 평균
                  대비 환경(E) 부문에서 12% 높은
                  성과를 기록하고 있습니다.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Benchmarking;