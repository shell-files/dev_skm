import React from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@hooks/AuthContext.jsx';
// import { useAlarm } from '@hooks/AlarmContext.jsx'; 
// import { get } from '@utils/network';
import logo from "@assets/images/logos/SKMlogo.png";

const Headernav = ({ toggleSidebar, isSidebarOpen }) => {
    const navigate = useNavigate();
    const { user, selectedCompany, logout, handleLogout, toggleSidebarMobile, goHome, goMyPage, openAlarmCenter } = useAuth();
    // const { toggleAlarm, unreadCount } = useAlarm();

    return (
        <header className="header">
            <div className="header-left-group">
                <div className="logo-placeholder" style={{cursor:"pointer"}}>
                    <img id="logo" className="logo" src={logo} onClick={goHome} alt="Logo" />
                </div>
            </div>
            <div className="header-right-group">
                <div className="user-link" onClick={goMyPage}>
                    이채훈 <span id="current-company-badge">(SKM)</span>
                </div>
                <button className="header-action" onClick={handleLogout}>로그아웃</button>
                <div className="header-action" onClick={openAlarmCenter}>
                    알림
                    <div className="noti-dot" id="header-noti-dot"></div>
                </div>
            </div>
        </header>
    );
}

export default Headernav;