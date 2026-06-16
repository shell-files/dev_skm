import { useRef, useState, Fragment, useEffect } from "react";
import { useNavigate } from "react-router";
import { useDispatch, useSelector } from "react-redux";
import "@styles/benchmarking.css";
import robot from "@assets/images/robot/robot_repoting_transparent.png";
import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";
import { useAuth } from "@hooks/AuthContext";
import {
  fetchCurrentWorkflow,
  uploadBenchmarkGroup,
  runBenchmarkAnalysis,
  fetchBenchmarkResult,
  fetchDmaWorkflowStatus,
  selectCanRunDmaStage,
  selectDmaGateReason,
} from "@stores/reportSlice";

const BENCHMARK_GROUP_CONFIG = {
  leader: { fileType: "Leader", label: "리더" },
  peer:   { fileType: "Peer",   label: "피어" },
  sub:    { fileType: "Own",    label: "자사" },
};

const mapBenchmarkResultToDashboard = (dto) => ({
  stats: {
    reports: dto.summary?.analyzedReportCount ?? 0,
    leaderCount: dto.summary?.leaderReportCount ?? 0,
    peerCount: dto.summary?.peerReportCount ?? 0,
    ownCount: dto.summary?.ownReportCount ?? 0,
    identifiedIssues: dto.summary?.identifiedIssueCount ?? 0,
    commonIssues: dto.summary?.commonIssueCount ?? 0,
    blindSpots: dto.summary?.blindSpotCount ?? 0,
  },
  topIssues: (dto.topIssues || []).map((item) => ({
    rank: item.rankNo,
    name: item.displaySubIssueName || item.subIssueCode,
    impact: item.benchmarkImpactScore10 ?? item.benchmarkImpactScore05 ?? 0,
    financial: item.benchmarkFinancialScore10 ?? item.benchmarkFinancialScore05 ?? 0,
  })),
  commonIssues: (dto.commonIssues || []).map((item) => ({
    name: item.displaySubIssueName || item.subIssueCode,
    leader: Boolean(item.leaderObserved),
    peer: Boolean(item.peerObserved),
    own: Boolean(item.ownObserved),
  })),
  blindSpots: (dto.blindSpotIssues || []).map((item) => ({
    title: item.displaySubIssueName || item.subIssueCode,
    desc: item.summary || "리더·피어 보고서 대비 자사 보고서에서 관측되지 않은 이슈입니다.",
  })),
});

const Benchmarking = () => {
  const dispatch = useDispatch();
  const currentRunId = useSelector((state) => state.report.currentRunId);
  const approvalProjects = useSelector((state) => state.report?.approval?.projects ?? []);
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.company_id ?? selectedCompany?.companyId;
  const reportingYear = useSelector((state) => state.report.currentYear);

  const workflow = useSelector((state) => state.report.workflow.current);
  const canRunDma = useSelector(selectCanRunDmaStage);
  const gateReason = useSelector(selectDmaGateReason);

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

  const [dashboardData, setDashboardData] = useState(null);

  const particleRef = useRef(null);
  const benchmarkPollTimerRef = useRef(null);
  const benchmarkWorkflowErrorRef = useRef(null);
  const navigate = useNavigate();

  const stopBenchmarkPolling = () => {
    if (benchmarkPollTimerRef.current !== null) {
      clearInterval(benchmarkPollTimerRef.current);
      benchmarkPollTimerRef.current = null;
    }
  };

  const fetchBenchmarkWorkflowStatus = async (runId) => {
    try {
      return await dispatch(
        fetchDmaWorkflowStatus({ runId, workflowType: "BENCHMARK" })
      ).unwrap();
    } catch {
      return null;
    }
  };

  const startBenchmarkPolling = (runId) => {
    stopBenchmarkPolling();
    benchmarkPollTimerRef.current = setInterval(async () => {
      const dto = await fetchBenchmarkWorkflowStatus(runId);
      if (!dto) {
        benchmarkWorkflowErrorRef.current = "벤치마킹 분석 상태 조회에 실패했습니다.";
        stopBenchmarkPolling();
        return;
      }

      setProgress((prev) => Math.max(prev, dto.progressPercent));

      if (dto.overallStatus === "COMPLETED" || dto.overallStatus === "FAILED") {
        stopBenchmarkPolling();
        if (dto.overallStatus === "FAILED") {
          benchmarkWorkflowErrorRef.current =
            dto.errorMessage || "벤치마킹 분석에 실패했습니다.";
        }
      }
    }, 1000);
  };

  useEffect(() => () => stopBenchmarkPolling(), []);

  // 진입 시 reportWorkflow.current 를 확보한다. (G0/롤업 완료 게이트 판정용)
  useEffect(() => {
  if (!workflow && companyId && reportingYear) {
    dispatch(fetchCurrentWorkflow({ companyId, reportingYear }));
  }
  }, [dispatch, workflow, companyId, reportingYear]);


  const steps = [
    { id: 1, title: "벤치마킹 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7" /><line x1="15.5" y1="15.5" x2="21" y2="21" /><line x1="7" y1="13" x2="7" y2="11" /><line x1="10" y1="13" x2="10" y2="8.5" /><line x1="13" y1="13" x2="13" y2="7" /><line x1="6" y1="13" x2="14" y2="13" /></svg>, path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /><polyline points="5,13 8,10 11,12 14,8 19,6" /></svg>, path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" /><line x1="13" y1="11" x2="16" y2="11" /><line x1="13" y1="16" x2="16" y2="16" /></svg>, path: "/survey" },
    { id: 4, title: "전체 결과", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="20" x2="21" y2="20" /><line x1="3" y1="4" x2="3" y2="20" /><rect x="5" y="13" width="3" height="7" /><rect x="10" y="10" width="3" height="10" /><rect x="15" y="8" width="3" height="12" /><circle cx="19" cy="4" r="3" /><polyline points="17.5,4 18.5,5 21,2.5" /></svg>, path: "/result" },
    { id: 5, title: "보고서 초안", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" /></svg>, path: "/draft" },
  ];

  const activeIndex = 0;

  const moveStep = (index) => {
    if (isAnalyzing) return;
    if (index === activeIndex) return;
    navigate(steps[index].path);
  };

  const handleCompanyNameChange = (group, value) => {
    setCompanyNames((prev) => ({ ...prev, [group]: value }));
  };

  const handleFileChange = (e, groupKey) => {
    const newFiles = Array.from(e.target.files);
    if (newFiles.length === 0) return;

    const totalCount = fileStorage[groupKey].length + newFiles.length;
    if (totalCount > 3) {
      showDefaultAlert(
        "파일 업로드 제한",
        `3개년치(3개) 파일만 등록할 수 있습니다.<br/>현재 등록된 파일 수: ${fileStorage[groupKey].length}개`,
        "warning"
      );
      e.target.value = "";
      return;
    }

    for (let file of newFiles) {
      if (file.name.split(".").pop().toLowerCase() !== "pdf") {
        showDefaultAlert(
          "파일 형식 오류",
          `오직 PDF 형식의 문서만 업로드 가능합니다.<br/>대상 파일: ${file.name}`,
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
          `이미 업로드된 파일입니다.<br/>대상 파일: ${file.name}`,
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

  const uploadGroupFiles = async (groupKey) => {
    const group = BENCHMARK_GROUP_CONFIG[groupKey];
    const files = fileStorage[groupKey] || [];

    if (files.length !== 3) {
      throw new Error(`${group.label} 보고서 PDF 3개를 등록해주세요.`);
    }

    const companyName = String(companyNames[groupKey] || "").trim();
    if (!companyName) {
      throw new Error(`${group.label} 기업명을 입력해주세요.`);
    }

    const response = await dispatch(
      uploadBenchmarkGroup({
        fileType: group.fileType,
        companyName,
        files,
        page: "SR",
      })
    ).unwrap();

    const storedFiles = response.data?.files || [];
    if (storedFiles.length !== files.length) {
      throw new Error(`${group.label} 업로드 파일 수가 일치하지 않습니다.`);
    }

    return storedFiles.map((item) => item.fileName);
  };

  const runAnalysis = async () => {
    if (isAnalyzing) return;

    const runId = Number(currentRunId);
    if (!Number.isInteger(runId) || runId <= 0) {
      showDefaultAlert("프로젝트 선택 필요", "현재 보고서 프로젝트를 먼저 선택해주세요.", "warning");
      return;
    }
    const validRunIds = approvalProjects.map((p) => p.runId);
    if (validRunIds.length > 0 && !validRunIds.includes(runId)) {
      showDefaultAlert("프로젝트 선택 필요", "유효하지 않은 프로젝트입니다. 헤더에서 프로젝트를 다시 선택해주세요.", "warning");
      return;
    }

    // G0/롤업 완료 게이트: DMA 단계 진입 전에는 벤치마킹 실행 금지
    if (!canRunDma) {
      showDefaultAlert("실행 불가", gateReason, "warning");
      return;
    }

    if (!companyNames.leader.trim() || !companyNames.peer.trim() || !companyNames.sub.trim()) {
      showDefaultAlert("입력 오류", "모든 그룹의 회사 이름을 입력해주세요.", "warning");
      return;
    }

    if (fileStorage.leader.length !== 3 || fileStorage.peer.length !== 3 || fileStorage.sub.length !== 3) {
      showDefaultAlert("파일 수 부족", "각 그룹별 정확히 3개년치(3개) 파일 업로드가 필수적입니다.", "warning");
      return;
    }

    stopBenchmarkPolling();
    benchmarkWorkflowErrorRef.current = null;

    setDashboardOpen(true);
    setShowResult(false);
    setProgress(0);
    setIsAnalyzing(true);
    showDefaultAlert("분석 시작", "AI 벤치마킹 분석이 시작되었습니다.", "success");

    try {
      setProgress(5);

      const uploadedFileNames = [];
      for (const groupKey of ["leader", "peer", "sub"]) {
        const storedNames = await uploadGroupFiles(groupKey);
        uploadedFileNames.push(...storedNames);
      }

      setProgress(15);

      const analyzePromise = dispatch(
        runBenchmarkAnalysis({ runId, fileNames: uploadedFileNames })
      ).unwrap();

      startBenchmarkPolling(runId);

      try {
        await analyzePromise;
      } catch (analyzeErr) {
        throw new Error(
          benchmarkWorkflowErrorRef.current ||
            analyzeErr?.message ||
            "벤치마킹 분석에 실패했습니다."
        );
      }

      if (benchmarkWorkflowErrorRef.current) {
        throw new Error(benchmarkWorkflowErrorRef.current);
      }

      const finalWorkflow = await fetchBenchmarkWorkflowStatus(runId);

      if (!finalWorkflow) {
        throw new Error("벤치마킹 분석 상태를 확인할 수 없습니다.");
      }
      if (finalWorkflow.overallStatus !== "COMPLETED") {
        throw new Error(finalWorkflow.errorMessage || "벤치마킹 분석이 완료되지 않았습니다.");
      }

      stopBenchmarkPolling();
      setProgress(100);

      const resultResponse = await dispatch(fetchBenchmarkResult({ runId })).unwrap();
      const dto = resultResponse.data ?? resultResponse;
      setDashboardData(mapBenchmarkResultToDashboard(dto));
      setIsAnalyzing(false);
      setShowResult(true);
    } catch (err) {
      console.error(err);
      stopBenchmarkPolling();
      showDefaultAlert("분석 오류", err.message || "벤치마킹 분석 중 오류가 발생했습니다.", "error");
      setIsAnalyzing(false);
      setShowResult(false);
    }
  };

  const renderUploadGroup = (groupKey, label, placeholder) => {
    const files = fileStorage[groupKey];
    const companyName = companyNames[groupKey] || "회사이름";

    return (
      <div className="upload-group-container" id={`group-${groupKey}`}>
        <div className="upload-group-badge">{label}</div>

        <div className="company-top-Bench-input-row">
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

  const displayData = dashboardData;

  return (
    <div className="Bench-container">
      <header className="Bench-header">
        <div className="Bench-stepper-row">
          {steps.map((step, index) => (
            <Fragment key={step.id}>
              <div className={`step-box ${index === activeIndex ? "active" : ""}`} onClick={() => moveStep(index)}>
                <div className="step-icon-circle">{step.icon}</div>
                <div style={{ fontSize: "0.8rem", fontWeight: 850 }}>{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line"></div>}
            </Fragment>
          ))}
        </div>
      </header>

      <main className="Bench-main-content">
        <div className="Bench-input-card">

          {/* ── 페이지 헤더 ── */}
          <div className="bench-page-header">
            <div className="bench-page-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="10" r="7" /><line x1="15.5" y1="15.5" x2="21" y2="21" />
                <line x1="7" y1="13" x2="7" y2="11" /><line x1="10" y1="13" x2="10" y2="8.5" />
                <line x1="13" y1="13" x2="13" y2="7" /><line x1="6" y1="13" x2="14" y2="13" />
              </svg>
            </div>
            <div className="bench-page-text">
              <h2 className="bench-page-title">벤치마킹 분석</h2>
              <p className="bench-page-desc">
                지속가능경영보고서(SR) PDF를 업로드하면 AI가 자동으로 ESG 이슈를 파싱하고,
                리더·피어·자회사 간 공시 현황과 격차(Gap)를 비교·분석합니다.
                각 그룹별 최근 <strong>3개년치</strong> 보고서를 등록하면 분석이 시작됩니다.
              </p>
              <div className="bench-tag-row">
                <span className="bench-tag bench-tag-green">PDF 자동 파싱</span>
                <span className="bench-tag bench-tag-blue">ESG 이슈 자동 식별</span>
                <span className="bench-tag bench-tag-purple">공시 Gap 분석</span>
                <span className="bench-tag bench-tag-orange">3개년 비교</span>
              </div>
            </div>
          </div>

          {/* ── 분석 대상 유형 안내 카드 ── */}
          <div className="bench-type-grid">
            <div className="bench-type-card bench-type-card--green">
              <div className="bench-type-card-head">
                <span className="bench-type-badge bench-type-badge--green">L</span>
                <span className="bench-type-label bench-type-label--green">리더 (Leader)</span>
              </div>
              <p className="bench-type-desc">
                동일 산업군 내 ESG 공시 수준이 가장 높은 벤치마크 기업입니다. 글로벌 표준에 근접한 공시 체계를 목표 기준으로 삼아 자사의 공시 완성도와 개선 방향을 가늠합니다.
              </p>
            </div>
            <div className="bench-type-card bench-type-card--blue">
              <div className="bench-type-card-head">
                <span className="bench-type-badge bench-type-badge--blue">P</span>
                <span className="bench-type-label bench-type-label--blue">피어 (Peer)</span>
              </div>
              <p className="bench-type-desc">
                자사와 업종·규모가 유사한 동종 비교 기업입니다. 시장 내 동등한 위치의 기업과 나란히 비교해 상대적 강·약점을 확인하고 실질적인 개선 여지를 파악합니다.
              </p>
            </div>
            <div className="bench-type-card bench-type-card--orange">
              <div className="bench-type-card-head">
                <span className="bench-type-badge bench-type-badge--orange">S</span>
                <span className="bench-type-label bench-type-label--orange">자회사 (Subsidiary)</span>
              </div>
              <p className="bench-type-desc">
                그룹 내 계열사 또는 종속 기업입니다. 연결 공시 관점에서 그룹 전체 ESG 보고서의 품질을 점검하고, 자회사별 누락 공시 항목을 식별합니다.
              </p>
            </div>
          </div>

          <div className="Bench-upload-section-grid">
            {renderUploadGroup("leader", "리더", "회사이름 필수 입력")}
            {renderUploadGroup("peer", "피어", "회사이름 필수 입력")}
            {renderUploadGroup("sub", "자사", "회사이름 필수 입력")}
          </div>

          {!canRunDma && (
            <div style={{ marginTop: "10px", fontSize: "0.85rem", color: "#b45309", textAlign: "center", fontWeight: 600 }}>
              {gateReason}
            </div>
          )}
          <button
            className="Bench-btn"
            id="bench-btn"
            onClick={runAnalysis}
            disabled={!canRunDma || isAnalyzing}
            title={!canRunDma ? gateReason : ""}
          >
            실시간 AI 분석 시작
          </button>
        </div>
      </main>

      <div className={`dashboard-result-dashboard ${dashboardOpen ? "open " : ""}`} id="dashboard">
        <div className="dashboard-handle" onClick={() => setDashboardOpen(!dashboardOpen)}>
          <div className="handle-pill">
            {isAnalyzing ? "AI 분석 진행 중..." : showResult ? "분석 완료 - 결과 요약 확인" : "실시간 분석 대기 중"}
          </div>
        </div>
        <div className={`robot-view-container ${isAnalyzing ? "analyzing" : ""} ${showResult ? "showing-result" : ""}`}>
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
                  <div style={{ marginTop: "6px", fontWeight: 900, fontSize: "0.85rem", color: "var(--Bench-primary)" }}>
                    {progress}% 분석 중
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="result-layout" id="benchmarking-result">
              <div className="ai-message-box" style={{ marginBottom: "20px" }}>
                <strong style={{ color: "var(--Bench-primary)", fontWeight: 850 }}>
                  [AI 벤치마킹 이슈 도출 및 Gap Analysis]
                </strong>
                <p style={{ margin: "8px 0 0", color: "#334155", fontWeight: 500, lineHeight: 1.5 }}>
                  보고서(SR) 교차 파싱 결과 <strong>{displayData.stats.identifiedIssues}개</strong>의 핵심 이슈가 식별되었습니다. 자사의 누락(Gap) 요소를 보완하여 최적의 초안 요건을 빌드하세요.
                </p>
              </div>

              <div className="result-stats-row">
                <div className="result-stat-card">
                  <div className="stat-icon-wrap">📋</div>
                  <div>
                    <div className="stat-label">분석보고서</div>
                    <div className="stat-value">{displayData.stats.reports}개</div>
                    <div className="stat-sub">
                      리더 {displayData.stats.leaderCount} · 피어 {displayData.stats.peerCount} · 자사 {displayData.stats.ownCount}
                    </div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">≡</div>
                  <div>
                    <div className="stat-label">식별 이슈</div>
                    <div className="stat-value">{displayData.stats.identifiedIssues}개</div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">👥</div>
                  <div>
                    <div className="stat-label">공통 이슈</div>
                    <div className="stat-value">{displayData.stats.commonIssues}개</div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">🎯</div>
                  <div>
                    <div className="stat-label">자사 Blind Spot</div>
                    <div className="stat-value">{displayData.stats.blindSpots}개</div>
                  </div>
                </div>
              </div>

              <div className="result-panels-row">
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
                      {displayData.topIssues.map((item) => (
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
                      {displayData.commonIssues.map((item, index) => (
                        <tr key={index}>
                          <td>{item.name}</td>
                          <td>{item.leader && <span className="chk">✓</span>}</td>
                          <td>{item.peer && <span className="chk">✓</span>}</td>
                          <td>{item.own && <span className="chk">✓</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="result-panel">
                  <div className="panel-header-row">
                    <span className="panel-title">자사 Blind Spot</span>
                    <span className="panel-info-btn">ⓘ</span>
                  </div>
                  <ul className="blind-spot-list">
                    {displayData.blindSpots.map((item, index) => (
                      <li key={index}>
                        <div className="blind-spot-title">{item.title}</div>
                        <p className="blind-spot-desc">{item.desc}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div style={{ textAlign: "center", marginTop: "20px" }}>
                <button
                  type="button"
                  className="Bench-btn"
                  style={{ maxWidth: "320px", margin: "0 auto" }}
                  onClick={() => navigate("/media")}
                >
                  다음 단계: 미디어 분석으로 이동
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Benchmarking;
