import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useSelector, useDispatch } from 'react-redux';
import { useAuth } from '@hooks/AuthContext.jsx';
import { setCurruntYear, setMaterialityRunId, fetchApprovalProjects } from '@stores/reportSlice';
import ApprovalProjectSelectModal from '@mains/modal/ApprovalProjectSelectModal';
import logo from "@assets/images/logos/SKMlogo.png";

const MOCK_PROJECTS = [
    { runId: 1, reportingYear: 2026, reportBasisType: "CONSOLIDATED", runStatus: "ACTIVE", currentStageLabel: "플랫폼 소개", pendingCount: 0, readOnlyYn: false },
    { runId: 2, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "COMPLETED", currentStageLabel: "completed", pendingCount: 0, readOnlyYn: true },
    { runId: 3, reportingYear: 2026, reportBasisType: "ENTITY", runStatus: "ACTIVE", currentStageLabel: "데이터 수집", pendingCount: 0, readOnlyYn: false },
    { runId: 4, reportingYear: 2025, reportBasisType: "CONSOLIDATED", runStatus: "ARCHIVED", currentStageLabel: "규제 검토", pendingCount: 0, readOnlyYn: true },
];

const Headernav = ({ toggleSidebar, isSidebarOpen }) => {
    const dispatch = useDispatch();
    const { userName, selectedCompany, handleLogout, goHome, goMyPage } = useAuth();
    const companyId = selectedCompany?.company_id;

    const currentYear = useSelector((state) => state.report.currentYear);
    const approvalProjects = useSelector((state) => state.report?.approval?.projects ?? []);

    const [showProjectModal, setShowProjectModal] = useState(false);
    const [currentProject, setCurrentProject] = useState(null);

    useEffect(() => {
        if (!companyId) return;
        dispatch(fetchApprovalProjects({ companyId }))
            .unwrap()
            .then((res) => {
                const items = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : []);
                if (items.length === 0) return;
                const firstActive =
                    items.find((p) => String(p.runStatus || "ACTIVE").toUpperCase() === "ACTIVE") ?? items[0];
                setCurrentProject(firstActive);
                dispatch(setCurruntYear(firstActive.reportingYear));
                dispatch(setMaterialityRunId(firstActive.runId));
            })
            .catch(() => {
                // API 실패 시 mock 값을 Redux/localStorage에 저장하지 않음
                // (잘못된 runId가 벤치마킹 등 하위 API에 전달되는 것을 방지)
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

    return (
        <>
            <header className="header">
                <div className="header-left-group">
                    <div className="logo-placeholder" style={{ cursor: "pointer" }}>
                        <img id="logo" className="logo" src={logo} onClick={goHome} alt="Logo" />
                    </div>
                </div>

                <div className="header-right-group">
                    {/* 프로젝트 정보 */}
                    <div className="header-project-group">
                        <span className="header-project-badge">
                            {currentYear || displayProject.reportingYear}
                        </span>
                        <span className="header-project-name">지속가능경영보고서</span>
                        <button
                            className="header-project-change-btn"
                            onClick={() => setShowProjectModal(true)}
                        >
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3" />
                                <path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" />
                            </svg>
                            프로젝트 변경
                        </button>
                    </div>
                    <div className="user-link" onClick={goMyPage}>
                        {userName} <span id="current-company-badge">{selectedCompany?.company_name}</span>
                    </div>
                    <button className="header-action" onClick={handleLogout}>로그아웃</button>
                </div>
            </header>

            <ApprovalProjectSelectModal
                isOpen={showProjectModal}
                projects={projectList}
                selectedRunId={displayProject?.runId}
                onSelectProject={handleSelectProject}
                onClose={() => setShowProjectModal(false)}
            />
        </>
    );
};

export default Headernav;
