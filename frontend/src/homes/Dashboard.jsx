import { useState, useEffect, useRef } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useNavigate } from "react-router";
import ApprovalProjectSelectModal from "@mains/modal/ApprovalProjectSelectModal";
import { useAuth } from "@hooks/AuthContext";
import { setCurruntYear, setMaterialityRunId, fetchApprovalProjects } from "@stores/reportSlice";
import "@styles/dashboard.css";

/* ── Image Assets ── */
import heroVisual from "@assets/home-dashboard/hero-esg-visual.png";
import iconData from "@assets/home-dashboard/icon-data.png";
import iconDma from "@assets/home-dashboard/icon-dma.png";
import iconReport from "@assets/home-dashboard/icon-report.png";
import iconApproval from "@assets/home-dashboard/icon-approval.png";
import iconProject from "@assets/home-dashboard/icon-project.png";
import iconDatabase from "@assets/home-dashboard/icon-database.png";
import iconAnalysis from "@assets/home-dashboard/icon-analysis.png";
import iconDocument from "@assets/home-dashboard/icon-document.png";

/* ── Fallback project data ── */
const MOCK_PROJECTS = [
  { runId: 1, reportingYear: 2026, reportBasisType: "CONSOLIDATED", runStatus: "ACTIVE", currentStageLabel: "플랫폼 소개", pendingCount: 0, readOnlyYn: false },
  { runId: 2, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "COMPLETED", currentStageLabel: "completed", pendingCount: 0, readOnlyYn: true },
  { runId: 3, reportingYear: 2026, reportBasisType: "ENTITY", runStatus: "ACTIVE", currentStageLabel: "데이터 수집", pendingCount: 0, readOnlyYn: false },
  { runId: 4, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "ARCHIVED", currentStageLabel: "규제 검토", pendingCount: 0, readOnlyYn: true },
];

/* ── Module cards data ── */
const MODULE_CARDS = [
  {
    key: "data",
    title: "데이터 입력",
    desc: "ESG 데이터를 체계적으로\n수집하고 관리합니다.",
    tone: "green",
    icon: iconData,
    path: "/onboard",
  },
  {
    key: "dma",
    title: "이중 중요성 평가",
    desc: "재무적·사회적 영향을 분석으로\n우선순위를 도출합니다.",
    tone: "blue",
    icon: iconDma,
    path: "/result",
  },
  {
    key: "report",
    title: "보고서 생성",
    desc: "검증된 데이터와 기반으로\n보고서를 작성·생성합니다.",
    tone: "purple",
    icon: iconReport,
    path: "/draft",
  },
  {
    key: "approval",
    title: "승인 워크플로우",
    desc: "다단계 검토 및 승인으로\n신뢰도를 높입니다.",
    tone: "orange",
    icon: iconApproval,
    // TODO: 승인 워크플로우 전용 route가 확정되면 교체
    path: "/onboard",
  },
];

/* ── Guide steps data ── */
const GUIDE_STEPS = [
  { step: 1, title: "프로젝트 선택", desc: "보고할 프로젝트를\n선택합니다.", icon: iconProject, color: "green" },
  { step: 2, title: "데이터 입력", desc: "ESG 데이터를\n입력합니다.", icon: iconDatabase, color: "green" },
  { step: 3, title: "분석 실행", desc: "이중 중요성 평가를\n수행합니다.", icon: iconAnalysis, color: "blue" },
  { step: 4, title: "보고서 생성", desc: "보고서 초안을\n확인하고 완성합니다.", icon: iconDocument, color: "purple" },
];

/* ── Progress data (static visual placeholder) ── */
/* TODO: Dashboard Summary API 연결 시 실제 progress로 대체 */
const PROGRESS_ITEMS = [
  { label: "데이터 입력", value: 80 },
  { label: "이중 중요성 평가", value: 65 },
  { label: "보고서 초안 생성", value: 40 },
  { label: "승인 및 발행", value: 0 },
];

const OVERALL_PROGRESS = 72;

/* ── Notice data (static — no API) ── */
const NOTICE_ITEMS = [
  { id: 1, isNew: true, text: "ESG 보고 기준 가이드라인 v2.10 배포되었습니다.", date: "03-20" },
  { id: 2, isNew: true, text: "시스템 점검 안내 (03/25 02:00~04:30)", date: "03-18" },
  { id: 3, isNew: false, text: "2024 지속가능경영보고서 템플릿이 업데이트되었습니다.", date: "03-15" },
];

/* ── Helpers (preserved) ── */
const getBasisLabel = (basisType) => {
  if (basisType === "CONSOLIDATED") return "연결 기준";
  if (basisType === "ENTITY") return "독립 기준";
  return "기준 미선택";
};

const getStageLabel = (label) => {
  if (!label) return "-";
  const lower = String(label).toLowerCase();
  if (lower.includes("completed") || lower.includes("all approvals")) return "데이터 승인 완료";
  return label;
};

/* ── Arrow SVG helper ── */
const ArrowRight = ({ size = 20, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14" />
    <path d="M12 5l7 7-7 7" />
  </svg>
);

const ChevronRight = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 18l6-6-6-6" />
  </svg>
);

/* ============================================================
   DASHBOARD COMPONENT
============================================================ */
const Dashboard = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.company_id;
  const companyName = selectedCompany?.company_name || "A_GROUP";
  const currentYear = useSelector((state) => state.report.currentYear);
  const currentRunId = useSelector((state) => state.report.currentRunId);
  const approvalProjects = useSelector((state) => state.report?.approval?.projects ?? []);

  const [showProjectModal, setShowProjectModal] = useState(false);
  const [currentProject, setCurrentProject] = useState(null);
  const guideRef = useRef(null);

  /* ── 회사 변경 시 프로젝트 목록 새로 불러오고 첫 활성 프로젝트 자동 선택 ── */
  useEffect(() => {
    if (!companyId) return;
    dispatch(fetchApprovalProjects({ companyId }))
      .unwrap()
      .then((res) => {
        const items = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : []);
        if (items.length === 0) return;
        const firstActive =
          items.find((p) => String(p.runStatus || "ACTIVE").toUpperCase() === "ACTIVE") ??
          items[0];
        setCurrentProject(firstActive);
        dispatch(setCurruntYear(firstActive.reportingYear));
        dispatch(setMaterialityRunId(firstActive.runId));
      })
      .catch(() => {
        const fallback = MOCK_PROJECTS[0];
        setCurrentProject(fallback);
        dispatch(setCurruntYear(fallback.reportingYear));
        dispatch(setMaterialityRunId(fallback.runId));
      });
  }, [companyId, dispatch]);

  const handleSelectProject = (project) => {
    setCurrentProject(project);
    dispatch(setCurruntYear(project.reportingYear));
    dispatch(setMaterialityRunId(project.runId));
    setShowProjectModal(false);
  };

  const displayProject = currentProject ?? MOCK_PROJECTS[0];
  const projectList = approvalProjects.length > 0 ? approvalProjects : MOCK_PROJECTS;

  /* ── CTA handlers ── */
  const handleStartDataInput = () => {
    navigate("/onboard");
  };

  const handleScrollToGuide = () => {
    guideRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  /* ============================================================
     RENDER
  ============================================================ */
  return (
    <div id="dashboard_page">
      <div className="home-dashboard-page">

        {/* ═══════════════════════════════════════════════════════
            HERO SECTION
        ═══════════════════════════════════════════════════════ */}
        <section className="home-dashboard-hero">
          <div className="home-dashboard-hero-copy">
            <h1 className="home-dashboard-hero-title">
              ESG 데이터를 통합 관리하고,<br />
              신뢰받는 보고서를 완성하세요
            </h1>
            <p className="home-dashboard-hero-desc">
              데이터 수집부터 인증 중요성 평가, 보고서 작성까지<br />
              SKM 플랫폼이 함께합니다.
            </p>
            <div className="home-dashboard-hero-actions">
              <button
                className="home-dashboard-cta-primary"
                onClick={handleStartDataInput}
              >
                데이터 입력 시작하기
                <ArrowRight size={18} color="#fff" />
              </button>
              <button
                className="home-dashboard-cta-secondary"
                onClick={handleScrollToGuide}
              >
                이용 방법 보기
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </button>
            </div>
          </div>

          <div className="home-dashboard-hero-visual">
            <img
              src={heroVisual}
              alt="ESG 데이터 관리 대시보드 일러스트레이션"
              draggable="false"
            />
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════
            MODULE CARDS — 4개
        ═══════════════════════════════════════════════════════ */}
        <section className="home-dashboard-module-grid">
          {MODULE_CARDS.map((mod) => (
            <div
              key={mod.key}
              className="home-dashboard-module-card"
              data-tone={mod.tone}
              onClick={() => navigate(mod.path)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && navigate(mod.path)}
            >
              <div className="home-dashboard-module-icon">
                <img src={mod.icon} alt={mod.title} />
              </div>
              <div className="home-dashboard-module-body">
                <div className="home-dashboard-module-title">{mod.title}</div>
                <div className="home-dashboard-module-desc">
                  {mod.desc.split("\n").map((line, i) => (
                    <span key={i}>{line}{i === 0 && <br />}</span>
                  ))}
                </div>
              </div>
              <div className="home-dashboard-module-arrow">
                <ChevronRight />
              </div>
            </div>
          ))}
        </section>

        {/* ═══════════════════════════════════════════════════════
            MAIN GRID — Progress + Guide
        ═══════════════════════════════════════════════════════ */}
        <section className="home-dashboard-main-grid">

          {/* ── 프로젝트 진행 현황 ── */}
          <div className="home-dashboard-progress-card">
            <div className="home-dashboard-progress-header">
              <h3>프로젝트 진행 현황</h3>
              <div className="home-dashboard-progress-header-right">
                <span className="home-dashboard-stage-link">상세 단계</span>
                <span className="home-dashboard-stage-pill">
                  {getStageLabel(displayProject.currentStageLabel)}
                </span>
              </div>
            </div>

            <div className="home-dashboard-progress-body">
              {/* Circular progress ring */}
              <div className="home-dashboard-progress-ring">
                <div className="home-dashboard-progress-ring-circle">
                  <div className="home-dashboard-progress-ring-inner">
                    <span className="home-dashboard-progress-ring-value">{OVERALL_PROGRESS}%</span>
                    <span className="home-dashboard-progress-ring-label">전체 진행률</span>
                  </div>
                </div>
              </div>

              {/* Progress bars */}
              <div className="home-dashboard-progress-list">
                {PROGRESS_ITEMS.map((item) => (
                  <div key={item.label} className="home-dashboard-progress-item">
                    <span className="home-dashboard-progress-item-label">{item.label}</span>
                    <div className="home-dashboard-progress-bar-track">
                      <div
                        className="home-dashboard-progress-bar-fill"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                    <span className="home-dashboard-progress-item-value">{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="home-dashboard-progress-divider" />

            {/* Project meta row */}
            <div className="home-dashboard-project-meta">
              <div className="home-dashboard-project-meta-item">
                <span className="home-dashboard-project-meta-label">보고 기준 연도</span>
                <span className="home-dashboard-project-meta-value">
                  {currentYear || "2024"}
                </span>
              </div>
              <div className="home-dashboard-project-meta-item">
                <span className="home-dashboard-project-meta-label">프로젝트</span>
                <span className="home-dashboard-project-meta-value">
                  {currentYear || "2024"} 지속가능경영보고서
                </span>
              </div>
              <div className="home-dashboard-project-meta-item">
                <span className="home-dashboard-project-meta-label">대상 회사</span>
                <span className="home-dashboard-project-meta-value">{companyName}</span>
              </div>
              <div className="home-dashboard-project-meta-item">
                <span className="home-dashboard-project-meta-label">보고 범위</span>
                <span className="home-dashboard-project-meta-value">
                  {getBasisLabel(displayProject.reportBasisType)}
                </span>
              </div>
              <button
                className="home-dashboard-project-change-btn"
                onClick={() => setShowProjectModal(true)}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3" />
                  <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
                </svg>
                프로젝트 변경
              </button>
            </div>
          </div>

          {/* ── 처음이신가요? 4단계 가이드 ── */}
          <div className="home-dashboard-guide-card" ref={guideRef}>
            <h3>처음이신가요? 4단계로 시작해 보세요</h3>
            <div className="home-dashboard-guide-steps">
              {GUIDE_STEPS.map((step, idx) => (
                <div key={step.step} className="home-dashboard-guide-step">
                  <div className={`home-dashboard-step-badge ${step.color}`}>
                    {step.step}
                  </div>
                  <div className="home-dashboard-step-icon">
                    <img src={step.icon} alt={step.title} />
                  </div>
                  <div className="home-dashboard-step-title">{step.title}</div>
                  <div className="home-dashboard-step-desc">
                    {step.desc.split("\n").map((line, i) => (
                      <span key={i}>{line}{i === 0 && <br />}</span>
                    ))}
                  </div>
                  {/* Arrow between steps (not after last) */}
                  {idx < GUIDE_STEPS.length - 1 && (
                    <span className="home-dashboard-step-arrow">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M9 18l6-6-6-6" />
                      </svg>
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════
            NOTICE STRIP
        ═══════════════════════════════════════════════════════ */}
        <div className="home-dashboard-notice-strip">
          <div className="home-dashboard-notice-title">
            공지사항
            <span className="home-dashboard-notice-count">{NOTICE_ITEMS.length}</span>
          </div>
          <div className="home-dashboard-notice-list">
            {NOTICE_ITEMS.map((item) => (
              <div key={item.id} className="home-dashboard-notice-item">
                {item.isNew && <span className="home-dashboard-notice-new">NEW</span>}
                <span className="home-dashboard-notice-text">{item.text}</span>
                <span className="home-dashboard-notice-date">{item.date}</span>
              </div>
            ))}
          </div>
          <button className="home-dashboard-notice-more">
            전체 보기 &gt;
          </button>
        </div>

      </div>

      {/* ── 프로젝트 선택 모달 (기존 유지) ── */}
      <ApprovalProjectSelectModal
        isOpen={showProjectModal}
        projects={projectList}
        selectedRunId={displayProject?.runId}
        onSelectProject={handleSelectProject}
        onClose={() => setShowProjectModal(false)}
      />
    </div>
  );
};

export default Dashboard;
