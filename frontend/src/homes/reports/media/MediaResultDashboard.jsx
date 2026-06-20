/**
 * MediaResultDashboard.jsx
 * 미디어 분석 결과 대시보드 슬라이드업 패널.
 * Media.jsx에서 렌더링; showResult/isAnalyzing 상태에 따라
 * 로딩 애니메이션 ↔ 결과(KPI + 3패널) 전환.
 *
 * props:
 *   dashboardOpen / setDashboardOpen — 패널 열림/닫힘 상태
 *   showResult    — 결과 표시 여부
 *   isAnalyzing   — AI 파이프라인 수집 진행 중 여부
 *   progress      — 분석 진행률 (0~100)
 *   loadingTitle / loadingDesc — 로딩 상태 표시 텍스트 (Media.jsx에서 단계별로 변경)
 *   dashboardData — mapMediaResultToDashboard 변환 결과 (stats/sourceTable/topIssues)
 *   navigate      — react-router useNavigate (다음 단계 이동)
 *   particleRef   — particle-field DOM ref
 */

import robot from "@assets/images/robot/robot_media_t.png";
import ResultStatCard from "@components/UI/ResultStatCard";
import analyzingIcon from "@assets/icons/steps/analyzing.png";
import { REFLECT_METHODS } from "./mediaData";

const MediaResultDashboard = ({
  dashboardOpen,
  setDashboardOpen,
  showResult,
  isAnalyzing,
  progress,
  loadingTitle,
  loadingDesc,
  dashboardData,
  navigate,
  particleRef,
}) => {
  return (
    <div className={`media-result-dashboard ${dashboardOpen ? "open" : ""} ${showResult ? "result-expanded" : ""}`}>
      <div className="dashboard-handle" onClick={() => setDashboardOpen(!dashboardOpen)}>
        <div className={`handle-pill ${showResult ? "complete" : ""}`}>
          {isAnalyzing ? "AI 파이프라인 수집 가동 중..." : showResult ? "분석 완료 - 결과 요약 확인 (클릭)" : "실시간 분석 대기 중"}
        </div>
      </div>
      {(dashboardOpen || isAnalyzing || showResult) && (
        <div
          className={`robot-view-container dma-stage ${isAnalyzing ? "dma-stage--running" : ""} ${showResult ? "showing-result" : ""}`}
          style={{ '--dma-icon': `url(${analyzingIcon})`, '--dma-accent': 'var(--media-primary)' }}
        >
          <div id="particle-field" ref={particleRef}></div>
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
          {!showResult && (
            <div className="dma-stage__content">
              <div className="dma-stage__robot">
                <img src={robot} className="dma-stage__img" alt="마스코트 로봇" />
              </div>
              <h3 className="dma-stage__title">{loadingTitle}</h3>
              <p className="dma-stage__desc">{loadingDesc}</p>
              {isAnalyzing && (
                <div className="dma-stage__progress">
                  <div className="dma-stage__progress-bar">
                    <div className="dma-stage__progress-fill" style={{ width: `${progress}%` }}></div>
                  </div>
                  <div className="dma-stage__progress-pct">{progress}% 분석 중</div>
                </div>
              )}
            </div>
          )}
          {showResult && (
            <div className="result-layout" style={{ zIndex: 3 }}>
              <div className="media-result-banner">
                <div className="media-result-banner-left">
                  <span className="media-result-banner-badge">
                    <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                      <path d="M2.5 6l2.5 2.5 4.5-5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    AI 분석 완료
                  </span>
                  <div className="media-result-banner-title">미디어 시그널 분석 결과</div>
                  <p className="media-result-banner-desc">
                    언론 기사, 전문기관 자료, 핵심규제 프레임을 종합 반영하여<br />
                    외부 시그널 기반의 주요 서브이슈를 도출했습니다.
                  </p>
                </div>
                <img src={robot} className="media-result-banner-robot" alt="robot" />
              </div>

              <div className="result-stats-row">
                <ResultStatCard
                  label="언론 기사"
                  value={dashboardData?.stats?.press?.count ?? "0건"}
                  sub={dashboardData?.stats?.press?.sub ?? ""}
                  colorClass="stat-card-blue"
                  icon={<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>}
                />
                <ResultStatCard
                  label="전문기관 자료"
                  value={dashboardData?.stats?.expert?.count ?? "0건"}
                  sub={dashboardData?.stats?.expert?.sub ?? ""}
                  colorClass="stat-card-purple"
                  icon={<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="22" x2="21" y2="22" /><line x1="6" y1="18" x2="6" y2="11" /><line x1="10" y1="18" x2="10" y2="11" /><line x1="14" y1="18" x2="14" y2="11" /><line x1="18" y1="18" x2="18" y2="11" /><polygon points="12 2 2 7 22 7" /></svg>}
                />
                <ResultStatCard
                  label="규제 프레임"
                  value={dashboardData?.stats?.regulation?.count ?? "0건"}
                  sub={dashboardData?.stats?.regulation?.sub ?? ""}
                  colorClass="stat-card-orange"
                  icon={<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>}
                />
                <ResultStatCard
                  label="반영 이슈 총계"
                  value={dashboardData?.stats?.total?.count ?? "0개"}
                  colorClass="stat-card-green"
                  icon={<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>}
                />
              </div>

              <div className="result-panels-row">
                <div className="result-panel panel-accent-blue">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-blue" />
                      Source 별 반영 현황
                    </span>
                    <span className="panel-badge-count">{(dashboardData?.sourceTable ?? []).length}건</span>
                  </div>
                  <div className="panel-body">
                    <table className="issue-table">
                      <thead>
                        <tr>
                          <th>Source</th><th>수집</th><th>반영</th><th>방식</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(dashboardData?.sourceTable ?? []).map((row, i) => (
                          <tr key={i}>
                            <td>{row.source}</td>
                            <td>{row.count}</td>
                            <td>{row.issues}</td>
                            <td>{row.method}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="result-panel panel-accent-green">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-green" />
                      미디어 TOP 이슈 점수
                    </span>
                    <span className="panel-badge-count">{(dashboardData?.topIssues ?? []).length}건</span>
                  </div>
                  <div className="panel-body">
                    <table className="issue-table">
                      <thead>
                        <tr>
                          <th style={{ width: "36px" }}>순위</th>
                          <th>Sub Issue</th>
                          <th>Impact</th>
                          <th>Financial</th>
                          <th>Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(dashboardData?.topIssues ?? []).map((item) => (
                          <tr key={item.rank}>
                            <td>
                              <span className={`rank-badge${item.rank <= 3 ? ` rank-top${item.rank}` : ""}`}>
                                {item.rank}
                              </span>
                            </td>
                            <td>{item.name}</td>
                            <td>{item.impact}</td>
                            <td>{item.financial}</td>
                            <td>{item.source}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="result-panel panel-accent-purple">
                  <div className="panel-header-row">
                    <span className="panel-title">
                      <span className="panel-dot dot-purple" />
                      반영 방식 안내
                    </span>
                  </div>
                  <div className="panel-body">
                    <ul className="reflect-list">
                      {REFLECT_METHODS.map((item) => (
                        <li key={item.key} className="reflect-item">
                          <div className="reflect-icon">{item.icon}</div>
                          <div>
                            <div className="reflect-title">{item.title}</div>
                            <p className="reflect-desc">{item.desc}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                    <div className="reflect-note">ⓘ 향후 MSCI·S&P·EcoVadis 등 외부 평가기관 자료 확장 가능</div>
                  </div>
                </div>
              </div>

              <div className="result-next-row">
                <button type="button" className="result-next-btn" onClick={() => navigate("/survey")}>
                  다음 단계: 이해관계자 설문으로 이동
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MediaResultDashboard;
