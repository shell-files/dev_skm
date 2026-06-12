import { useState } from "react";
import { useNavigate } from "react-router";
import ApprovalProjectSelectModal from "./mains/modal/ApprovalProjectSelectModal";
import "@styles/dashboard.css";

const MOCK_PROJECTS = [
  { runId: 1, reportingYear: 2026, reportBasisType: "CONSOLIDATED", runStatus: "ACTIVE",    currentStageLabel: "플랫폼 소개", pendingCount: 0, readOnlyYn: false },
  { runId: 2, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "COMPLETED", currentStageLabel: "completed",   pendingCount: 0, readOnlyYn: true  },
  { runId: 3, reportingYear: 2026, reportBasisType: "ENTITY",       runStatus: "ACTIVE",    currentStageLabel: "데이터 수집",  pendingCount: 0, readOnlyYn: false },
  { runId: 4, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "ARCHIVED",  currentStageLabel: "규제 검토",   pendingCount: 0, readOnlyYn: true  },
];

// Result.jsx 주석 처리된 "필요 온보딩 지표" 데이터 인용
const ONBOARDING_ROWS = [
  { name: "기후변화 대응",          e: true,  s: true,  g: false, count: "8개", done: "3/8", doneColor: "#ef4444" },
  { name: "지속가능한 공급망 관리",  e: false, s: true,  g: true,  count: "6개", done: "2/6", doneColor: "#ef4444" },
  { name: "정보보호 및 데이터 보안", e: false, s: false, g: true,  count: "5개", done: "1/5", doneColor: "#ef4444" },
  { name: "인재 육성 및 역량 강화",  e: false, s: true,  g: false, count: "6개", done: "4/6", doneColor: "#475569" },
  { name: "친환경 제품·서비스 확대", e: true,  s: false, g: false, count: "5개", done: "2/5", doneColor: "#ef4444" },
];

const MODULES = [
  {
    title: "데이터 입력",
    desc: "ESG 데이터를 체계적으로 수집하고 관리합니다.",
    path: "/onboard",
    iconStyle: { background: "#f0fdf4" },
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="3" y1="15" x2="21" y2="15" />
        <line x1="9" y1="3" x2="9" y2="21" />
        <line x1="15" y1="3" x2="15" y2="21" />
      </svg>
    ),
  },
  {
    title: "이중중대성 평가",
    desc: "재무적·비재무적 영향을 분석하여 우선순위를 도출합니다.",
    path: "/result",
    iconStyle: { background: "#eff6ff" },
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="3" x2="12" y2="21" />
        <line x1="3" y1="8" x2="21" y2="8" />
        <line x1="5" y1="8" x2="2" y2="14" /><line x1="5" y1="8" x2="5" y2="14" /><line x1="5" y1="8" x2="8" y2="14" />
        <path d="M2 14 Q5 17 8 14" />
        <line x1="19" y1="8" x2="16" y2="14" /><line x1="19" y1="8" x2="19" y2="14" /><line x1="19" y1="8" x2="22" y2="14" />
        <path d="M16 14 Q19 17 22 14" />
      </svg>
    ),
  },
  {
    title: "보고서 생성",
    desc: "보고서 템플릿을 기반으로 자동화된 보고서를 생성합니다.",
    path: "/draft",
    iconStyle: { background: "#fff7ed" },
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ea580c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
];

const getProjectStatusLabel = (runStatus) => {
  const s = String(runStatus || "ACTIVE").toUpperCase();
  if (s === "COMPLETED") return "완료";
  if (s === "ARCHIVED") return "보관됨";
  return "진행중";
};

const getBasisLabel = (basisType) => {
  if (basisType === "CONSOLIDATED") return "연결기준";
  if (basisType === "ENTITY") return "독립기준";
  return "기준 미선택";
};

const getStageLabel = (label) => {
  if (!label) return "-";
  const lower = String(label).toLowerCase();
  if (lower.includes("completed") || lower.includes("all approvals")) return "데이터 승인 완료";
  return label;
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [currentProject, setCurrentProject] = useState(MOCK_PROJECTS[0]);

  const handleSelectProject = (project) => {
    setCurrentProject(project);
    setShowProjectModal(false);
  };

  return (
    <div id="dashboard_page">

      {/* ── 페이지 헤더 ── */}
      <section className="db-header">
        <h1>ESG 통합 관리 대시보드</h1>
      </section>

      {/* ── 현재 프로젝트 배너 ── */}
      <section className="db-project-banner">
        <div>
          <p className="db-project-label">현재 보고서 프로젝트</p>
          <h2 className="db-project-title">
            {currentProject.reportingYear} 지속가능경영보고서
          </h2>
          <p className="db-project-meta">
            A_GROUP · {getBasisLabel(currentProject.reportBasisType)} · {getProjectStatusLabel(currentProject.runStatus)}
          </p>
        </div>

        <div className="db-project-right">
          <div className="db-flag-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
              <line x1="4" y1="22" x2="4" y2="15" />
            </svg>
          </div>

          <div className="db-project-actions">
            <span className="db-stage-chip">
              현재 단계: {getStageLabel(currentProject.currentStageLabel)}
            </span>
            <button className="db-change-btn" onClick={() => setShowProjectModal(true)}>
              프로젝트 변경
            </button>
          </div>
        </div>
      </section>

      {/* ── 소개 카드 3개 ── */}
      <section className="db-info-grid">

        {/* 플랫폼 소개 */}
        <div className="db-card">
          <div className="db-card-header">
            <div className="db-icon-circle green">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <h3 className="db-card-title">플랫폼 소개</h3>
          </div>
          <p className="db-card-desc">
            ESG 데이터 수집부터 분석, 보고서 작성, 승인 워크플로우까지 통합 관리하는 플랫폼입니다.
          </p>
          <ul className="db-card-list">
            <li>ESG 데이터 수집 및 관리</li>
            <li>이중중대성(DMA) 분석 지원</li>
            <li>보고서 자동화 및 템플릿 제공</li>
            <li>승인 워크플로우 및 이력 관리</li>
          </ul>
        </div>

        {/* 이용 방법 */}
        <div className="db-card">
          <div className="db-card-header">
            <div className="db-icon-circle blue">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </div>
            <h3 className="db-card-title">이용 방법</h3>
          </div>
          <div className="db-steps-list">
            {[
              ["프로젝트 선택", "보고할 프로젝트를 선택합니다."],
              ["데이터 입력",   "필요한 데이터를 입력하고 관리합니다."],
              ["분석 실행",     "분석을 실행하고 결과를 확인합니다."],
              ["결과 검토",     "결과를 검토하고 보고서를 완성합니다."],
            ].map(([title, desc], i) => (
              <div key={i} className="db-step-item">
                <span className="db-step-num">{i + 1}</span>
                <div>
                  <span className="db-step-title">{title}</span>
                  <span className="db-step-desc">{desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 빠른 안내 */}
        <div className="db-card">
          <div className="db-card-header">
            <div className="db-icon-circle orange">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ea580c" strokeWidth="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </div>
            <h3 className="db-card-title">빠른 안내</h3>
          </div>
          <ul className="db-card-list">
            <li>현재 화면은 소개 대시보드입니다.</li>
            <li>좌측 메뉴에서 세부 기능으로 이동할 수 있습니다.</li>
            <li>실제 데이터는 각 모듈에서 입력됩니다.</li>
          </ul>
        </div>
      </section>

      {/* ── 주요 모듈 + 최근 공지 ── */}
      <section className="db-main-grid">

        {/* 주요 모듈 — 3개 가로 배치 */}
        <div className="db-card">
          <p className="db-section-title">주요 모듈</p>
          <div className="db-modules-grid">
            {MODULES.map((mod) => (
              <div
                key={mod.title}
                className="db-module-item"
                onClick={() => navigate(mod.path)}
              >
                <div className="db-module-icon" style={mod.iconStyle}>
                  {mod.icon}
                </div>
                <div>
                  <div className="db-module-title">{mod.title}</div>
                  <div className="db-module-desc">{mod.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 필요 온보딩 지표 */}
        <div className="db-card">
          <div className="db-notice-header">
            <p className="db-section-title">필요 온보딩 지표</p>
            <button className="db-notice-view-all" onClick={() => navigate("/onboard")}>
              전체 보기 →
            </button>
          </div>
          <table className="db-onboard-table">
            <thead>
              <tr>
                <th>이슈</th>
                <th>E</th>
                <th>S</th>
                <th>G</th>
                <th>지표 수</th>
                <th>완료</th>
              </tr>
            </thead>
            <tbody>
              {ONBOARDING_ROWS.map((row, i) => (
                <tr key={i}>
                  <td>{row.name}</td>
                  {[row.e, row.s, row.g].map((v, j) => (
                    <td key={j}>
                      <span className={`db-onboard-check ${v ? "on" : "off"}`}>
                        {v ? "✓" : "—"}
                      </span>
                    </td>
                  ))}
                  <td className="db-onboard-count">{row.count}</td>
                  <td className="db-onboard-done" style={{ color: row.doneColor }}>{row.done}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── 플랫폼 활용 팁 배너 ── */}
      <section className="db-tip-banner">
        <div className="db-tip-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="3" strokeLinecap="round" />
          </svg>
        </div>
        <strong className="db-tip-label">플랫폼 활용 팁</strong>
        <div className="db-tip-list">
          {[
            "정확한 데이터 입력이 신뢰도 높은 보고서의 시작입니다.",
            "DMA 분석으로 핵심 이슈의 우선순위를 확인하세요.",
            "승인 워크플로우를 통해 협업 효율을 높이세요.",
          ].map((tip, i) => (
            <span key={i} className="db-tip-item">• {tip}</span>
          ))}
        </div>
      </section>

      {/* ── 프로젝트 선택 모달 ── */}
      <ApprovalProjectSelectModal
        isOpen={showProjectModal}
        projects={MOCK_PROJECTS}
        selectedRunId={currentProject?.runId}
        onSelectProject={handleSelectProject}
        onClose={() => setShowProjectModal(false)}
      />
    </div>
  );
};

export default Dashboard;
