import { useEffect, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import { useSelector, useDispatch } from "react-redux";
import "@styles/sr.css";
import "@styles/survey.css";

import robot from "@assets/images/robot/robot_servey_t.png";

import {
  showDefaultAlert,
  showConfirmAlert,
} from "@components/UI/ServiceAlert";

import { useAuth } from "@hooks/AuthContext";

import {
  fetchSurveyForm as fetchSurveyFormThunk,
  retrySurveyForm as retrySurveyFormThunk,
  importSurveyResponses as importSurveyResponsesThunk,
  recalculateSurveyScores as recalculateSurveyScoresThunk,
  fetchSurveyResponseStatus as fetchSurveyResponseStatusThunk,
  saveSurveyResponseTargets as saveSurveyResponseTargetsThunk,
  clearSurveyState,
} from "@stores/reportSlice";

/* ── 그룹 메타 ──────────────────────────────────── */
const GROUP_META = {
  employee: {
    label: "임직원",
    color: "#03A94D",
    bg: "#e8f8ef",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  management: {
    label: "경영진",
    color: "#3b82f6",
    bg: "#eff6ff",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  external: {
    label: "외부이해관계자",
    color: "#f97316",
    bg: "#fff7ed",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
};
const GROUP_KEYS = ["employee", "management", "external"];

const URL_LABEL = {
  employee:   (year) => `임직원 ESG ${year} 설문조사`,
  management: (year) => `경영진 ESG ${year} 설문조사`,
  external:   (year) => `외부이해관계자 용 ESG ${year} 설문조사`,
};

const Survey = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { selectedCompany } = useAuth();
  const currentRunId  = useSelector((state) => state.report.currentRunId);
  const currentYear   = useSelector((state) => state.report.currentYear);

  /* Redux state */
  const surveyForm       = useSelector((s) => s.report.survey.form);
  const surveyFormLoading= useSelector((s) => s.report.loading.surveyForm);
  const responseStatus   = useSelector((s) => s.report.survey.responseStatus);
  const surveyActionLoading = useSelector(
    (s) =>
      s.report.loading.surveyImport ||
      s.report.loading.surveyRecalculate ||
      s.report.loading.surveyRetry ||
      s.report.loading.surveyTargets
  );
  const responseStatusLoading = useSelector((s) => s.report.loading.surveyResponseStatus);
  const surveyErrorRaw = useSelector(
    (s) =>
      s.report.error.surveyImport ||
      s.report.error.surveyRecalculate ||
      s.report.error.surveyRetry ||
      null
  );
  const surveyError = surveyErrorRaw?.message ?? null;

  /* 목표 인원 / 대시보드 로컬 상태 */
  const [localTargets, setLocalTargets] = useState({ employee: 150, management: 20, external: 80 });
  const [targetsDirty, setTargetsDirty] = useState(false);
  const [recalcDone, setRecalcDone] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const activeIndex = 2;

  const steps = [
    {
      id: 1, title: "벤치마킹 분석", path: "/benchmk",
      icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7"/><line x1="15.5" y1="15.5" x2="21" y2="21"/><line x1="7" y1="13" x2="7" y2="11"/><line x1="10" y1="13" x2="10" y2="8.5"/><line x1="13" y1="13" x2="13" y2="7"/><line x1="6" y1="13" x2="14" y2="13"/></svg>,
    },
    {
      id: 2, title: "미디어 분석", path: "/media",
      icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/><polyline points="5,13 8,10 11,12 14,8 19,6"/></svg>,
    },
    {
      id: 3, title: "이해관계자 설문", path: "/survey",
      icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><polyline points="9,11 10.5,12.5 13,10"/><polyline points="9,16 10.5,17.5 13,15"/><line x1="13" y1="11" x2="16" y2="11"/><line x1="13" y1="16" x2="16" y2="16"/></svg>,
    },
    {
      id: 4, title: "전체 결과", path: "/result",
      icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="20" x2="21" y2="20"/><line x1="3" y1="4" x2="3" y2="20"/><rect x="5" y="13" width="3" height="7"/><rect x="10" y="10" width="3" height="10"/><rect x="15" y="8" width="3" height="12"/><circle cx="19" cy="4" r="3"/><polyline points="17.5,4 18.5,5 21,2.5"/></svg>,
    },
    {
      id: 5, title: "보고서 초안", path: "/draft",
      icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/></svg>,
    },
  ];

  /* ── Effects ───────────────────────────────────── */

  useEffect(() => {
    if (!currentRunId) {
      dispatch(clearSurveyState());
      setRecalcDone(false);
      return;
    }
    dispatch(fetchSurveyFormThunk({ runId: currentRunId }));
    dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
  }, [currentRunId, dispatch]);

  useEffect(() => {
    if (!responseStatus?.groups) return;
    setLocalTargets({
      employee:   responseStatus.groups.employee?.targetCount   ?? 150,
      management: responseStatus.groups.management?.targetCount ?? 20,
      external:   responseStatus.groups.external?.targetCount   ?? 80,
    });
    setTargetsDirty(false);
  }, [responseStatus]);

  /* ── Handlers ──────────────────────────────────── */

  const handleFetchSurveyForm = () => {
    if (!currentRunId) return;
    dispatch(fetchSurveyFormThunk({ runId: currentRunId }));
  };

  const handleRetrySurveyForm = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const ok = await showConfirmAlert("설문 URL 재생성", "설문 URL 생성을 다시 시도할까요?", "question");
    if (!ok) return;
    const res = await dispatch(retrySurveyFormThunk({ runId: currentRunId }));
    if (retrySurveyFormThunk.fulfilled.match(res)) {
      await showDefaultAlert("완료", "설문 URL 생성 상태를 갱신했습니다.", "success");
    } else {
      await showDefaultAlert("실패", "설문 URL 재시도에 실패했습니다.", "error");
    }
  };

  const handleRefreshStatus = () => {
    if (!currentRunId) return;
    dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
  };

  const handleSaveTargets = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const res = await dispatch(saveSurveyResponseTargetsThunk({ runId: currentRunId, targets: localTargets }));
    if (saveSurveyResponseTargetsThunk.fulfilled.match(res)) {
      setTargetsDirty(false);
      await showDefaultAlert("저장 완료", "목표 인원이 저장되었습니다.", "success");
    } else {
      await showDefaultAlert("저장 실패", "목표 인원 저장에 실패했습니다.", "error");
    }
  };

  const handleImport = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const ok = await showConfirmAlert("응답 가져오기", "Google Sheet의 최신 설문 응답을 DB로 가져올까요?", "question");
    if (!ok) return;
    const res = await dispatch(importSurveyResponsesThunk({ runId: currentRunId }));
    if (importSurveyResponsesThunk.fulfilled.match(res)) {
      const raw = res.payload?.data ?? res.payload;
      const empC  = raw?.respondentCounts?.employee   ?? 0;
      const mgmtC = raw?.respondentCounts?.management ?? 0;
      const extC  = raw?.respondentCounts?.external   ?? 0;
      console.debug("[Survey] import:", raw);
      await showDefaultAlert("응답 동기화 완료", `임직원 ${empC}명 / 경영진 ${mgmtC}명 / 외부 ${extC}명`, "success");
      dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
    } else {
      await showDefaultAlert("실패", "설문 응답 가져오기에 실패했습니다.", "error");
    }
  };

  const handleRecalculate = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const ok = await showConfirmAlert("응답 집계 반영", "설문 점수를 이중중대성 평가 점수에 반영할까요?", "question");
    if (!ok) return;
    setDashboardOpen(true);
    setIsAnalyzing(true);
    const res = await dispatch(recalculateSurveyScoresThunk({ runId: currentRunId }));
    setIsAnalyzing(false);
    if (recalculateSurveyScoresThunk.fulfilled.match(res)) {
      console.debug("[Survey] recalculate:", res.payload?.data ?? res.payload);
      setRecalcDone(true);
      dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
    } else {
      await showDefaultAlert("실패", "응답 집계 반영에 실패했습니다.", "error");
    }
  };

  /* ── Helpers ──────────────────────────────────── */

  const copyUrl = async (url) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        const ta = document.createElement("textarea");
        ta.value = url;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      showDefaultAlert("복사 완료", "클립보드 복사 완료", "success");
    } catch {
      showDefaultAlert("복사 실패", "오류 발생", "error");
    }
  };

  const openUrl = (url) => { if (url) window.open(url, "_blank", "noopener,noreferrer"); };
  const moveStep = (i) => { if (i !== activeIndex) navigate(steps[i].path); };
  const handleTargetChange = (group, value) => {
    const n = Math.max(0, Math.floor(Number(value)));
    if (!Number.isFinite(n)) return;
    setLocalTargets((prev) => ({ ...prev, [group]: n }));
    setTargetsDirty(true);
  };

  /* ── Derived ──────────────────────────────────── */
  const isReady = surveyForm?.surveyStatus === "READY";
  const isActionDisabled = !currentRunId || surveyActionLoading || !isReady;
  const groups = responseStatus?.groups ?? null;
  const totals = responseStatus?.totals ?? null;

  /* ── URL panel ────────────────────────────────── */
  const renderUrlArea = () => {
    if (surveyFormLoading) return <p className="survey-status-box">설문 URL 상태를 불러오는 중...</p>;
    if (!currentRunId)     return <p className="survey-status-box">분석 실행 후 설문 URL이 자동 생성됩니다.</p>;
    if (surveyForm?.surveyStatus === "RETRYABLE") {
      return (
        <div>
          <p className="survey-error-box">{surveyForm.errorMessage || "설문 URL 생성에 실패했습니다."}</p>
          <button className="survey-btn" style={{ marginBottom: 0 }} onClick={handleRetrySurveyForm} disabled={surveyActionLoading}>재시도</button>
        </div>
      );
    }
    if (surveyForm === null) {
      return (
        <div>
          <p className="survey-status-box">미디어 분석 완료 후 설문 URL이 자동 생성됩니다.</p>
          <button className="survey-btn" style={{ marginBottom: 0, marginTop: "8px" }} onClick={handleFetchSurveyForm} disabled={surveyFormLoading}>URL 생성 상태 재조회</button>
        </div>
      );
    }
    if (surveyForm.surveyStatus === "GENERATING") return <p className="survey-status-box">설문 URL 자동 생성 중입니다...</p>;

    const urlRows = [
      { key: "employee",   url: surveyForm.employeeFormUrl },
      { key: "management", url: surveyForm.managementFormUrl },
      { key: "external",   url: surveyForm.externalFormUrl },
    ];
    return (
      <div className="svurl-list">
        {urlRows.map(({ key, url }) => {
          const meta = GROUP_META[key];
          return (
            <div className="svurl-row" key={key}>
              <div className="svurl-row-left">
                <span className="svgroup-icon-sm" style={{ background: meta.bg, color: meta.color }}>{meta.icon}</span>
                <span className="svgroup-badge" style={{ color: meta.color, background: meta.bg }}>{meta.label}</span>
              </div>
              {isReady && url ? (
                <div className="svurl-row-right">
                  <span className="svurl-text" title={url}>{url}</span>
                  <button className="svurl-btn svurl-btn--dark" onClick={() => window.open(url, '_blank')}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    열기
                  </button>
                  <button className="svurl-btn svurl-btn--green" onClick={() => copyUrl(url)}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    복사
                  </button>
                </div>
              ) : (
                <span className="svurl-empty">URL 없음</span>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  /* ── Response rate panel ──────────────────────── */
  const renderResponseRate = () => {
    if (responseStatusLoading) return <p className="survey-status-box" style={{ marginTop: "12px" }}>응답 현황 불러오는 중...</p>;
    if (!currentRunId || !groups) return <p className="survey-status-box" style={{ marginTop: "12px" }}>runId를 선택하면 응답 현황이 표시됩니다.</p>;

    return (
      <div className="svrate-list">
        {GROUP_KEYS.map((key) => {
          const grp  = groups[key];
          if (!grp) return null;
          const meta = GROUP_META[key];
          const pct  = grp.targetCount > 0 ? Math.round(grp.responseRate * 1000) / 10 : 0;
          const pctW = Math.min(100, Math.round(pct));
          return (
            <div className="svrate-card" key={key}>
              <div className="svrate-card-top">
                <div className="svrate-card-left">
                  <span className="svgroup-icon-sm" style={{ background: meta.bg, color: meta.color }}>{meta.icon}</span>
                  <span className="svrate-group-name">{meta.label}</span>
                </div>
                <div className="svrate-card-count">
                  <strong style={{ color: "#1e293b", fontSize: "1.15rem" }}>{grp.responseCount}</strong>
                  <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}> / {grp.targetCount} 명</span>
                </div>
              </div>
              <div className="svrate-bar-row">
                <div className="svrate-bar-bg">
                  <div className="svrate-bar-fill" style={{ width: `${pctW}%`, background: meta.color }} />
                </div>
                <span className="svrate-pct" style={{ color: meta.color }}>{pct.toFixed(1)}%</span>
              </div>
            </div>
          );
        })}

        {totals && (
          <div className="svrate-total-card">
            <div className="svrate-total-stat">
              <div className="svrate-total-icon" style={{ background: "#e8f8ef" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <div>
                <div className="svrate-total-label">총 응답</div>
                <div className="svrate-total-value">{totals.responseCount} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>명</span></div>
              </div>
            </div>
            <div className="svrate-total-divider" />
            <div className="svrate-total-stat">
              <div className="svrate-total-icon" style={{ background: "#e8f8ef" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
              </div>
              <div>
                <div className="svrate-total-label">응답률</div>
                <div className="svrate-total-value">{(totals.responseRate * 100).toFixed(1)}<span style={{ fontSize: "0.8rem", fontWeight: 500 }}>%</span></div>
              </div>
            </div>
          </div>
        )}

        {recalcDone && (
          <div className="survey-recalc-done" style={{ marginTop: "10px" }}>
            이중 중대성 평가 점수에 설문 응답이 반영되었습니다.
          </div>
        )}
      </div>
    );
  };

  /* ── Render ────────────────────────────────────── */
  return (
    <div className="survey-container">
      {/* Stepper */}
      <header className="survey-header">
        <div className="survey-stepper-row">
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

      <main className="main-content">
        <div className="survey-input-card">

          {/* 상단 고정 영역 */}
          <div className="sv-top-section">
            {/* 페이지 헤더 */}
            <div className="survey-page-header">
              <div className="survey-page-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>
                  <polyline points="9,11 10.5,12.5 13,10"/><polyline points="9,16 10.5,17.5 13,15"/>
                  <line x1="13" y1="11" x2="16" y2="11"/><line x1="13" y1="16" x2="16" y2="16"/>
                </svg>
              </div>
              <div className="survey-page-text">
                <h2 className="survey-page-title">이해관계자 설문</h2>
                <p className="survey-page-desc">
                  임직원·경영진·외부이해관계자를 대상으로 ESG 이슈의 중요도를 직접 평가받습니다.
                  설문 URL을 배포하고 응답을 집계하여 <strong>이중 중대성 평가</strong>에 반영합니다.
                </p>
                <div className="survey-tag-row">
                  <span className="survey-tag survey-tag-green">설문 URL 자동 생성</span>
                  <span className="survey-tag survey-tag-blue">3그룹 분류</span>
                  <span className="survey-tag survey-tag-purple">AI 집계 분석</span>
                  <span className="survey-tag survey-tag-orange">이중 중대성 반영</span>
                </div>
              </div>
            </div>

            {/* 그룹 카드 */}
            <div className="survey-group-grid">
              <div className="survey-group-card survey-group-card--green">
                <div className="survey-group-card-head">
                  <span className="survey-group-badge survey-group-badge--green">임직원</span>
                  <span className="survey-group-label survey-group-label--green">Employee</span>
                </div>
                <p className="survey-group-desc">기업 활동이 환경·사회에 미치는 영향 관점에서 ESG 이슈의 중요도를 평가합니다.</p>
              </div>
              <div className="survey-group-card survey-group-card--blue">
                <div className="survey-group-card-head">
                  <span className="survey-group-badge survey-group-badge--blue">경영진</span>
                  <span className="survey-group-label survey-group-label--blue">Management</span>
                </div>
                <p className="survey-group-desc">ESG 이슈가 기업의 재무성과, 사업 지속가능성 및 경영 전략에 미치는 영향을 고려하여 중요도를 평가합니다.</p>
              </div>
              <div className="survey-group-card survey-group-card--orange">
                <div className="survey-group-card-head">
                  <span className="survey-group-badge survey-group-badge--orange">외부</span>
                  <span className="survey-group-label survey-group-label--orange">External Stakeholder</span>
                </div>
                <p className="survey-group-desc">고객, 투자자, 협력사, 지역사회 등 이해관계자의 관점에서 ESG 이슈의 중요도를 평가합니다.</p>
              </div>
            </div>

            {/* 에러 */}
            {surveyError && <div className="survey-error-box" style={{ marginTop: "10px" }}>{surveyError}</div>}
          </div>

          {/* 2패널 그리드 */}
          <div className="survey-section-grid">

            {/* ── 좌: URL & 목표 인원 ── */}
            <div className="sv-panel-card">
              {/* 패널 헤더 */}
              <div className="sv-panel-header">
                <div className="sv-panel-header-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                  </svg>
                </div>
                <div>
                  <div className="sv-panel-title">설문 URL & 발송 관리</div>
                  <div className="sv-panel-subtitle">대상 그룹별 설문 URL을 관리하고, 발송 목표 인원을 설정합니다.</div>
                </div>
              </div>

              {/* URL 영역 */}
              <div className="sv-panel-body">
                {renderUrlArea()}

                {/* 목표 인원 */}
                <div className="sv-target-section">
                  <div className="sv-target-label">발송 목표 인원</div>
                  <div className="sv-target-row">
                    {GROUP_KEYS.map((key) => {
                      const meta = GROUP_META[key];
                      return (
                        <div className="sv-target-item" key={key}>
                          <span className="svgroup-icon-sm" style={{ background: meta.bg, color: meta.color }}>{meta.icon}</span>
                          <span className="sv-target-item-label">{meta.label}</span>
                          <input
                            type="number"
                            min="0"
                            className="sv-target-input"
                            value={localTargets[key]}
                            onChange={(e) => handleTargetChange(key, e.target.value)}
                          />
                          <span className="sv-target-unit">명</span>
                        </div>
                      );
                    })}
                  </div>
                  {currentRunId && (
                    <button
                      className={`sv-save-btn${targetsDirty ? "" : " sv-save-btn--disabled"}`}
                      onClick={handleSaveTargets}
                      disabled={!targetsDirty || surveyActionLoading}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                        <polyline points="17,21 17,13 7,13 7,21"/>
                        <polyline points="7,3 7,8 15,8"/>
                      </svg>
                      {surveyActionLoading ? "저장 중..." : "목표 인원 저장"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* ── 우: 응답 현황 ── */}
            <div className="sv-panel-card">
              {/* 패널 헤더 */}
              <div className="sv-panel-header">
                <div className="sv-panel-header-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10"/>
                    <line x1="12" y1="20" x2="12" y2="4"/>
                    <line x1="6" y1="20" x2="6" y2="14"/>
                  </svg>
                </div>
                <div>
                  <div className="sv-panel-title">응답 현황</div>
                </div>
              </div>

              {/* 액션 버튼 */}
              <div className="sv-panel-body">
                <div className="sv-action-row">
                  <button className="sv-action-btn sv-action-btn--outline" onClick={handleRefreshStatus} disabled={!currentRunId || responseStatusLoading}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                    </svg>
                    {responseStatusLoading ? "갱신 중..." : "응답 현황 갱신"}
                  </button>
                  <button className="sv-action-btn sv-action-btn--outline" onClick={handleImport} disabled={isActionDisabled} title={!isReady ? "READY 상태 설문 폼이 필요합니다." : ""}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    {surveyActionLoading ? "처리 중..." : "응답 가져오기"}
                  </button>
                  <button className="sv-action-btn sv-action-btn--green" onClick={handleRecalculate} disabled={isActionDisabled} title={!isReady ? "READY 상태 설문 폼이 필요합니다." : ""}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/>
                      <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    응답 집계 반영
                  </button>
                </div>

                {renderResponseRate()}
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ── 하단 슬라이드업 결과 대시보드 ── */}
      <div className={`survey-result-dashboard ${dashboardOpen ? "open" : ""}`}>
        {/* Handle */}
        <div className="dashboard-handle" onClick={() => setDashboardOpen((o) => !o)}>
          <div className={`handle-pill${isAnalyzing ? " handle-pill--analyzing" : recalcDone ? " handle-pill--done" : ""}`}>
            {isAnalyzing
              ? "AI 분석 진행 중..."
              : recalcDone
                ? "분석 완료 — 결과 요약 확인"
                : "실시간 분석 대기 중"}
          </div>
        </div>

        {/* Body */}
        <div className="sv-dashboard-body">
          {isAnalyzing ? (
            /* ── 분석 진행 중 ── */
            <div className="sv-dashboard-analyzing">
              <div className="sv-dashboard-robot">
                <img src={robot} alt="robot" className="sv-robot-img sv-robot-img--bounce" />
              </div>
              <h3 className="sv-dashboard-state-title">이중 중대성 매트릭스 분석 중...</h3>
              <p className="sv-dashboard-state-desc">AI 기반 알고리즘이 설문 응답을 이중 중대성 평가 점수에 반영하고 있습니다.</p>
              <div className="sv-analyzing-bar">
                <div className="sv-analyzing-bar-fill" />
              </div>
            </div>
          ) : recalcDone && groups ? (
            /* ── 분석 완료 — KPI + 결과 ── */
            <>
              <div className="sv-dashboard-complete-banner">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                이중 중대성 평가 점수에 설문 응답이 반영되었습니다. <strong>전체 결과</strong> 페이지에서 상세 결과를 확인하세요.
              </div>

              {/* KPI 4카드 */}
              <div className="survey-kpi-grid" style={{ marginTop: "14px" }}>
                {GROUP_KEYS.map((key) => {
                  const grp  = groups[key];
                  const meta = GROUP_META[key];
                  const pct  = grp?.targetCount > 0 ? Math.round(grp.responseRate * 1000) / 10 : 0;
                  return (
                    <div className="survey-kpi-card" key={key}>
                      <div className="stat-label" style={{ color: meta.color, display: "flex", alignItems: "center", gap: "6px" }}>
                        {meta.icon}{meta.label} 응답
                      </div>
                      <div className="stat-value">
                        {grp?.responseCount ?? 0}<span style={{ fontSize: "0.85rem", fontWeight: 500 }}>명</span>
                        <span className="stat-target">(목표 {grp?.targetCount ?? 0}명)</span>
                      </div>
                      <div className="kpi-bar-wrap">
                        <div className="kpi-bar-fill" style={{ width: `${Math.min(100, pct)}%`, background: meta.color }} />
                        <span className="kpi-bar-pct" style={{ color: meta.color }}>{pct.toFixed(1)}%</span>
                      </div>
                    </div>
                  );
                })}
                {totals && (
                  <div className="survey-kpi-card">
                    <div className="stat-label">전체 응답률</div>
                    <div className="stat-value">
                      {(totals.responseRate * 100).toFixed(1)}<span style={{ fontSize: "0.85rem", fontWeight: 500 }}>%</span>
                      <span className="stat-target">({totals.responseCount}/{totals.targetCount}명)</span>
                    </div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${Math.min(100, totals.responseRate * 100)}%` }} />
                      <span className="kpi-bar-pct">{(totals.responseRate * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                )}
              </div>

              {/* 결과 2패널 */}
              <div className="survey-panels" style={{ marginTop: "16px" }}>

                {/* Sub-Issue 점수 테이블 (TODO: 전체 결과 API 연동 후 채울 것) */}
                <div className="survey-panel">
                  <div className="panel-header-row">
                    <div className="panel-title">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" style={{ verticalAlign: "middle", marginRight: "4px" }}>
                        <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
                      </svg>
                      설문 Top 이슈 점수
                    </div>
                  </div>
                  <div style={{ overflowX: "auto" }}>
                    <table className="survey-complex-table">
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
                        {/* TODO: 전체 결과 페이지 API 연동 후 실 데이터로 교체 */}
                        <tr>
                          <td colSpan="10" style={{ textAlign: "center", color: "#94a3b8", padding: "20px", fontSize: "0.82rem" }}>
                            전체 결과 페이지에서 Sub-Issue별 상세 점수를 확인하세요.
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 이해관계자 분석 패널 */}
                <div className="survey-panel">
                  <div className="panel-header-row">
                    <div className="panel-title">이해관계자 분석</div>
                  </div>
                  <div className="stakeholder-group-list">
                    {GROUP_KEYS.map((key) => {
                      const grp  = groups[key];
                      const meta = GROUP_META[key];
                      const pct  = grp?.targetCount > 0 ? Math.round(grp.responseRate * 1000) / 10 : 0;
                      return (
                        <div className="stakeholder-item" key={key}>
                          <div className="stakeholder-header">
                            <span className="svgroup-icon-sm" style={{ background: meta.bg, color: meta.color, width: 36, height: 36, borderRadius: 10 }}>
                              {meta.icon}
                            </span>
                            <div>
                              <span className="stakeholder-name">{meta.label}</span>
                              <span className="stakeholder-topics">
                                응답 {grp?.responseCount ?? 0}명 / 목표 {grp?.targetCount ?? 0}명 ({pct.toFixed(1)}%)
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            </>
          ) : (
            /* ── 대기 중 — 로봇 + 안내 ── */
            <div className="sv-dashboard-analyzing">
              <div className="sv-dashboard-robot">
                <img src={robot} alt="robot" className="sv-robot-img sv-robot-img--idle" />
              </div>
              <h3 className="sv-dashboard-state-title">분석 미실행 상태</h3>
              <p className="sv-dashboard-state-desc">응답 가져오기 후 <strong>응답 집계 반영</strong> 버튼을 눌러 설문 결과를 분석해주세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Survey;
