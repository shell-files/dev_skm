/**
 * BenchMarking.jsx
 * 레이어: Page
 * 역할: 리더·피어·자사 ESG 보고서(SR) PDF를 업로드하여 AI 벤치마킹 분석을 실행하고, 이슈 점수·공통 이슈·Blind Spot 결과를 표시하는 페이지
 */
import { useRef, useState, Fragment, useEffect } from "react";
import { useNavigate } from "react-router";
import { useDispatch, useSelector } from "react-redux";
import "@styles/benchmarking.css";
import "@styles/dma-robot-stage.css";
import RankBadge from "@components/UI/RankBadge";
import robot from "@assets/images/robot/robot_repoting_transparent.png";
import benchIcon from "@assets/icons/steps/benchmarking.png";
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
  leader: { fileType: "Leader", label: "리더",  letter: "L", color: "green"  },
  peer:   { fileType: "Peer",   label: "피어",  letter: "P", color: "blue"   },
  sub:    { fileType: "Own",    label: "자사",  letter: "S", color: "orange" },
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

  // 페이지 재진입 시 현재 runId의 기존 벤치마킹 결과 복원
  useEffect(() => {
    if (!currentRunId || isAnalyzing) return;
    const runId = Number(currentRunId);
    if (!runId) return;

    dispatch(fetchBenchmarkResult({ runId }))
      .unwrap()
      .then((res) => {
        const dto = res.data ?? res;
        if (dto?.topIssues?.length > 0 || dto?.summary?.analyzedReportCount > 0) {
          setDashboardData(mapBenchmarkResultToDashboard(dto));
          setShowResult(true);
          setDashboardOpen(true);
        }
      })
      .catch(() => { });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRunId, dispatch]);


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
        `최대 3개 파일까지 등록할 수 있습니다.<br/>현재 등록된 파일 수: ${fileStorage[groupKey].length}개`,
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

    if (files.length < 1 || files.length > 3) {
      throw new Error(`${group.label} 보고서 PDF를 1~3개 등록해주세요.`);
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

    if (showResult) {
      const confirmed = await showConfirmAlert(
        "재분석 확인",
        "이미 벤치마킹 결과가 존재합니다.<br/>기존 데이터를 삭제하고 다시 분석하시겠습니까?",
        "warning"
      );
      if (!confirmed) return;
    }

    if (!companyNames.leader.trim() || !companyNames.peer.trim() || !companyNames.sub.trim()) {
      showDefaultAlert("입력 오류", "모든 그룹의 회사 이름을 입력해주세요.", "warning");
      return;
    }

    if (fileStorage.leader.length === 0 || fileStorage.peer.length === 0 || fileStorage.sub.length === 0) {
      showDefaultAlert("파일 미등록", "각 그룹별 최소 1개 파일 업로드가 필요합니다.", "warning");
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

  const renderUploadGroup = (groupKey) => {
    const { label, letter, color } = BENCHMARK_GROUP_CONFIG[groupKey];
    const files = fileStorage[groupKey];
    const companyName = companyNames[groupKey] || "회사이름";

    return (
      <div className={`upload-group-container upload-group--${color}`} id={`group-${groupKey}`}>

        {/* 카드 헤더 */}
        <div className="upload-group-header">
          <span className={`upload-group-letter upload-group-letter--${color}`}>{letter}</span>
          <div>
            <div className={`upload-group-label upload-group-label--${color}`}>{label}</div>
            <div className="upload-group-hint">보고서(SR) PDF 1~3개</div>
          </div>
        </div>

        {/* 회사명 입력 + 업로드 버튼 */}
        <div className="upload-name-row">
          <div className="upload-name-input-wrap">
            <svg className="upload-name-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <input
              type="text"
              className="company-name-input"
              placeholder="회사이름 필수 입력"
              value={companyNames[groupKey]}
              onChange={(e) => handleCompanyNameChange(groupKey, e.target.value)}
            />
          </div>
          <label className={`inline-upload-btn inline-upload-btn--${color}`}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            파일 선택
            <input type="file" hidden multiple accept=".pdf" onChange={(e) => handleFileChange(e, groupKey)} />
          </label>
        </div>

        {/* 파일 목록 */}
        <div className="file-list-container">
          {files.length === 0 ? (
            <div className="empty-file-zone">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="18" x2="12" y2="12"/>
                <line x1="9" y1="15" x2="15" y2="15"/>
              </svg>
              <span>PDF 파일 1~3개 업로드</span>
            </div>
          ) : (
            files.map((file, index) => (
              <div className="file-item-box" key={index}>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <div className="file-info-text">
                  <div className="mock-label">{companyName}</div>
                  <div className="file-status-text" title={file.name}>{file.name}</div>
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

        {/* 파일 카운트 */}
        {files.length > 0 && (
          <div className="upload-file-count">
            <span className={`upload-file-count-dot upload-file-count-dot--${color}`}/>
            {files.length}개 파일 선택됨
          </div>
        )}
      </div>
    );
  };

  const displayData = dashboardData;

  return (
    <div id="bench-page" className="Bench-container">
      <header className="Bench-header">
        <div className="Bench-stepper-row">
          {steps.map((step, index) => (
            <Fragment key={step.id}>
              <div className={`step-box ${index === activeIndex ? "active" : ""}`} onClick={() => moveStep(index)}>
                <div className="step-icon-circle">{step.icon}</div>
                <div style={{ fontSize: "0.8rem", fontWeight: 800 }}>{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line" />}
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
                각 그룹별 최근 <strong>최대 3개년치</strong> 보고서를 등록하면 분석이 시작됩니다.
              </p>
              <div className="bench-tag-row">
                <span className="bench-tag bench-tag-green">PDF 자동 파싱</span>
                <span className="bench-tag bench-tag-blue">ESG 이슈 자동 식별</span>
                <span className="bench-tag bench-tag-purple">공시 Gap 분석</span>
                <span className="bench-tag bench-tag-orange">최대 3개년 비교</span>
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
            {renderUploadGroup("leader")}
            {renderUploadGroup("peer")}
            {renderUploadGroup("sub")}
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
          <div style={{ height: "60px", flexShrink: 0 }} />
        </div>
      </main>

      <div className={`dashboard-result-dashboard ${dashboardOpen ? "open " : ""}`} id="dashboard">
        <div className="dashboard-handle" onClick={() => setDashboardOpen(!dashboardOpen)}>
           <div className={`handle-pill ${showResult ? "complete" : ""}`}>
            {isAnalyzing ? "AI 분석 진행 중..." : showResult ? "분석 완료 - 결과 요약 확인 (클릭)" : "실시간 분석 대기 중"}
          </div>
        </div>
        <div
          className={`bench-robot-view-container dma-stage ${isAnalyzing ? "analyzing dma-stage--running" : ""} ${showResult ? "showing-result" : ""}`}
          style={{ '--dma-icon': `url(${benchIcon})`, '--dma-accent': '#6366f1' }}
        >
          <div id="particle-field" className="particle-field" ref={particleRef}></div>
          {!showResult && (
            <div className="dma-stage__blobs" aria-hidden="true">
              <div className="dma-stage__blob dma-stage__blob--1" />
              <div className="dma-stage__blob dma-stage__blob--2" />
              <div className="dma-stage__blob dma-stage__blob--3" />
              <div className="dma-stage__blob dma-stage__blob--4" />
              <div className="dma-stage__blob dma-stage__blob--5" />
              <div className="dma-stage__blob dma-stage__blob--6" />
              <div className="dma-stage__blob dma-stage__blob--7" />
              <div className="dma-stage__blob dma-stage__blob--8" />
              <div className="dma-stage__blob dma-stage__blob--9" />
              <div className="dma-stage__blob dma-stage__blob--10" />
              <div className="dma-stage__blob dma-stage__blob--11" />
              <div className="dma-stage__blob dma-stage__blob--12" />
            </div>
          )}

          {!showResult ? (
            <div className="dma-stage__content">
              <div className="dma-stage__robot">
                <img src={robot} className="dma-stage__img" alt="robot" />
              </div>
              <h3 className="dma-stage__title">
                {isAnalyzing ? "AI 분석 진행 중..." : "분석 준비가 완료되었습니다"}
              </h3>
              <p className="dma-stage__desc">
                {isAnalyzing
                  ? "벤치마킹 보고서를 분석하고 있습니다. 잠시 기다려 주세요."
                  : "파일을 업로드하고 벤치마킹 분석을 시작하세요."}
              </p>
              {isAnalyzing && (
                <div className="dma-stage__progress">
                  <div className="dma-stage__progress-bar">
                    <div className="dma-stage__progress-fill" style={{ width: `${progress}%` }}></div>
                  </div>
                  <div className="dma-stage__progress-pct">{progress}% 분석 중</div>
                </div>
              )}
            </div>
          ) : (
            <div className="result-layout" id="benchmarking-result">

              {/* 결과 배너 */}
              <div className="bench-result-banner">
                <div className="bench-result-banner-left">
                  <span className="bench-result-banner-badge">
                    <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                      <path d="M2.5 6l2.5 2.5 4.5-5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    AI 분석 완료
                  </span>
                  <div className="bench-result-banner-title">벤치마킹 이슈 도출 · Gap Analysis</div>
                  <p className="bench-result-banner-desc">
                    보고서(SR) 교차 파싱 결과 <strong>{displayData.stats.identifiedIssues}개</strong>의 핵심 이슈가 식별되었습니다.
                    자사의 누락(Gap) 요소를 보완하여 최적의 초안 요건을 빌드하세요.
                  </p>
                </div>
                <img src={robot} className="bench-result-banner-robot" alt="robot" />
              </div>

              {/* KPI 카드 */}
              <div className="result-stats-row">
                <div className="result-stat-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <line x1="10" y1="9" x2="8" y2="9" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">분석보고서</div>
                    <div className="stat-value-row">
                    <div className="stat-value">{displayData.stats.reports}개</div>
                    <div className="stat-sub">
                      리더 {displayData.stats.leaderCount} · 피어 {displayData.stats.peerCount} · 자사 {displayData.stats.ownCount}
                    </div>
                    </div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="8" y1="6" x2="21" y2="6" />
                      <line x1="8" y1="12" x2="21" y2="12" />
                      <line x1="8" y1="18" x2="21" y2="18" />
                      <circle cx="3" cy="6" r="1" fill="#64748b" stroke="none" />
                      <circle cx="3" cy="12" r="1" fill="#64748b" stroke="none" />
                      <circle cx="3" cy="18" r="1" fill="#64748b" stroke="none" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">식별 이슈</div>
                    <div className="stat-value">{displayData.stats.identifiedIssues}개</div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                      <circle cx="9" cy="7" r="4" />
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">공통 이슈</div>
                    <div className="stat-value">{displayData.stats.commonIssues}개</div>
                  </div>
                </div>

                <div className="result-stat-card">
                  <div className="stat-icon-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <circle cx="12" cy="12" r="6" />
                      <circle cx="12" cy="12" r="2" />
                    </svg>
                  </div>
                  <div>
                    <div className="stat-label">자사 Blind Spot</div>
                    <div className="stat-value">{displayData.stats.blindSpots}개</div>
                  </div>
                </div>
              </div>

              {/* 3-패널 */}
              <div className="result-panels-row">

                {/* 패널 1: Top 이슈 */}
                <div className="result-panel panel-accent-green">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-green" />
                      벤치마킹 Top 이슈 점수
                    </span>
                    <span className="panel-badge-count">{displayData.topIssues.length}건</span>
                  </div>
                  <div className="panel-body">
                    <table className="issue-table">
                      <thead>
                        <tr>
                          <th style={{ width: "36px" }}>순위</th>
                          <th>Sub Issue</th>
                          <th>Impact</th>
                          <th>Financial</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayData.topIssues.map((item) => (
                          <tr key={item.rank}>
                            <td><RankBadge rank={item.rank} /></td>
                            <td>{item.name}</td>
                            <td>{item.impact}</td>
                            <td>{item.financial}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 패널 2: 공통 선정 이슈 */}
                <div className="result-panel panel-accent-blue">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-blue" />
                      공통 선정 이슈
                    </span>
                    <span className="panel-badge-count">{displayData.commonIssues.length}건</span>
                  </div>
                  <div className="panel-body">
                    <table className="issue-table">
                      <thead>
                        <tr>
                          <th>Sub Issue</th>
                          <th><span className="col-badge col-green">리더</span></th>
                          <th><span className="col-badge col-blue">피어</span></th>
                          <th><span className="col-badge col-orange">자사</span></th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayData.commonIssues.map((item, index) => (
                          <tr key={index}>
                            <td>{item.name}</td>
                            <td>{item.leader && <span className="chk chk-green">✓</span>}</td>
                            <td>{item.peer && <span className="chk chk-blue">✓</span>}</td>
                            <td>{item.own && <span className="chk chk-orange">✓</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 패널 3: Blind Spot */}
                <div className="result-panel panel-accent-orange">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-orange" />
                      자사 Blind Spot
                    </span>
                    <span className="panel-badge-count">{displayData.blindSpots.length}건</span>
                  </div>
                  <div className="panel-body">
                    <ul className="blind-spot-list">
                      {displayData.blindSpots.map((item, index) => (
                        <li key={index} className="blind-spot-item">
                          <span className="blind-spot-num">{index + 1}</span>
                          <div>
                            <div className="blind-spot-title">{item.title}</div>
                            <p className="blind-spot-desc">{item.desc}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* 다음 단계 버튼 */}
              <div className="result-next-row">
                <button type="button" className="result-next-btn" onClick={() => navigate("/media")}>
                  다음 단계: 미디어 분석으로 이동
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
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
