import React from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@hooks/AuthContext.jsx';
// import { useAlarm } from '@hooks/AlarmContext.jsx'; 
// import { get } from '@utils/network';
import logo from "@assets/images/logos/SKMlogo.png";

const Headernav = ({ toggleSidebar, isSidebarOpen }) => {
    const navigate = useNavigate();
    const { user, userName, selectedCompany, companies, isAuthReady, logout, handleLogout, toggleSidebarMobile, goHome, goMyPage } = useAuth();
    // const { toggleAlarm, unreadCount } = useAlarm();

    // if (isAuthReady) console.log(userName, selectedCompany, companies);
    
    return (
        <header className="header">
            <div className="header-left-group">
                <div className="logo-placeholder" style={{cursor:"pointer"}}>
                    <img id="logo" className="logo" src={logo} onClick={goHome} alt="Logo" />
                </div>
            </div>
            <div className="header-right-group">
                <div className="user-link" onClick={goMyPage}>
                    {userName} <span id="current-company-badge">({selectedCompany?.company_name})</span>
                </div>
                <button className="header-action" onClick={handleLogout}>로그아웃</button>
            </div>
        </header>
    );
}

export default Headernav;