import robot from "@assets/images/robot/robot_repoting_transparent.png";
import benchIcon from "@assets/icons/steps/benchmarking.png";

const BenchResultDashboard = ({
  dashboardOpen, setDashboardOpen, isAnalyzing, showResult,
  progress, displayData, navigate, particleRef,
}) => {
  return (
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
                            <td>
                              <span className={`rank-badge${item.rank <= 3 ? ` rank-top${item.rank}` : ""}`}>
                                {item.rank}
                              </span>
                            </td>
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
  );
};

export default BenchResultDashboard;