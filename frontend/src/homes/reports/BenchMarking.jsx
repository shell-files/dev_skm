/* ============================================================================
 *  [병합 작업 요약]  benchmarking.jsx(소문자) → BenchMarking.jsx(대문자) 통합
 * ----------------------------------------------------------------------------
 *  - 베이스: 대문자 BenchMarking.jsx (정상 동작하는 React 컴포넌트) 유지
 *  - 이식:   소문자 파일의 "통계카드 4개 + 3패널"만 React 문법으로 변환해 추가
 *  - 숫자:   현재는 더미. 백엔드 연동 시 dashboardData 한 곳만 교체하면 됨
 *
 *  ▶ 코드에서 [병합-추가] = 이번에 새로 들어간 부분
 *             [병합-수정] = 기존 코드를 살짝 손본 부분
 *             (주석 없는 부분은 대문자 원본 그대로)
 * ========================================================================== */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/benchmarking.css";
import robot from "@assets/images/robot/robot_repoting_transparent.png";
import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

import axios from 'axios';
import { POST } from "@utils/Network";

const USE_DUMMY = true; // true: 더미 모드, false: 실제 API 연동 모드

// 온톨로지 사전 구조에 맞춘 실전형 더미 데이터 세트 (총 20개 로우 샘플)
const DUMMY_DB_RESULTS = [
  { domain: "E", selected_issue: "기후변화·온실가스", selected_sub_issue: "회사의 기후변화 대응 거버넌스, 온실가스(GHG) 산정체계 및 인벤토리 구축, 배출계수 적용을 설명하는 문장.", type: "leader" },
  { domain: "E", selected_issue: "기후변화·온실가스", selected_sub_issue: "회사의 기후변화 대응 거버넌스, 온실가스(GHG) 산정체계 및 인벤토리 구축, 배출계수 적용을 설명하는 문장.", type: "peer" },
  { domain: "E", selected_issue: "수자원·폐수 관리", selected_sub_issue: "취수량 저감 및 취수원 리스크 관리, 공정 내 용수 재활용률 확대, 자원 순환 체계 수립 현황을 설명하는 문장.", type: "leader" },
  { domain: "E", selected_issue: "폐기물·자원순환", selected_sub_issue: "사업장 폐기물 총량 관리, 폐기물 매립 제로(ZWTL) 인증 획득 및 순환 자원 전환 노력을 설명하는 문장.", type: "leader" },
  { domain: "E", selected_issue: "폐기물·자원순환", selected_sub_issue: "사업장 폐기물 총량 관리, 폐기물 매립 제로(ZWTL) 인증 획득 및 순환 자원 전환 노력을 설명하는 문장.", type: "peer" },
  { domain: "E", selected_issue: "폐기물·자원순환", selected_sub_issue: "사업장 폐기물 총량 관리, 폐기물 매립 제로(ZWTL) 인증 획득 및 순환 자원 전환 노력을 설명하는 문장.", type: "sub" },
  { domain: "E", selected_issue: "친환경 제품·Eco-Design", selected_sub_issue: "제품 설계 단계의 환경성 검토, 친환경 인증 원부자재 도입 및 Eco-Design 프로세스를 설명하는 문장.", type: "peer" },

  { domain: "S", selected_issue: "안전보건 보장", selected_sub_issue: "안전보건 경영시스템(ISO 45001) 인증 및 전사 재해율 관리, 유해 위험요인 상시 발굴 체계를 설명하는 문장.", type: "leader" },
  { domain: "S", selected_issue: "안전보건 보장", selected_sub_issue: "안전보건 경영시스템(ISO 45001) 인증 및 전사 재해율 관리, 유해 위험요인 상시 발굴 체계를 설명하는 문장.", type: "peer" },
  { domain: "S", selected_issue: "안전보건 보장", selected_sub_issue: "안전보건 경영시스템(ISO 45001) 인증 및 전사 재해율 관리, 유해 위험요인 상시 발굴 체계를 설명하는 문장.", type: "sub" },
  { domain: "S", selected_issue: "공급망 ESG 관리", selected_sub_issue: "협력사 ESG 행동규범 제정, 서면 및 실사 평가 프로세스 구축, 공급망 지속가능성 리스크 실사 대응을 설명하는 문장.", type: "leader" },
  { domain: "S", selected_issue: "공급망 ESG 관리", selected_sub_issue: "협력사 ESG 행동규범 제정, 서면 및 실사 평가 프로세스 구축, 공급망 지속가능성 리스크 실사 대응을 설명하는 문장.", type: "peer" },
  { domain: "S", selected_issue: "인권 경영 체계", selected_sub_issue: "UNGP 기준 인권정책 선언, 전사 인권 영향평가 실시 및 인권침해 고충처리 채널 활성화를 설명하는 문장.", type: "leader" },
  { domain: "S", selected_issue: "정보보안·개인정보", selected_sub_issue: "정보보호 관리체계(ISMS-P, ISO 27001) 운영, 개인정보 유출 방지 시스템 및 보안 사고 모니터링을 설명하는 문장.", type: "leader" },
  { domain: "S", selected_issue: "정보보안·개인정보", selected_sub_issue: "정보보호 관리체계(ISMS-P, ISO 27001) 운영, 개인정보 유출 방지 시스템 및 보안 사고 모니터링을 설명하는 문장.", type: "peer" },
  { domain: "S", selected_issue: "정보보안·개인정보", selected_sub_issue: "정보보호 관리체계(ISMS-P, ISO 27001) 운영, 개인정보 유출 방지 시스템 및 보안 사고 모니터링을 설명하는 문장.", type: "sub" },

  { domain: "G", selected_issue: "이사회 구성 및 독립성", selected_sub_issue: "이사회 내 사외이사 구성 비율, 이사회 의장과 CEO 분리 여부, 사외이사 후보추천위 독립성을 설명하는 문장.", type: "leader" },
  { domain: "G", selected_issue: "이사회 구성 및 독립성", selected_sub_issue: "이사회 내 사외이사 구성 비율, 이사회 의장과 CEO 분리 여부, 사외이사 후보추천위 독립성을 설명하는 문장.", type: "peer" },
  { domain: "G", selected_issue: "이사회 구성 및 독립성", selected_sub_issue: "이사회 내 사외이사 구성 비율, 이사회 의장과 CEO 분리 여부, 사외이사 후보추천위 독립성을 설명하는 문장.", type: "sub" },
  { domain: "G", selected_issue: "윤리·준법경영 시스템", selected_sub_issue: "부패방지 경영시스템(ISO 37001) 운영, 임직원 윤리강령 준수 서약, 내부고발제도 활성화를 설명하는 문장.", type: "leader" },
  { domain: "G", selected_issue: "윤리·준법경영 시스템", selected_sub_issue: "부패방지 경영시스템(ISO 37001) 운영, 임직원 윤리강령 준수 서약, 내부고발제도 활성화를 설명하는 문장.", type: "peer" },
  { domain: "G", selected_issue: "윤리·준법경영 시스템", selected_sub_issue: "부패방지 경영시스템(ISO 37001) 운영, 임직원 윤리강령 준수 서약, 내부고발제도 활성화를 설명하는 문장.", type: "sub" },
];

// ════════════════════════════════════════════════════════════════
// [병합-추가] 결과 대시보드(통계카드 + 3패널)용 더미 데이터.
//   - 소문자 파일에선 HTML에 하드코딩돼 있던 값을 객체로 구조화한 것.
//   - 나중에 백엔드 연동 시, 응답을 이 객체와 같은 형태로 받아
//     setDashboardData(response.data.dashboard) 한 줄로 교체하면 됨.
// ════════════════════════════════════════════════════════════════
const DUMMY_RESULT_DASHBOARD = {stats:{
    reports: 24,
    leaderCount: 8,
    peerCount: 8,
    subcount: 8,
    commonIssues: 19,
    blindSpots: 9,
  }
,
// 패널1: 벤치마킹 Top 이슈 점수
  topIssues: [
    { rank: 1, name: "기후변화·온실가스", impact: 9.2, financial:8.7 },
    { rank: 2, name: "수자원·폐수 관리", impact: 8.6, financial: 7.9} ,
    { rank: 3, name :"폐기물·자원순환", impact: 8.1, financial: 7.6} ,
    { rank: 4, name :"친환경 제품·Eco-Design", impact: 7.8, financial: 7.3} ,
    { rank: 5, name :"공급망 ESG 관리", impact: 7.4, financial: 6.8} ,
  ],
  // 패널2: 공통 선정 이슈
  commonIssues: [
    { name: "기후변화·온실가스", leader: true, peer: true, sub: true },
    { name: "폐기물·자원순환", leader: true, peer: true, sub: true },
    { name: "제품안전·품질", leader: true, peer: true, sub: true },
    { name: "공급망 ESG 관리", leader: true, peer: true, sub: true },
    { name: "공급망 ESG 관리", leader: true, peer: true, sub: true },
  ],
   // 패널3: 자사 Blind Spot
   blindSpots : [
    {title: "생물다양성 영향 관리", desc: "생물다양성 리스크·영향 평가 및 관리 체계가 보고서에서 상대적으로 낮게 다뤄지고 있습니다."},
    { title: "인권 실사 및 관리", desc: "인권 실사 프로세스 및 고충처리 체계에 대한 정보가 상대적으로 부족합니다." },
     { title: "ESG 데이터 관리 체계", desc: "ESG 데이터 수집·관리·검증 체계의 고도화 및 거버넌스 정보가 미흡합니다." },
  ],  
}
  


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

  // API 혹은 더미로부터 들어오는 원본 Row 보관 상태
  const [rawRows, setRawRows] = useState([]);
  // [병합-추가] 결과 대시보드(통계카드 + 3패널) 데이터 상태.
  //   백엔드 연동 전까지는 더미를 기본값으로 사용.
  const [dashboardData, setDashobardData] = useState(DUMMY_RESULT_DASHBOARD);

  const particleRef = useRef(null);
  const navigate = useNavigate();

  const steps = [
    { id: 1, title: "벤치마킹 분석", icon: "🎯", path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: "📺", path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: "👥", path: "/survey" },
    { id: 4, title: "전체 결과", icon: "📊", path: "/result" },
    { id: 5, title: "보고서 초안", icon: "📄", path: "/draft" },
  ];

  const activeIndex = 0;

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

            if (USE_DUMMY) {
              setRawRows(DUMMY_DB_RESULTS);
            }

            return 100;
          }
          return prev + 2;
        });
      }, 30);
    }

    return () => clearInterval(interval);
  }, [isAnalyzing]);

  /**
   * DB 로우 데이터를selected_issue 기준으로 압축 결합하는 로직
   * subIssueSentence(문장)를 framework 매핑 항목으로 치환하여 병합합니다.
   */
  const getGroupedIssues = () => {
    const map = {};

    rawRows.forEach((row) => {
      const key = row.selected_issue;
      if (!map[key]) {
        map[key] = {
          title: row.selected_issue,
          category: row.domain || "E",
          sentence: row.selected_sub_issue || "정의된 서브 이슈 문장이 없습니다.",
          leader: false,
          peer: false,
          sub: false,
        };
      }

      if (row.type === "leader") map[key].leader = true;
      if (row.type === "peer") map[key].peer = true;
      if (row.type === "sub") map[key].sub = true;
    });

    return Object.values(map);
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

  const handleCompanyNameChange = (group, value) => {
    setCompanyNames((prev) => ({
      ...prev,
      [group]: value,
    }));
  };

  const handleFileChange = (e, groupKey) => {
    const newFiles = Array.from(e.target.files);
    if (newFiles.length === 0) return;

    const totalCount = fileStorage[groupKey].length + newFiles.length;

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
      if (file.name.split(".").pop().toLowerCase() !== "pdf") {
        showDefaultAlert(
          "파일 형식 오류",
          `오직 PDF 형식의 문서만 업로드 가능합니다.<br/>
          대상 파일: ${file.name}`,
          "error"
        );
        e.target.value = "";
        return;
      }

      const isDuplicate = fileStorage[groupKey].some(
        (existingFile) => existingFile.name === file.name
      );
      if (isDuplicate) {
        showDefaultAlert(
          "중복 파일 오류",
          `이미 업로드된 파일입니다.<br/>
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
      [groupKey]: prev[groupKey].filter((_, i) => i !== index),
    }));
  };

  const runAnalysis = async () => {
    if (isAnalyzing) return;

    if (!companyNames.leader.trim() || !companyNames.peer.trim() || !companyNames.sub.trim()) {
      showDefaultAlert("입력 오류", "모든 그룹의 회사 이름을 입력해주세요.", "warning");
      return;
    }

    if (fileStorage.leader.length !== 3 || fileStorage.peer.length !== 3 || fileStorage.sub.length !== 3) {
      showDefaultAlert("파일 수 부족", "각 그룹별 정확히 3개년치(3개) 파일 업로드가 필수적입니다.", "warning");
      return;
    }

    setDashboardOpen(true);
    setShowResult(false);
    setProgress(0);
    setIsAnalyzing(true);
    showDefaultAlert("분석 시작", "AI 벤치마킹 분석이 시작되었습니다.", "success");

    if (!USE_DUMMY) {
      try {
        const response = await POST("skm", "/api/v1/benchmark/analyze", {
          companyNames,
          files: fileStorage,
        });
        if (response && response.status !== false) {
          setRawRows(response.data || []);
          // [병합-추가/백엔드 TODO] 통계카드 + 3패널 데이터도 응답에서 주입.
          //   응답이 DUMMY_RESULT_DASHBOARD와 같은 형태라면 아래 한 줄이면 됨:
          // setDashboardData(response.data.dashboard);
        } else {
          showDefaultAlert("데이터 분석 오류", "네트워크 통신 중 에러가 발생했습니다.", "error");
        }
      } catch (err) {
        console.error(err);
      }
    }
  };

  const renderUploadGroup = (groupKey, label, placeholder) => {
    const files = fileStorage[groupKey];
    const companyName = companyNames[groupKey] || "회사이름";

    return (

      <div className="upload-group-container" id={`group-${groupKey}`}>
        <div className="upload-group-badge">{label}</div>

        <div className="company-top-input-row">
          <input
            type="text"
            className="company-name-input"
            placeholder={placeholder}
            value={companyNames[groupKey]}
            onChange={(e) => handleCompanyNameChange(groupKey, e.target.value)}
          />

          <label className="inline-upload-btn">
            업로드
            <input
              type="file"
              hidden
              multiple
              accept=".pdf"
              onChange={(e) => handleFileChange(e, groupKey)}
            />
          </label>
        </div>

        <div className="file-list-container">
          {files.length === 0 ? (
            <div className="empty-file-text">3개년치 파일 필수 업로드</div>
          ) : (
            files.map((file, index) => (
              <div className="file-item-box" key={index}>
                <div className="file-info-text">
                  <div className="mock-label">{companyName}</div>
                  <div className="file-status-text" title={file.name}>
                    업로드 파일 : {file.name}
                  </div>
                </div>

                <button
                  className="file-cancel-btn"
                  onClick={async () => {
                    const confirmed = await showConfirmAlert("파일 삭제", "선택한 파일을 삭제하시겠습니까?", "warning");
                    if (confirmed) removeFile(groupKey, index);
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

  const processedIssues = getGroupedIssues();

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

      <main className="main-content">
        <div className="input-card" style={{ marginBottom: "50px" }}>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 850, marginBottom: "6px" }}>벤치마킹 분석</h2>
          <p style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: "4px" }}>
            산업군 리더 기업들의 공시 지표를 수집하고 우리 기업과의 격차 분석을 시작합니다.
          </p>

          <div className="upload-section-grid">
            {renderUploadGroup("leader", "리더", "회사이름 필수 입력")}
            {renderUploadGroup("peer", "피어", "회사이름 필수 입력")}
            {renderUploadGroup("sub", "자회사", "회사이름 필수 입력")}
          </div>

          <button className="sr-btn" id="bench-btn" onClick={runAnalysis}> 실시간 AI 분석 시작</button>
        </div>
      </main>

      <div className={`sr-result-dashboard ${dashboardOpen ? "open" : ""}`} id="dashboard">
        <div className="dashboard-handle" onClick={() => setDashboardOpen(!dashboardOpen)}>
          <div className="handle-pill">
            {isAnalyzing ? "AI 분석 진행 중..." : showResult ? "분석 완료 - 결과 요약 확인" : "실시간 분석 대기 중"}
          </div>
        </div>
          {/* [병합-수정] showResult일 때 showing-result 클래스 부여 → 결과 길어지면 내부 스크롤 (CSS와 연동) */}
        <div className={`robot-view-container ${isAnalyzing ? "analyzing" : ""} ${showResult ? "showing-result":""}`}>
          <div id="particle-field" className="particle-field" ref={particleRef}></div>

          {!showResult ? (
            <div id="loading-content" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div className="robot-stage">
                <div className="robot-float-wrap">
                  <img src={robot} className="robot-main-img mascot-entrance-pop" alt="robot" />
                </div>
              </div>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 850, margin: "0 0 4px 0" }}>
                {isAnalyzing ? "벤치마킹 분석 진행 중..." : "분석 준비가 완료되었습니다"}
              </h3>
              {isAnalyzing && (
                <div className="progress-section">
                  <div className="progress-bar-wrap">
                    <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
                  </div>
                  <div style={{ marginTop: "6px", fontWeight: 900, fontSize: "0.85rem", color: "var(--sr-primary)" }}>
                    {progress}% 분석 중
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="result-layout" id="benchmarking-result">
              <div className="ai-message-box" style={{ marginBottom: "20px" }}>
                <strong style={{ color: "var(--sr-primary)", fontWeight: 850 }}>
                  [AI 벤치마킹 이슈 도출 및 Gap Analysis]
                </strong>
                <p style={{ margin: "8px 0 0", color: "#334155", fontWeight: 500, lineHeight: 1.5 }}>
                  보고서(SR) 교차 파싱 결과 <strong>{processedIssues.length}개</strong>의 핵심 이슈가 식별되었습니다. 자회사의 누락(Gap) 요소를 보완하여 최적의 초안 요건을 빌드하세요.
                </p>
              </div>

               {/* 통계 카드 4개 */}
               <div className = "result-stats-row">
                <div className="result-stat-card">
                  <div className="stat-icon-wrap">📋</div>
                  <div>
                    <div className="stat-label"> 분석보고서</div>
                    <div className="stat-value">{dashboardData.stats.reports}개</div>
                    <div className="stat-sub">
                      리더 {dashboardData.stats.leaderCount} · 피어 {dashboardData.stats.peerCount} · 자회사 {dashboardData.stats.subcount}
                    </div>
                    </div>  
                    </div>
                
                <div className="result-stat-card">
                  <div className="stat-icon-wrap">≡</div>
                  <div>
                    <div className="stat-label">식별 이슈</div>
                    <div className="stat-value">{dashboardData.stats.identifiedIssues}개</div>
                  </div>
                </div>
                <div className="result-stat-card">
                  <div className="stat-icon-wrap">👥</div>
                  <div>
                    <div className="stat-label"> 공통 이슈</div>
                    <div className="stat-value">{dashboardData.stats.commonIssues}개</div>
                  </div>
                </div>

                
                  <div className="result-stat-card">
                    <div className="stat-icon-wrap">🎯</div>
                    <div>
                      <div className="stat-label">자사 Blind Spot</div>
                      <div className="stat-value">{dashboardData.stats.blindSpots}개</div>
                    </div>
                  </div>
              </div>
                {/* 하단 3패널 (Top 이슈 점수 / 공통 선정 이슈 / Blind Spot) */}
              <div className="result-panels-row">
                {/* 패널1: 벤치마킹 Top 이슈 점수 */}
                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">벤치마킹 Top 이슈 점수</span>
                    <span className="panel-info-btn">ⓘ</span>
                  </div>
                  <table className="issue-table">
                    <thead>
                      <tr><th>순위</th><th>Sub Issue</th><th>Impact</th><th>Financial</th></tr>
                    </thead>
                    <tbody>
                      {dashboardData.topIssues.map((item) => (
                        <tr key={item.rank}>
                          <td>{item.rank}</td>
                          <td>{item.name}</td>
                          <td>{item.impact}</td>
                          <td>{item.financial}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 패널2: 공통 선정 이슈 */}
                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">공통 선정 이슈</span>
                    <span className="panel-info-btn">ⓘ</span>
                  </div>
                  <table className="issue-table">
                    <thead>
                      <tr><th>Sub Issue</th><th>리더</th><th>피어</th><th>자사</th></tr>
                    </thead>
                    <tbody>
                      {dashboardData.commonIssues.map((item, index) => (
                        <tr key={index}>
                          <td>{item.name}</td>
                          <td>{item.leader && <span className="chk">✓</span>}</td>
                          <td>{item.peer && <span className="chk">✓</span>}</td>
                          <td>{item.sub && <span className="chk">✓</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 패널3: 자사 Blind Spot */}
                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">자사 Blind Spot</span>
                    <span className="panel-info-btn">ⓘ</span>
                  </div>
                  <ul className="blind-spot-list">
                    {dashboardData.blindSpots.map((item, index) => (
                      <li key={index}>
                        <div className="blind-spot-title">{item.title}</div>
                        <p className="blind-spot-desc">{item.desc}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>





              {/* 개선된 1컬럼 스택트 레이아웃 테이블 */}
              <div className="gap-analysis-container">
                <div className="gap-table-header">
                  <div className="col-info-stacked-header">식별된 ESG 이슈그룹 및 세부 분석 문장(Sub Issue)</div>
                  <div className="col-status-group-header">
                    <div className="status-label">리더</div>
                    <div className="status-label">피어</div>
                    <div className="status-label">자회사</div>
                  </div>
                </div>

                <div className="gap-table-body">
                  {processedIssues.map((issue, index) => (
                    <div className="gap-table-row" key={index}>
                      {/* 좌측: 이슈 대분류 태그 + 이슈그룹명 + 세부 문장 수직 누적 배치 */}
                      <div className="col-info-stacked">
                        <div className="issue-main-row">
                          <span className={`category-tag tag-${issue.category.toLowerCase()}`}>
                            {issue.category}
                          </span>
                          <span className="issue-title-text">{issue.title}</span>
                        </div>
                        <div className="issue-sub-sentence">
                          {issue.sentence}
                        </div>
                      </div>

                      {/* 우측: 공시 여부 심볼 체계 */}
                      <div className="col-status-group">
                        <div className="status-cell">
                          <span className={`status-dot ${issue.leader ? "checked" : "empty"}`}>
                            {issue.leader ? "●" : "○"}
                          </span>
                        </div>
                        <div className="status-cell">
                          <span className={`status-dot ${issue.peer ? "checked" : "empty"}`}>
                            {issue.peer ? "●" : "○"}
                          </span>
                        </div>
                        <div className="status-cell">
                          <span className={`status-dot ${issue.sub ? "checked" : "unreported"}`}>
                            {issue.sub ? "●" : "✕"}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Benchmarking;