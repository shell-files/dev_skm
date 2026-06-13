import { useRef, useState, Fragment, useEffect } from "react";
import { useNavigate } from "react-router";
import { useSelector } from "react-redux";
import "@styles/benchmarking.css";
import robot from "@assets/images/robot/robot_repoting_transparent.png";
import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

import { GET, POST_FORM, PUT } from "@utils/Network";

const USE_DUMMY =
  import.meta.env.DEV &&
  import.meta.env.VITE_BENCHMARK_DUMMY === "true";

const BENCHMARK_GROUP_CONFIG = {
  leader: { fileType: "Leader", label: "리더" },
  peer:   { fileType: "Peer",   label: "피어" },
  sub:    { fileType: "Own",    label: "자사" },
};

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

const DUMMY_RESULT_DASHBOARD = {
  stats: {
    reports: 24,
    leaderCount: 8,
    peerCount: 8,
    ownCount: 8,
    identifiedIssues: 10,
    commonIssues: 19,
    blindSpots: 9,
  },
  topIssues: [
    { rank: 1, name: "기후변화·온실가스", impact: 9.2, financial: 8.7 },
    { rank: 2, name: "수자원·폐수 관리", impact: 8.6, financial: 7.9 },
    { rank: 3, name: "폐기물·자원순환", impact: 8.1, financial: 7.6 },
    { rank: 4, name: "친환경 제품·Eco-Design", impact: 7.8, financial: 7.3 },
    { rank: 5, name: "공급망 ESG 관리", impact: 7.4, financial: 6.8 },
  ],
  commonIssues: [
    { name: "기후변화·온실가스", leader: true, peer: true, own: true },
    { name: "폐기물·자원순환", leader: true, peer: true, own: true },
    { name: "제품안전·품질", leader: true, peer: true, own: true },
    { name: "공급망 ESG 관리", leader: true, peer: true, own: true },
    { name: "공급망 ESG 관리", leader: true, peer: true, own: true },
  ],
  blindSpots: [
    { title: "생물다양성 영향 관리", desc: "생물다양성 리스크·영향 평가 및 관리 체계가 보고서에서 상대적으로 낮게 다뤄지고 있습니다." },
    { title: "인권 실사 및 관리", desc: "인권 실사 프로세스 및 고충처리 체계에 대한 정보가 상대적으로 부족합니다." },
    { title: "ESG 데이터 관리 체계", desc: "ESG 데이터 수집·관리·검증 체계의 고도화 및 거버넌스 정보가 미흡합니다." },
  ],
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
  const currentRunId = useSelector((state) => state.report.currentRunId);

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

  const [rawRows, setRawRows] = useState([]);
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
    const res = await GET(`/materiality/workflow-status/${runId}/BENCHMARK`);
    return res && !res.error ? res : null;
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

  const uploadBenchmarkGroup = async (groupKey) => {
    const group = BENCHMARK_GROUP_CONFIG[groupKey];
    const files = fileStorage[groupKey] || [];

    if (files.length !== 3) {
      throw new Error(`${group.label} 보고서 PDF 3개를 등록해주세요.`);
    }

    const companyName = String(companyNames[groupKey] || "").trim();
    if (!companyName) {
      throw new Error(`${group.label} 기업명을 입력해주세요.`);
    }

    const formData = new FormData();
    files.forEach((file) => { formData.append("file", file); });
    formData.append("fileType", group.fileType);
    formData.append("companyName", companyName);
    formData.append("page", "SR");

    const response = await POST_FORM("/benchmk", formData);
    if (!response || response.status === false) {
      throw new Error(response?.message || `${group.label} 업로드에 실패했습니다.`);
    }

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

    if (USE_DUMMY) {
      setProgress(100);
      setIsAnalyzing(false);
      setRawRows(DUMMY_DB_RESULTS);
      setDashboardData(DUMMY_RESULT_DASHBOARD);
      setShowResult(true);
      return;
    }

    try {
      setProgress(5);

      const uploadedFileNames = [];
      for (const groupKey of ["leader", "peer", "sub"]) {
        const storedNames = await uploadBenchmarkGroup(groupKey);
        uploadedFileNames.push(...storedNames);
      }

      setProgress(15);

      const analyzePromise = PUT("/benchmk", {
        file: uploadedFileNames,
        page: "SR",
        esgMaterialityRunId: runId,
        sourceStep: "benchmark",
      });

      startBenchmarkPolling(runId);

      const analyzeResponse = await analyzePromise;

      if (benchmarkWorkflowErrorRef.current) {
        throw new Error(benchmarkWorkflowErrorRef.current);
      }

      if (!analyzeResponse || analyzeResponse.status === false) {
        throw new Error(analyzeResponse?.message || "벤치마킹 분석에 실패했습니다.");
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

      const resultResponse = await GET(`/materiality/benchmark/${runId}`);

      if (!resultResponse || resultResponse.status === false) {
        throw new Error(resultResponse?.message || "벤치마킹 결과 조회에 실패했습니다.");
      }

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

  const processedIssues = getGroupedIssues();
  const displayData = dashboardData ?? DUMMY_RESULT_DASHBOARD;

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
        <div className="Bench-input-card" style={{ marginBottom: "50px" }}>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 850, marginBottom: "6px" }}>벤치마킹 분석</h2>
          <p style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: "4px" }}>
            산업군 리더 기업들의 공시 지표를 수집하고 우리 기업과의 격차 분석을 시작합니다.
          </p>

          <div className="Bench-upload-section-grid">
            {renderUploadGroup("leader", "리더", "회사이름 필수 입력")}
            {renderUploadGroup("peer", "피어", "회사이름 필수 입력")}
            {renderUploadGroup("sub", "자사", "회사이름 필수 입력")}
          </div>

          <button className="Bench-btn" id="bench-btn" onClick={runAnalysis}>실시간 AI 분석 시작</button>
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
                  보고서(SR) 교차 파싱 결과 <strong>{processedIssues.length}개</strong>의 핵심 이슈가 식별되었습니다. 자사의 누락(Gap) 요소를 보완하여 최적의 초안 요건을 빌드하세요.
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Benchmarking;
