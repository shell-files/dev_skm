import { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useAuth } from '@hooks/AuthContext.jsx';
import { setCurruntYear, setMaterialityRunId, fetchApprovalProjects } from '@stores/reportSlice';
import { showDefaultAlert } from '@components/UI/ServiceAlert';
import ApprovalProjectSelectModal from '@mains/modal/ApprovalProjectSelectModal';
import logo from "@assets/images/logos/SKMlogo.png";

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
                if (items.length === 0) {
                    showDefaultAlert(
                        "프로젝트 없음",
                        "등록된 프로젝트가 없습니다. 프로젝트를 먼저 생성해 주세요.",
                        "warning"
                    );
                    return;
                }
                const firstActive =
                    items.find((p) => String(p.runStatus || "ACTIVE").toUpperCase() === "ACTIVE") ?? items[0];
                setCurrentProject(firstActive);
                dispatch(setCurruntYear(firstActive.reportingYear));
                dispatch(setMaterialityRunId(firstActive.runId));
            })
            .catch(() => {
                showDefaultAlert(
                    "프로젝트 조회 실패",
                    "프로젝트 목록을 불러오지 못했습니다. 프로젝트를 생성하거나 다시 시도해 주세요.",
                    "error"
                );
            });
    }, [companyId, dispatch]);

    const handleSelectProject = (project) => {
        setCurrentProject(project);
        dispatch(setCurruntYear(project.reportingYear));
        dispatch(setMaterialityRunId(project.runId));
        setShowProjectModal(false);
    };

    return (
        <>
            <header className="header">
                <div className="header-left-group">
                    <div className="logo-placeholder" style={{ cursor: "pointer" }}>
                        <img id="logo" className="logo" src={logo} onClick={goHome} alt="Logo" />
                    </div>
                </div>

                <div className="header-right-group">
                    {/* 프로젝트 정보 — 선택된 프로젝트가 있을 때만 표시 */}
                    {currentProject ? (
                        <div className="header-project-group">
                            <span className="header-project-badge">
                                {currentYear || currentProject.reportingYear}
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
                    ) : (
                        <div className="header-project-group header-project-empty">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                                <line x1="12" y1="9" x2="12" y2="13" />
                                <line x1="12" y1="17" x2="12.01" y2="17" />
                            </svg>
                            <span className="header-project-none">프로젝트를 생성해 주세요</span>
                        </div>
                    )}
                    <div className="user-link" onClick={goMyPage}>
                        {userName} <span id="current-company-badge">{selectedCompany?.company_name}</span>
                    </div>
                    <button className="header-action" onClick={handleLogout}>로그아웃</button>
                </div>
            </header>

            {currentProject && (
                <ApprovalProjectSelectModal
                    isOpen={showProjectModal}
                    projects={approvalProjects.length > 0 ? approvalProjects : []}
                    selectedRunId={currentProject.runId}
                    onSelectProject={handleSelectProject}
                    onClose={() => setShowProjectModal(false)}
                />
            )}
        </>
    );
};

export default Headernav;
