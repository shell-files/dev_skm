import React, { useState, useEffect } from "react";
import { Routes, Route } from "react-router";
import '@styles/App.css'
import "@styles/mains.css";
import NotFound from '@errors/NotFound.jsx';
import OnBoard from '@onboards/OnBoard.jsx';
import Benchmarking from '@reports/Benchmarking.jsx';
import Media from '@reports/Media.jsx';
import Survey from '@reports/Survey.jsx';
import Mypage from '@mains/Mypage.jsx';
import Manager from '@mains/Manager.jsx';
import Dashboard from './Dashboard.jsx';
import Headernav from '@components/Layout/HeaderNav.jsx'
import Sidebarnav from '@components/Layout/SidebarNav.jsx'



const Main = () => {
  return (
    <h1>MAIN</h1>
  )
}

const App = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(()=>{
    if (typeof window !== "undefined") {
      return window.innerWidth > 800;
    }
    return true;
  });
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 800) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

	return (
		<div id="main_page">
      {/* 1. 상단 전역 헤더 배치 */}
      <Headernav
        isSidebarOpen={isSidebarOpen}
        toggleSidebar={() => setIsSidebarOpen(prev => !prev)}
      />

      {/* 2. 사이드바와 본문 콘텐츠 영역을 감싸는 Flex 레이아웃 컨테이너 */}
      <div className="content_box">
        {/* 3. 좌측 전역 사이드바 배치 */}
        <Sidebarnav
          isOpen={isSidebarOpen}
          setIsOpen={setIsSidebarOpen}
        />
        <button
            className={`sidebar-edge-toggle ${isSidebarOpen ? "open" : "closed"}`}
            onClick={() => setIsSidebarOpen(prev => !prev)}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {isSidebarOpen ? (
                <path d="M15 18l-6-6 6-6" />
              ) : (
                <path d="M9 18l6-6-6-6" />
              )}
            </svg>
          </button>

        {/* 4. 우측 메인 화면 영역 (URL 경로에 따라 컴포넌트 동적 전환) */}
        <main className="ob-body" style={{ flex: 1, width: '100%' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/company/:id" element={<Main />} />
            <Route path="/onb" element={<OnBoard />} />
            <Route path="/benchmk" element={<Benchmarking />} />
            <Route path="/media" element={<Media />} />
            <Route path="/survey" element={<Survey />} />
            {/* <Route path="/dashboard" element={<Dashboard />} /> */}
            <Route path="/mypage" element={<Mypage />} />
            <Route path="/manager" element={<Manager />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
	);
}

export default App;