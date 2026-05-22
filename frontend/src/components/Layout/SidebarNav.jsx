import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router";
import { useAuth } from '@hooks/AuthContext.jsx';

const Sidebarnav = ({ isOpen, setIsOpen }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const { selectedCompany, selectCompany, handleLogout, goHome, goMyPage, openAlarmCenter } = useAuth();

    // 권한 확인
    const role = selectedCompany?.role || "ESG담당자";
    const isSysAdmin = role === "시스템관리자";
    const isESG = role === "ESG담당자" || role === "ESG 담당자";
    const isConsultant = role === "컨설턴트";

    const canViewService = isSysAdmin || isESG || isConsultant;
    const canViewAdmin = isSysAdmin || isESG || isConsultant;

    // 아코디언 상태 관리
    const [expanded, setExpanded] = useState({
        service: true,
        admin: false,
        settings: false
    });

    const [expandedSub, setExpandedSub] = useState({
        report: false,
        carbon: false,
        supply: false
    });

    const [filteredCompanies, setFilteredCompanies] = useState([]);
    const [companies, setCompanies] = useState([]);
    const [companie, setCompanie] = useState("");
    const [searchTerm, setSearchTerm] = useState("");

    const toggleAccordion = (key) => {
        setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const toggleSubAccordion = (key, e) => {
        e.stopPropagation();
        setExpandedSub(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const isActive = (path) => location.pathname.includes(path);

    // 커스텀 스크롤 인디케이터 로직
    const scrollRef = useRef(null);
    const indicatorRef = useRef(null);
    const isDraggingRef = useRef(false);

    const [showIndicator, setShowIndicator] = useState(false);
    const [activeIndex, setActiveIndex] = useState(0);
    const dashCount = 8;

    const handleScroll = () => {
        if (!scrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;

        if (scrollHeight > clientHeight + 1) {
            setShowIndicator(true);
            const scrollRatio = scrollTop / (scrollHeight - clientHeight);
            const index = Math.min(
                dashCount - 1,
                Math.max(0, Math.round(scrollRatio * (dashCount - 1)))
            );
            setActiveIndex(index);
        } else {
            setShowIndicator(false);
        }
    };

    const handlePointerMove = (e) => {
        if (!isDraggingRef.current || !scrollRef.current || !indicatorRef.current) return;
        const rect = indicatorRef.current.getBoundingClientRect();
        const y = e.clientY - rect.top;
        const ratio = Math.max(0, Math.min(1, y / rect.height));

        const scrollArea = scrollRef.current;
        const maxScroll = scrollArea.scrollHeight - scrollArea.clientHeight;
        scrollArea.scrollTop = ratio * maxScroll;
    };

    const handlePointerUp = () => {
        isDraggingRef.current = false;
        window.removeEventListener('pointermove', handlePointerMove);
        window.removeEventListener('pointerup', handlePointerUp);
        document.body.style.userSelect = '';
        if (scrollRef.current) {
            scrollRef.current.style.scrollBehavior = 'smooth';
        }
    };

    const handlePointerDown = (e) => {
        isDraggingRef.current = true;
        if (scrollRef.current) {
            scrollRef.current.style.scrollBehavior = 'auto';
        }
        handlePointerMove(e);
        window.addEventListener('pointermove', handlePointerMove);
        window.addEventListener('pointerup', handlePointerUp);
        document.body.style.userSelect = 'none';
    };

    useEffect(() => {
        const allCompanie = localStorage.getItem("companies");
        const parsedCompanies = allCompanie ? JSON.parse(allCompanie) : [];
        const arr = [
            { "company_id": 0, "company_name": "선택하세요" },
            ...parsedCompanies
        ];
        setCompanies(arr);
        setFilteredCompanies(arr);
        return () => {
            window.removeEventListener('pointermove', handlePointerMove);
            window.removeEventListener('pointerup', handlePointerUp);
        };
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => {
            handleScroll();
        }, 350);
        return () => clearTimeout(timer);
    }, [expanded, expandedSub]);

    useEffect(() => {
        let observer;
        if (scrollRef.current) {
            observer = new ResizeObserver(() => handleScroll());
            observer.observe(scrollRef.current);
            if (scrollRef.current.firstElementChild) {
                observer.observe(scrollRef.current.firstElementChild);
            }
        }
        return () => {
            if (observer) observer.disconnect();
        };
    }, []);

    const searchCompanie = target => {
        setFilteredCompanies(target === "" ? companies : companies.filter(company => {
            if ("선택하세요".includes(target.toLowerCase())) return false;
            else if (company.company_name === "선택하세요") return true;
            return company.company_name.toLowerCase().includes(target.toLowerCase());
        }));
    }

    const setCompany = target => {
        if (target > 0) {
            selectCompany(target);
            setCompanie(target);
            setSearchTerm("");
        }
    }

    const goBenchMk = () => { navigate("/benchmk"); if(window.innerWidth <= 800) setIsOpen(false); };
    const goOnboard = () => { navigate("/onb"); if(window.innerWidth <= 800) setIsOpen(false); };
    const goManager = () => { navigate("/manager"); if(window.innerWidth <= 800) setIsOpen(false); };
    const handleGoHome = () => { goHome(); if(window.innerWidth <= 800) setIsOpen(false); };

    return (
        <aside
            className={`sidebar ${isOpen ? "open" : "closed"}`}
            id="globalSidebar"
        >
            <div className="nav-scroll-wrapper">
                <div className="nav-scroll-area" ref={scrollRef}>
                    <div className="nav-group">
                        <div className="nav-item" onClick={handleGoHome}>
                            <span>대시보드</span>
                        </div>
                    </div>
                    <div className="nav-group">
                        <div className="nav-item" onClick={goBenchMk}>
                            <div className="nav-accordion-header">
                                <span>지속가능경영보고서</span>
                            </div>
                        </div>
                    </div>
                    <div className="nav-group">
                        <div className="nav-item" onClick={goOnboard}>
                            <span>데이터 입력</span>
                        </div>
                    </div>
                    <div className="nav-group">
                        <div
                            className="nav-item"
                            onClick={() => toggleAccordion("admin")}
                        >
                            <div className="nav-accordion-header">
                                <span>ESG 담당자 통합 관리</span>
                                <svg className={`nav-arrow ${expanded.admin ? "expanded" : ""}`} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M9 5l7 7-7 7"></path>
                                </svg>
                            </div>
                        </div>

                        <div className={`nav-accordion-content ${expanded.admin ? "expanded" : ""}`}>
                            <div className="inner-wrapper">
                                <div className="nav-item sub-item" onClick={goManager}>데이터 승인</div>
                            </div>
                        </div>
                    </div>
                    <div className="nav-group">
                        <div className="nav-item" onClick={() => toggleAccordion("settings")}>
                            <div className="nav-accordion-header">
                                <span>환경 설정</span>
                                <svg className={`nav-arrow ${expanded.settings ? "expanded" : ""}`} viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M9 5l7 7-7 7"></path>
                                </svg>
                            </div>
                        </div>

                        <div className={`nav-accordion-content ${expanded.settings ? "expanded" : ""}`}>
                            <div className="inner-wrapper">
                                <div className="nav-item sub-item" onClick={() => { goMyPage(); if(window.innerWidth <= 800) setIsOpen(false); }}>
                                    내 계정 설정
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="sidebar-footer">
                <div className="search-container">
                    <input type="text" className="company-search" id="companySearchInput" placeholder="회사 검색..." />
                </div>
                <select className="company-select" id="sidebarCompanySelect">
                    <option value="SKM">SKM</option>
                    <option value="HG">HG</option>
                    <option value="TV">TV</option>
                </select>
            </div>
        </aside>
    );
}

export default Sidebarnav;