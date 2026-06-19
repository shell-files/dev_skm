/**
 * SurveyResultDashboard.jsx
 * 이해관계자 설문 결과 대시보드 슬라이드업 패널.
 * Survey.jsx에서 렌더링; recalcDone 이후 결과(KPI + 2패널) 표시.
 *
 * props:
 *   dashboardOpen / setDashboardOpen — 패널 열림/닫힘 상태
 *   isAnalyzing   — 집계 반영 진행 중 여부 (handle-pill 애니메이션)
 *   recalcDone    — 집계 완료 여부 (결과 뷰 전환 조건)
 *   groups        — 그룹별 응답 현황 (responseStatus.groups)
 *   totals        — 전체 응답 요약 (responseStatus.totals)
 *   surveyTopIssues      — 설문 Top 이슈 점수 목록
 *   surveyResultLoading  — 설문 결과 로딩 중 여부
 *   stakeholderTopIssues — 그룹별 상위 2개 Sub-Issue ({ employee, management, external })
 */

import robot from "@assets/images/robot/robot_servey_t.png";
import surveyIcon from "@assets/icons/steps/survey.png";
import {
  GROUP_META, GROUP_KEYS, GROUP_SCORE_KEY,
  pctFromRate, displayRate, rateBarWidth, fmtScore,
} from "./surveyConstants";

const SurveyResultDashboard = ({
  dashboardOpen, setDashboardOpen, isAnalyzing, recalcDone,
  groups, totals, surveyTopIssues, surveyResultLoading, stakeholderTopIssues,
}) => {
  return (
      <div className={`survey-result-dashboard ${dashboardOpen ? "open" : ""}`}>
        <div className="dashboard-handle" onClick={() => setDashboardOpen((o) => !o)}>
          <div className={`handle-pill${isAnalyzing ? " handle-pill--analyzing" : recalcDone ? " handle-pill--done" : ""}`}>
            {isAnalyzing
              ? "AI 분석 진행 중..."
              : recalcDone
                ? "분석 완료 — 결과 요약 확인"
                : "실시간 분석 대기 중"}
          </div>
        </div>

        {/* Body — result only */}
        {recalcDone && groups ? (
        <div className="sv-dashboard-body">
          <>

              <div className="sv-dashboard-complete-banner">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#15803d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                이중 중대성 평가 점수에 설문 응답이 반영되었습니다. <strong>전체 결과</strong> 페이지에서 상세 결과를 확인하세요.
              </div>

              <div className="survey-kpi-grid" style={{ marginTop: "14px" }}>
                {GROUP_KEYS.map((key) => {
                  const grp  = groups[key];
                  const meta = GROUP_META[key];
                  const hasTarget = grp?.targetCount > 0;
                  return (
                    <div className="survey-kpi-card" key={key}>
                      <div className="stat-label" style={{ color: meta.color, display: "flex", alignItems: "center", gap: "6px" }}>
                        {meta.icon}{meta.label} 응답
                      </div>
                      <div className="stat-value">
                        {grp?.responseCount ?? 0}<span style={{ fontSize: "0.85rem", fontWeight: 500 }}>명</span>
                        <span className="stat-target">{hasTarget ? `(목표 ${grp.targetCount}명)` : "(목표 미설정)"}</span>
                      </div>
                      <div className="kpi-bar-wrap">
                        <div className="kpi-bar-fill" style={{ width: `${rateBarWidth(grp?.responseRate, grp?.targetCount ?? 0)}%`, background: meta.color }} />
                        <span className="kpi-bar-pct" style={{ color: meta.color }}>{displayRate(grp?.responseRate, grp?.targetCount ?? 0)}</span>
                      </div>
                    </div>
                  );
                })}
                {totals && (
                  <div className="survey-kpi-card">
                    <div className="stat-label">전체 응답률</div>
                    <div className="stat-value">
                      {totals.targetCount > 0
                        ? <>{pctFromRate(totals.responseRate).toFixed(1)}<span style={{ fontSize: "0.85rem", fontWeight: 500 }}>%</span></>
                        : <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "#94a3b8" }}>목표 미설정</span>}
                      <span className="stat-target">({totals.responseCount}/{totals.targetCount}명)</span>
                    </div>
                    <div className="kpi-bar-wrap">
                      <div className="kpi-bar-fill" style={{ width: `${rateBarWidth(totals.responseRate, totals.targetCount)}%` }} />
                      <span className="kpi-bar-pct">{displayRate(totals.responseRate, totals.targetCount)}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="survey-panels" style={{ marginTop: "16px" }}>

                {/* Sub-Issue 점수 테이블 (GET /materiality/survey/{runId}) */}
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
                        {surveyResultLoading ? (
                          <tr>
                            <td colSpan="10" style={{ textAlign: "center", color: "#94a3b8", padding: "20px", fontSize: "0.82rem" }}>
                              설문 점수를 불러오는 중...
                            </td>
                          </tr>
                        ) : surveyTopIssues.length > 0 ? (
                          surveyTopIssues.map((issue, i) => (
                            <tr key={issue.subIssueCode ?? i}>
                              <td>{issue.rankNo ?? i + 1}</td>
                              <td style={{ textAlign: "left" }}>{issue.displaySubIssueName ?? issue.subIssueCode}</td>
                              <td>{fmtScore(issue.surveyImpactScore05)}</td>
                              <td>{fmtScore(issue.surveyFinancialScore05)}</td>
                              <td>{fmtScore(issue.employeeImpactScore05)}</td>
                              <td>{fmtScore(issue.employeeFinancialScore05)}</td>
                              <td>{fmtScore(issue.managementImpactScore05)}</td>
                              <td>{fmtScore(issue.managementFinancialScore05)}</td>
                              <td>{fmtScore(issue.externalImpactScore05)}</td>
                              <td>{fmtScore(issue.externalFinancialScore05)}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan="10" style={{ textAlign: "center", color: "#94a3b8", padding: "20px", fontSize: "0.82rem" }}>
                              아직 설문 점수 데이터가 없습니다. 설문 점수 반영 후 다시 확인하세요.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="survey-panel">
                  <div className="panel-header-row">
                    <div className="panel-title">이해관계자 분석</div>
                  </div>
                  <div className="stakeholder-group-list">
                    {GROUP_KEYS.map((key) => {
                      const grp     = groups[key];
                      const meta    = GROUP_META[key];
                      const hasTarget = grp?.targetCount > 0;
                      const topTwo  = stakeholderTopIssues[key] ?? [];
                      return (
                        <div className="stakeholder-item" key={key}>
                          <div className="stakeholder-header">
                            <span className="svgroup-icon-sm" style={{ background: meta.bg, color: meta.color, width: 36, height: 36, borderRadius: 10 }}>
                              {meta.icon}
                            </span>
                            <div style={{ flex: 1 }}>
                              <span className="stakeholder-name">{meta.label}</span>
                              <span className="stakeholder-topics">
                                {hasTarget
                                  ? `응답 ${grp?.responseCount ?? 0}명 / 목표 ${grp.targetCount}명 (${pctFromRate(grp.responseRate).toFixed(1)}%)`
                                  : `응답 ${grp?.responseCount ?? 0}명 / 목표 미설정`}
                              </span>
                            </div>
                          </div>
                          {topTwo.length > 0 ? (
                            <div className="stakeholder-top-issues">
                              {topTwo.map((issue, i) => (
                                <div className="stakeholder-top-issue-row" key={issue.subIssueCode ?? i}>
                                  <span className="stakeholder-issue-rank" style={{ background: meta.bg, color: meta.color }}>{i + 1}위</span>
                                  <span className="stakeholder-issue-name">{issue.displaySubIssueName ?? issue.subIssueCode}</span>
                                  <span className="stakeholder-issue-score" style={{ color: meta.color }}>
                                    {fmtScore(issue[GROUP_SCORE_KEY[key]])}
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="stakeholder-top-empty">점수 데이터 없음</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            </>
          </div>
        ) : (
          <div
            className={`sv-dashboard-analyzing dma-stage ${isAnalyzing ? "dma-stage--running" : ""}`}
            style={{ '--dma-icon': `url(${surveyIcon})`, '--dma-accent': 'var(--survey-primary)' }}
          >
            <div id="particle-field" className="particle-field"></div>
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
            <div className="dma-stage__content">
              <div className="dma-stage__robot">
                <img src={robot} alt="robot" className="dma-stage__img" />
              </div>
              <h3 className="dma-stage__title">
                {isAnalyzing ? "AI 분석 진행 중..." : "분석 준비가 완료되었습니다"}
              </h3>
              <p className="dma-stage__desc">
                {isAnalyzing
                  ? "설문 응답을 이중 중대성 평가 점수에 반영하고 있습니다."
                  : <>응답 가져오기 후 <strong>응답 집계 반영</strong> 버튼을 눌러 설문 결과를 분석해주세요.</>}
              </p>
              {isAnalyzing && (
                <div className="dma-stage__progress dma-stage__progress--indeterminate">
                  <div className="dma-stage__progress-bar">
                    <div className="dma-stage__progress-fill" />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
  );
};

export default SurveyResultDashboard;
