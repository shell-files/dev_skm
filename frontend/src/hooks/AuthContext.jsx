/**
 * AuthContext.jsx - 전역 인증 상태 관리 컨텍스트
 */

import { createContext, useState, useContext, useEffect, Component } from "react";
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { useNavigate } from "react-router";
import { checkUser, updateUserName } from "@stores/authSlice";
import { useDispatch, useSelector } from "react-redux";
import { logoutUser } from "../stores/authSlice";
import {showConfirmAlert} from "@components/UI/ServiceAlert"

const AuthContext = createContext(null);

/**
 * [유틸] safeJsonParse: localStorage 파싱 실패 시 fallback 반환
 */
const safeJsonParse = (value, fallback) => {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

export const AuthProvider = ({ children }) => {
	// [변수] user: 현재 로그인한 사용자 정보
	const [user, setUser] = useState(null);
  const navigate = useNavigate()

  const dispatch = useDispatch();

	const userName = useSelector((state) => state.auth.userName);

	// [변수] isAuthReady: localStorage 복원 완료 여부 (라우터 가드에서 활용)
	const isAuthReady = useSelector((state) => state.auth.isAuthReady);

  // [변수] 다이렉트 주소
	const redirectUrl = useSelector((state) => state.auth.redirectUrl);

	// [변수] companies: 해당 사용자의 전체 소속 회사 목록
	const companies = useSelector((state) => state.auth.companies);

  const selectedCompany = useSelector((state) => state.auth.selectedCompany);

  // [변수] isLoading: 로딩 상태 여부
	const isLoading = useSelector((state) => state.auth.loading);
  // [변수] 이름 변경 
  const updateName = (newName) => {
    dispatch(updateUserName(newName));
  };
	/**
   * [이펙트] 앱 진입 시 localStorage에서 이전 세션 복원
   */
  useEffect(() => { 
    dispatch(checkUser()); 
  }, []);
  
  // selectedCompany

	/**
   * [이펙트] 앱 진입 시 localStorage에서 이전 세션 복원
   */

	/**
   * [함수] selectCompany: CompanySelect 페이지에서 회사 선택 시 호출
   */
  const selectCompany = (companyId) => {
    const company = companies.find(c => Number(c.company_id) === Number(companyId));
    if (!company) return null;

    setSelectedCompany(company);
    localStorage.setItem("selectedCompany", JSON.stringify(company));
    return company;
  };

	/**
   * [함수] login: 로그인 API 응답 데이터를 받아 전역 상태 및 localStorage에 저장
   */
  const login = (data) => {
		try {
      console.log(data);
    } catch (error) {
      console.error("Login API failed:", error);
    } finally {
      
    }
	};

	/**
   * [함수] logout: API 호출 후 전역 인증 상태 초기화 및 localStorage 전체 삭제
   */
  const logout = async () => {
    try {
      dispatch(logoutUser())
    } catch (error) {
      console.error("Logout API failed:", error);
    } finally {
      
    }
  };

   // nav관련 navigate
   const handleLogout = async () => {
      const isConfirmed = await showConfirmAlert(
        "로그아웃", 
        "정말 로그아웃하시겠습니까?", 
        "warning"
      );

      if (isConfirmed) {
        dispatch(logoutUser())
        location.href = import.meta.env.VITE_API_URL_MAIN;;
      }
    };
    const toggleSidebarMobile = () => {
        const sidebar = document.getElementById('globalSidebar');
        if (sidebar) sidebar.classList.toggle('mobile-open');
    }
    const goHome = () => {
        navigate('/');
    };
    const goMyPage = () => {
        navigate('/mypage');
    };
    
    const openAlarmCenter = () => {
        return;
    }

	/**
	 * [함수] hasRole: 현재 사용자가 특정 권한(role)을 가지고 있는지 확인
	 */
	const hasRole = (...roles) => {
		const role = selectedCompany?.role || user?.role;
		return roles.includes(role);
	};

	// 전역 인증 상태 관리 컨텍스트에 필요한 값들을 객체로 묶어서 제공
	const authContextValue = {login, goMyPage, goHome, 
    userName, selectedCompany, 
    companies, isAuthReady, isLoading,
    updateName, logoutUser,handleLogout};
 
	return (
		<AuthContext.Provider value={authContextValue}>
			{children}
		</AuthContext.Provider>
	);
  
  

};
	
export const useAuth = () => useContext(AuthContext);