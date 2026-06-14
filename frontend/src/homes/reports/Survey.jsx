import { useEffect, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import { useSelector, useDispatch } from "react-redux";
import "@styles/sr.css";
import "@styles/survey.css";

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

const Survey = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { selectedCompany } = useAuth();
  const currentRunId = useSelector((state) => state.report.currentRunId);

  /* Redux state */
  const surveyForm = useSelector((s) => s.report.survey.form);
  const surveyFormLoading = useSelector((s) => s.report.loading.surveyForm);
  const responseStatus = useSelector((s) => s.report.survey.responseStatus);
  const recalculateResult = useSelector((s) => s.report.survey.recalculateResult);

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

  /* Local state — target inputs (editable form values) */
  const [localTargets, setLocalTargets] = useState({ employee: 150, management: 20, external: 80 });
  const [targetsDirty, setTargetsDirty] = useState(false);
  const [recalcDone, setRecalcDone] = useState(false);

  const activeIndex = 2;

  const steps = [
    {
      id: 1,
      title: "벤치마킹 분석",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="10" cy="10" r="7" /><line x1="15.5" y1="15.5" x2="21" y2="21" />
          <line x1="7" y1="13" x2="7" y2="11" /><line x1="10" y1="13" x2="10" y2="8.5" />
          <line x1="13" y1="13" x2="13" y2="7" /><line x1="6" y1="13" x2="14" y2="13" />
        </svg>
      ),
      path: "/benchmk",
    },
    {
      id: 2,
      title: "미디어 분석",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" /><polyline points="5,13 8,10 11,12 14,8 19,6" />
        </svg>
      ),
      path: "/media",
    },
    {
      id: 3,
      title: "이해관계자 설문",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          <rect x="8" y="2" width="8" height="4" rx="1" />
          <polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" />
          <line x1="13" y1="11" x2="16" y2="11" /><line x1="13" y1="16" x2="16" y2="16" />
        </svg>
      ),
      path: "/survey",
    },
    {
      id: 4,
      title: "전체 결과",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="20" x2="21" y2="20" /><line x1="3" y1="4" x2="3" y2="20" />
          <rect x="5" y="13" width="3" height="7" /><rect x="10" y="10" width="3" height="10" />
          <rect x="15" y="8" width="3" height="12" /><circle cx="19" cy="4" r="3" />
          <polyline points="17.5,4 18.5,5 21,2.5" />
        </svg>
      ),
      path: "/result",
    },
    {
      id: 5,
      title: "보고서 초안",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
        </svg>
      ),
      path: "/draft",
    },
  ];

  /* =========================
     EFFECTS
  ========================= */

  useEffect(() => {
    if (!currentRunId) {
      dispatch(clearSurveyState());
      setRecalcDone(false);
      return;
    }
    dispatch(fetchSurveyFormThunk({ runId: currentRunId }));
    dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
  }, [currentRunId, dispatch]);

  // Sync local targets from server when responseStatus loads
  useEffect(() => {
    if (!responseStatus?.groups) return;
    setLocalTargets({
      employee: responseStatus.groups.employee?.targetCount ?? 150,
      management: responseStatus.groups.management?.targetCount ?? 20,
      external: responseStatus.groups.external?.targetCount ?? 80,
    });
    setTargetsDirty(false);
  }, [responseStatus]);

  /* =========================
     ACTION HANDLERS
  ========================= */

  const handleFetchSurveyForm = () => {
    if (!currentRunId) return;
    dispatch(fetchSurveyFormThunk({ runId: currentRunId }));
  };

  const handleRetrySurveyForm = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const confirmed = await showConfirmAlert("설문 URL 재생성", "설문 URL 생성을 다시 시도할까요?", "question");
    if (!confirmed) return;
    const result = await dispatch(retrySurveyFormThunk({ runId: currentRunId }));
    if (retrySurveyFormThunk.fulfilled.match(result)) {
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
    const result = await dispatch(
      saveSurveyResponseTargetsThunk({ runId: currentRunId, targets: localTargets })
    );
    if (saveSurveyResponseTargetsThunk.fulfilled.match(result)) {
      setTargetsDirty(false);
      await showDefaultAlert("저장 완료", "목표 인원이 저장되었습니다.", "success");
    } else {
      await showDefaultAlert("저장 실패", "목표 인원 저장에 실패했습니다.", "error");
    }
  };

  const handleImportSurveyResponses = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const confirmed = await showConfirmAlert(
      "응답 가져오기",
      "Google Sheet의 최신 설문 응답을 DB로 가져올까요?",
      "question"
    );
    if (!confirmed) return;
    const result = await dispatch(importSurveyResponsesThunk({ runId: currentRunId }));
    if (importSurveyResponsesThunk.fulfilled.match(result)) {
      const raw = result.payload?.data ?? result.payload;
      const empC = raw?.respondentCounts?.employee ?? 0;
      const mgmtC = raw?.respondentCounts?.management ?? 0;
      const extC = raw?.respondentCounts?.external ?? 0;
      console.debug("[Survey] import result:", raw);
      await showDefaultAlert(
        "응답 동기화 완료",
        `임직원 ${empC}명 / 경영진 ${mgmtC}명 / 외부 ${extC}명`,
        "success"
      );
      dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
    } else {
      await showDefaultAlert("실패", "설문 응답 가져오기에 실패했습니다.", "error");
    }
  };

  const handleRecalculate = async () => {
    if (!currentRunId || surveyActionLoading) return;
    const confirmed = await showConfirmAlert(
      "응답 집계 반영",
      "설문 점수를 이중중대성 평가 점수에 반영할까요?",
      "question"
    );
    if (!confirmed) return;
    const result = await dispatch(recalculateSurveyScoresThunk({ runId: currentRunId }));
    if (recalculateSurveyScoresThunk.fulfilled.match(result)) {
      console.debug("[Survey] recalculate result:", result.payload?.data ?? result.payload);
      setRecalcDone(true);
      await showDefaultAlert(
        "반영 완료",
        "이중 중대성 평가 점수에 설문 응답이 반영되었습니다.",
        "success"
      );
      dispatch(fetchSurveyResponseStatusThunk({ runId: currentRunId }));
    } else {
      await showDefaultAlert("실패", "응답 집계 반영에 실패했습니다.", "error");
    }
  };

  /* =========================
     HELPERS
  ========================= */

  const copyUrl = async (url) => {
    try {
      if (!url) throw new Error("empty url");
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

  const openUrl = (url) => {
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  };

  const moveStep = (index) => {
    if (index === activeIndex) return;
    navigate(steps[index].path);
  };

  const handleTargetChange = (group, value) => {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) return;
    setLocalTargets((prev) => ({ ...prev, [group]: Math.floor(n) }));
    setTargetsDirty(true);
  };

  const rateColor = (rate) => {
    if (rate >= 0.7) return "#22c55e";
    if (rate >= 0.3) return "#f59e0b";
    return "#ef4444";
  };

  /* =========================
     DERIVED
  ========================= */

  const isReady = surveyForm?.surveyStatus === "READY";
  const isActionDisabled = !currentRunId || surveyActionLoading || !isReady;

  const groups = responseStatus?.groups ?? null;
  const totals = responseStatus?.totals ?? null;

  /* =========================
     URL AREA
  ========================= */

  const renderUrlArea = () => {
    if (surveyFormLoading) {
      return <p className="survey-status-box">설문 URL 상태를 불러오는 중...</p>;
    }
    if (!currentRunId) {
      return <p className="survey-status-box">분석 실행 후 설문 URL이 자동 생성됩니다.</p>;
    }
    if (surveyForm?.surveyStatus === "RETRYABLE") {
      return (
        <div>
          <p className="survey-error-box">{surveyForm.errorMessage || "설문 URL 생성에 실패했습니다."}</p>
          <button className="survey-btn" style={{ marginBottom: 0 }} onClick={handleRetrySurveyForm} disabled={surveyActionLoading}>
            재시도
          </button>
        </div>
      );
    }
    if (surveyForm === null) {
      return (
        <div>
          <p className="survey-status-box">미디어 분석 완료 후 설문 URL이 자동 생성됩니다.</p>
          <button className="survey-btn" style={{ marginBottom: 0, marginTop: "8px" }} onClick={handleFetchSurveyForm} disabled={surveyFormLoading}>
            URL 생성 상태 재조회
          </button>
        </div>
      );
    }
    if (surveyForm.surveyStatus === "GENERATING") {
      return <p className="survey-status-box">설문 URL 자동 생성 중입니다...</p>;
    }
    const urlRows = [
      { label: "임직원", url: surveyForm.employeeFormUrl },
      { label: "경영진", url: surveyForm.managementFormUrl },
      { label: "외부이해관계자", url: surveyForm.externalFormUrl },
    ];
    return (
      <div className="survey-group-list">
        {urlRows.map(({ label, url }) => (
          <div className="survey-row-box" key={label}>
            <label>{label}</label>
            {isReady && url ? (
              <div className="url-input-line">
                <span style={{ flex: 1, fontSize: "0.78rem", color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {url}
                </span>
                <div className="survey-url-actions">
                  <button className="btn-url-copy" style={{ background: "#334155", marginBottom: 0 }} onClick={() => openUrl(url)}>열기</button>
                  <button className="btn-url-copy" style={{ marginBottom: 0 }} onClick={() => copyUrl(url)}>복사</button>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", margin: 0 }}>URL 없음</p>
            )}
          </div>
        ))}
      </div>
    );
  };

  /* =========================
     RESPONSE RATE PANEL
  ========================= */

  const GROUP_LABELS = { employee: "임직원", management: "경영진", external: "외부이해관계자" };

  const renderResponseRatePanel = () => {
    if (responseStatusLoading) {
      return <p className="survey-status-box" style={{ marginTop: "12px" }}>응답 현황 불러오는 중...</p>;
    }
    if (!currentRunId || !groups) {
      return <p className="survey-status-box" style={{ marginTop: "12px" }}>runId를 선택하면 응답 현황이 표시됩니다.</p>;
    }

    const groupKeys = ["employee", "management", "external"];

    return (
      <div style={{ marginTop: "12px" }}>
        {groupKeys.map((g) => {
          const grp = groups[g];
          if (!grp) return null;
          const pct = Math.round(grp.responseRate * 100);
          const color = rateColor(grp.responseRate);
          return (
            <div className="survey-rate-card" key={g}>
              <div className="survey-rate-header">
                <span className="survey-rate-label">{GROUP_LABELS[g]} 응답자</span>
                <span className="survey-rate-count">
                  <strong style={{ color }}>{grp.responseCount}</strong>
                  <span style={{ color: "#94a3b8" }}> / {grp.targetCount}명</span>
                  <span className="survey-rate-pct" style={{ color }}>{pct}%</span>
                </span>
              </div>
              <div className="survey-rate-bar-bg">
                <div
                  className="survey-rate-bar-fill"
                  style={{ width: `${Math.min(100, pct)}%`, background: color }}
                />
              </div>
            </div>
          );
        })}

        {totals && (
          <div className="survey-rate-card survey-rate-card--total">
            <div className="survey-rate-header">
              <span className="survey-rate-label">총 응답률</span>
              <span className="survey-rate-count">
                <strong style={{ color: rateColor(totals.responseRate) }}>{totals.responseCount}</strong>
                <span style={{ color: "#94a3b8" }}> / {totals.targetCount}명</span>
                <span className="survey-rate-pct" style={{ color: rateColor(totals.responseRate) }}>
                  {Math.round(totals.responseRate * 100)}%
                </span>
              </span>
            </div>
            <div className="survey-rate-bar-bg">
              <div
                className="survey-rate-bar-fill"
                style={{ width: `${Math.min(100, Math.round(totals.responseRate * 100))}%`, background: rateColor(totals.responseRate) }}
              />
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

  /* =========================
     RENDER
  ========================= */

  return (
    <div className="survey-container">
      {/* Stepper */}
      <header className="survey-header">
        <div className="survey-stepper-row">
          {steps.map((step, index) => (
            <Fragment key={step.id}>
              <div
                className={`step-box ${index === activeIndex ? "active" : ""}`}
                onClick={() => moveStep(index)}
              >
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

          {/* 페이지 헤더 */}
          <div className="survey-page-header">
            <div className="survey-page-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
                <rect x="8" y="2" width="8" height="4" rx="1" />
                <polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" />
                <line x1="13" y1="11" x2="16" y2="11" /><line x1="13" y1="16" x2="16" y2="16" />
              </svg>
            </div>
            <div className="survey-page-text">
              <h2 className="survey-page-title">이해관계자 설문</h2>
              <p className="survey-page-desc">
                임직원·경영진·외부이해관계자를 대상으로 ESG 이슈의 중요도를 직접 평가받습니다.
                설문 URL을 배포하고 응답을 집계하여{" "}
                <strong>이중 중대성 평가</strong>에 반영합니다.
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
              <p className="survey-group-desc">
                기업 활동이 환경·사회에 미치는 영향 관점에서 ESG 이슈의 중요도를 평가합니다.
                업무 수행 과정에서 경험한 실제 영향과 현장의 의견을 바탕으로 응답합니다.
              </p>
            </div>
            <div className="survey-group-card survey-group-card--blue">
              <div className="survey-group-card-head">
                <span className="survey-group-badge survey-group-badge--blue">경영진</span>
                <span className="survey-group-label survey-group-label--blue">Management</span>
              </div>
              <p className="survey-group-desc">
                ESG 이슈가 기업의 재무성과, 사업 지속가능성 및 경영 전략에 미치는 영향을
                고려하여 중요도를 평가합니다. 리스크와 기회 요인을 종합적으로 검토해 응답합니다.
              </p>
            </div>
            <div className="survey-group-card survey-group-card--orange">
              <div className="survey-group-card-head">
                <span className="survey-group-badge survey-group-badge--orange">외부</span>
                <span className="survey-group-label survey-group-label--orange">External Stakeholder</span>
              </div>
              <p className="survey-group-desc">
                고객, 투자자, 협력사, 지역사회 등 이해관계자의 관점에서 ESG 이슈의 중요도를
                평가합니다. 기업 활동이 사회와 환경에 미치는 영향 및 기대 수준을 반영하여 응답합니다.
              </p>
            </div>
          </div>

          {/* 에러 박스 */}
          {surveyError && (
            <div className="survey-error-box" style={{ marginBottom: "12px" }}>{surveyError}</div>
          )}

          {/* 2패널 그리드 */}
          <div className="survey-section-grid">

            {/* 좌: URL & 목표 인원 */}
            <div className="survey-wrapper">
              <div className="survey-badge white-badge">설문 URL & 발송 관리</div>
              <div className="survey-panel">
                {renderUrlArea()}

                {/* 목표 인원 입력 */}
                <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0" }}>
                  <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "#64748b", marginBottom: "8px" }}>
                    발송 목표 인원
                  </p>
                  {[
                    { group: "employee", label: "임직원" },
                    { group: "management", label: "경영진" },
                    { group: "external", label: "외부이해관계자" },
                  ].map(({ group, label }) => (
                    <div className="kpi-input-line" key={group} style={{ marginBottom: "6px" }}>
                      <span>{label}:</span>
                      <input
                        type="number"
                        min="0"
                        value={localTargets[group]}
                        onChange={(e) => handleTargetChange(group, e.target.value)}
                        style={{ width: "70px" }}
                      />
                      <span>명</span>
                    </div>
                  ))}
                  {currentRunId && (
                    <button
                      className="survey-btn secondary"
                      style={{ marginTop: "8px", marginBottom: 0, width: "100%" }}
                      onClick={handleSaveTargets}
                      disabled={!targetsDirty || surveyActionLoading}
                    >
                      {surveyActionLoading ? "저장 중..." : "목표 인원 저장"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* 우: 응답 현황 */}
            <div className="survey-wrapper">
              <div className="survey-badge white-badge">응답 현황</div>
              <div className="survey-panel">

                {/* 버튼 행 */}
                <div className="survey-action-row">
                  <button
                    className="survey-btn secondary"
                    style={{ marginBottom: 0, flex: 1 }}
                    onClick={handleRefreshStatus}
                    disabled={!currentRunId || responseStatusLoading}
                  >
                    {responseStatusLoading ? "갱신 중..." : "응답 현황 갱신"}
                  </button>
                  <button
                    className="survey-btn"
                    style={{ marginBottom: 0, flex: 1 }}
                    onClick={handleImportSurveyResponses}
                    disabled={isActionDisabled}
                    title={!isReady ? "READY 상태 설문 폼이 필요합니다." : ""}
                  >
                    {surveyActionLoading ? "처리 중..." : "응답 가져오기"}
                  </button>
                  <button
                    className="survey-btn"
                    style={{ marginBottom: 0, flex: 1 }}
                    onClick={handleRecalculate}
                    disabled={isActionDisabled}
                    title={!isReady ? "READY 상태 설문 폼이 필요합니다." : ""}
                  >
                    응답 집계 반영
                  </button>
                </div>

                {renderResponseRatePanel()}
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
};

export default Survey;
