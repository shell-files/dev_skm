/**
 * AuthContext.jsx - 전역 인증 상태 관리 컨텍스트
 */

import { createContext, useState, useContext, useEffect } from "react";
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { useNavigate } from "react-router";
import { showDefaultAlert } from "@components/UI/ServiceAlert"; // 기존에 쓰시던 알림 컴포넌트

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
  const navigate = useNavigate();

  // [변수] companies: 해당 사용자의 전체 소속 회사 목록
  const [companies, setCompanies] = useState([]);

  // [변수] selectedCompany: 현재 선택된 회사 (role, company_id 등 포함)
  const [selectedCompany, setSelectedCompany] = useState(null);

  // [변수] isAuthReady: localStorage 복원 완료 여부 (라우터 가드에서 활용)
  const [isAuthReady, setIsAuthReady] = useState(false);

  // [추가 변수] 로딩 상태
  const [loading, setLoading] = useState(false);

  /**
   * [이펙트] 앱 진입 시 localStorage에서 이전 세션 복원
   */
  useEffect(() => {
    // 예시: 초기 진입 시 로컬스토리지에 저장된 데이터 복원 및 준비 상태 전환
    const storedCompanies = safeJsonParse(localStorage.getItem("companies"), []);
    const storedSelectedCompany = safeJsonParse(localStorage.getItem("selectedCompany"), null);
    
    if (storedCompanies.length > 0) {
      setCompanies(storedCompanies);
    }
    if (storedSelectedCompany) {
      setSelectedCompany(storedSelectedCompany);
    }
    setIsAuthReady(true);
  }, []);

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
    setLoading(true);
    try {
      // 1. 백엔드에 로그아웃 요청 (쿠키/세션 파기 유도)
      const res = await DELETE('/auth');
      
      if (res.status === true) {
        // 2. 백엔드 처리 성공 시 브라우저 로컬 데이터 완전 청소
        localStorage.removeItem("companies");
        localStorage.removeItem("selectedCompany"); // 선택했던 회사도 초기화
        
        // 3. React 상태 변수 초기화
        setUser(null);
        setCompanies([]);
        setSelectedCompany(null);
        
        showDefaultAlert("로그아웃 완료", "회원 인증이 만료되었습니다.", "success");
        return true; // 성공 플래그 반환
      } else {
        showDefaultAlert("로그아웃 실패", "접속 오류가 발생 했습니다.", "error");
        return false;
      }
    } catch (error) {
      console.error("Logout API failed:", error);
      showDefaultAlert("로그아웃 실패", "네트워크 오류가 발생했습니다.", "error");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // nav관련 navigate를 처리하는 실제 이벤트 핸들러
  const handleLogout = async () => {
    const isSuccess = await logout();
    if (isSuccess) {
      navigate('/'); // 로그아웃이 완벽히 성공하면 홈/로그인 화면으로 이동
    }
  };

  const toggleSidebarMobile = () => {
    const sidebar = document.getElementById('globalSidebar');
    if (sidebar) sidebar.classList.toggle('mobile-open');
  };

  const goHome = () => {
    navigate('/');
  };

  const goMyPage = () => {
    navigate('/mypage');
  };
    
  const openAlarmCenter = () => {
    return;
  };

  /**
   * [함수] hasRole: 현재 사용자가 특정 권한(role)을 가지고 있는지 확인
   */
  const hasRole = (...roles) => {
    const role = selectedCompany?.role || user?.role;
    return roles.includes(role);
  };

  // 전역 인증 상태 관리 컨텍스트에 필요한 값들을 객체로 묶어서 제공
  // 상단 네비바나 사이드바에서 사용할 handleLogout, user, companies 상태 등을 다 넘겨줍니다.
  const authContextValue = {
    user,
    companies,
    selectedCompany,
    isAuthReady,
    loading,
    login,
    logout,
    handleLogout,
    goMyPage,
    goHome,
    selectCompany,
    toggleSidebarMobile,
    hasRole
  };
 
  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  );
};
  
export const useAuth = () => useContext(AuthContext);