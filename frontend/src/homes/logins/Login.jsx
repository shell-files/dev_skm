/**
 * Login.jsx 페이지 흐름 및 구조 가이드
 *
 * 1. 상태(State) 구성:
 *    - view: 화면 전환 관리 ('login' | 'forgot' | 'success')
 *    - formData: 모든 입력값 통합 관리 (이메일, 비밀번호 등)
 *    - errors: 유효성 검사 및 API 에러 메시지 관리
 *    - loading: API 통신 중 버튼 비활성화 및 스피너 제어
 *
 * 2. 주요 로직 흐름:
 *    - 로그인: handleLogin -> validate 확인 -> requestApi.login 호출 -> 성공 시 AuthContext.login 및 페이지 이동
 *    - 비번 찾기: handleResetPassword -> validate 확인 -> requestApi.resetPassword 호출 -> 성공 시 'success' 뷰 전환
 *    - 뷰 전환: setView 및 setErrors 초기화를 통해 화면 간 상태 격리
 *
 * 3. 외부 연동:
 *    - useAuth: 전역 로그인 상태 관리 (세션 유지)
 *    - useNavigate: 라우팅 (메인 홈, 회사 선택, 게이트 페이지 등)
 *    - api (network.js): 실제 백엔드 서버와의 HTTP 통신
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import LoginBackground from "@components/Layout/LoginBackground";
import LoginVisualPanel from "@logins/LoginVisualPanel";
import "@styles/logins.css";
import emailIcon from "@assets/icons/base/email-icon.png"; // 새로 추가된 아이콘

import { useAuth } from '@hooks/AuthContext.jsx';

// ── requestApi: 인증 관련 통신 함수 모음 ──
const requestApi = {
  /**
   * 1. login: 로그인 API 요청
   * @param {string} email - 사용자 이메일
   * @param {string} password - 사용자 비밀번호
   * @returns {object} - 로그인 성공 시 사용자 정보 및 소속 회사 목록 반환
   */
  login: async (email, password) => {
    const res = await POST("/auth", { email, password });
    return res.data;
  },

  /**
   * 2. resetPassword: 임시 비밀번호 발송 API 요청 (PUT /verification)
   * @param {string} email - 임시 비밀번호를 받을 이메일 주소
   */
  resetPassword: async (email) => {
    try {
      const res = await PUT("/verification", { email });
      // 성공 시 문자열 반환 (200 OK)
      return { status: true, data: res.data };
    } catch (e) {
      return { status: false, message: e.response?.data?.message || "이메일 발송에 실패했습니다." };
    }
  }
};

const Login = () => {
  // [연결] useAuth(): 전역 인증 상태를 업데이트하는 login 함수 가져오기
  const { login } = useAuth();

  // [연결] useNavigate(): 페이지 이동을 위한 네비게이트 함수
  const navigate = useNavigate();

  // ── States ──

  // [변수] view: 현재 활성화된 화면 섹션 관리
  const [view, setView] = useState("login");

  // [변수] formData: 로그인 및 비밀번호 재설정에 필요한 모든 입력 데이터 통합 관리
  const [formData, setFormData] = useState({ loginEmail: "", loginPassword: "", resetEmail: "" });

  // [변수] errors: 각 입력 필드별 유효성 검사 에러 메시지 저장
  const [errors, setErrors] = useState({});

  // [변수] loading: API 호출 중 중복 클릭 방지 및 로딩 스피너 제어
  const [loading, setLoading] = useState(false);

  // [변수] isReady: 초기 레이아웃 시프트를 방지하기 위한 렌더링 준비 상태
  const [isReady, setIsReady] = useState(false);

  /**
   * [이펙트] 초기화 로직
   * - 페이지 진입 시 body에 'login' ID 부여 (CSS 스코프용)
   * - cleanup 시 ID 제거 및 프레임 취소
   */
  useEffect(() => {
    const frame = requestAnimationFrame(() => requestAnimationFrame(() => setIsReady(true)));
    document.body.id = "login";
    // localStorage.removeItem("companies");
    return () => { cancelAnimationFrame(frame); document.body.removeAttribute("id"); };
  }, []);

  /**
   * [함수] validate: 입력 필드 유효성 검사 (실시간 및 블러 시 동작)
   * @param {string} name - 검사할 필드 이름 (formData의 key)
   * @param {string} value - 검사할 값
   * @returns {string} - 에러 메시지 (정상이면 빈 문자열)
   */
  const validate = (name, value) => {
    let msg = "";
    if (!value.trim()) {
      msg = name.toLowerCase().includes("email") ? "이메일을 입력해 주세요." : "비밀번호를 입력해 주세요.";
    } else if (name.toLowerCase().includes("email") && !/\S+@\S+\.\S+/.test(value)) {
      msg = "올바른 이메일 주소를 입력해 주세요.";
    }
    setErrors(prev => ({ ...prev, [name]: msg }));
    return msg;
  };

  /**
   * [핸들러] handleLogin: 로그인 폼 제출 처리
   * [연결] validate(), requestApi.login(), AuthContext.login()
   */
  const handleLogin = async (e) => {
    e.preventDefault();
    // 1. 유효성 검사
    if (validate("loginEmail", formData.loginEmail) || validate("loginPassword", formData.loginPassword)) return;

    try {
      setLoading(true);
      // 2. API 요청
      const params = { email: formData.loginEmail, password: formData.loginPassword };
      login(params);
    } catch (err) {
      setErrors(p => ({ ...p, loginSubmit: "이메일 또는 비밀번호가 일치하지 않습니다." }));
    } finally { setLoading(false); }
  };

  /**
   * [핸들러] handleResetPassword: 비밀번호 재설정 요청 처리
   * [연결] validate(), requestApi.resetPassword()
   */
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (validate("resetEmail", formData.resetEmail)) return;

    try {
      setLoading(true);
      const res = await requestApi.resetPassword(formData.resetEmail);
      if (res.status) setView("success");
      else throw new Error(res.message);
    } catch (err) {
      showDefaultAlert("발송 실패", "이메일 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.", "error");
    } finally { setLoading(false); }
  };

  /**
   * [함수] maskEmail: 이메일 보안을 위한 마스킹 처리 (success 뷰에서 사용)
   */
  const maskEmail = (email) => {
    const [id, domain] = email.split("@");
    if (!id || !domain) return email;
    return `${id.length <= 2 ? id[0] : id.slice(0, 2)}***@${domain}`;
  };

  /**
   * [함수] showInquiry: 각종 안내 모달 출력 (계정 찾기, 고객센터 등)
   */
  const showInquiry = (type) => {
    if (type === 'account') {
      showDefaultAlert("계정 정보 문의", "보안 정책상 계정 조회는 <span class='text-point'>사내 관리자</span>를 통해 진행됩니다.", "info");
    } else {
      showDefaultAlert("도움이 필요하신가요?", "<span class='text-point'>platformanagers@gmail.com</span>으로 문의해 주세요.", "question");
    }
  };

  /**
   * [헬퍼 렌더러] renderInput: 공통 입력 필드 렌더링 함수
   * @param {string} name - 필드 고유 이름
   * @param {string} type - input 타입 (text, password, email)
   * @param {string} placeholder - 플레이스홀더 텍스트
   * @param {string} value - 현재 입력값
   */
  const renderInput = (name, type, placeholder, value) => (
    <div className="input-wrapper">
      <input
        type={type}
        name={name}
        placeholder={placeholder}
        className={errors[name] ? "input-error" : ""}
        value={value}
        autoComplete={type === 'password' ? 'new-password' : 'off'}
        onChange={e => {
          setFormData(p => ({ ...p, [name]: e.target.value }));
          setErrors(p => ({ ...p, [name]: "" }));
        }}
        onBlur={e => validate(name, e.target.value)}
      />
      {errors[name] && <p className="error-text">{errors[name]}</p>}
    </div>
  );

  // 초기 준비 중일 때는 아무것도 렌더링하지 않음 (레이아웃 튐 방지)
  if (!isReady) return null;

  return (
    <div id="login">
      <LoginBackground>
        <div className="login-combined-card">
          <LoginVisualPanel />
          <section className="login-form-panel">
            <div className="login-card-viewport">

              {/* [SECTION] 1. Login View: 일반 로그인 화면 */}
              {view === "login" && (
                <div className="login-card active" id="login-section">
                  {/* <div className="header-nav"><span className="back-btn" onClick={() => navigate("/")}>←</span></div> */}
                  <div className="login-logo-mark">ESG DATA PLATFORM</div>
                  <h1>Login</h1>
                  <form className="input-group" onSubmit={handleLogin}>
                    {renderInput("loginEmail", "email", "이메일을 입력해주세요", formData.loginEmail)}
                    {renderInput("loginPassword", "password", "비밀번호를 입력해주세요", formData.loginPassword)}
                    <div className="links">
                      <span onClick={() => navigate("/signup")}>회원 가입</span> | <span onClick={() => showInquiry('account')}>이메일 찾기</span> | <span className="active-link" onClick={() => setView("forgot")}>비밀번호 찾기</span>
                    </div>
                    <button className="login-action-button" type="submit" disabled={loading}>
                      {loading ? <span className="button-spinner" /> : "로그인"}
                    </button>
                    {errors.loginSubmit && <p className="error-text submit-error">{errors.loginSubmit}</p>}
                  </form>
                </div>
              )}

              {/* [SECTION] 2. Forgot View: 비밀번호 찾기 (이메일 입력) */}
              {view === "forgot" && (
                <div className="login-card active" id="forgot-section">
                  <div className="header-nav"><span className="back-btn" onClick={() => { setView("login"); setErrors({}); }}>←</span></div>
                  <div className="login-logo-mark">ESG DATA PLATFORM</div>
                  <div className="forgot-view-header">
                    <h1>비밀번호 찾기</h1>
                    <div className="forgot-visual-wrap"><img src={emailIcon} alt="email" className="forgot-visual-image" /></div>
                  </div>
                  <form className="input-group" onSubmit={handleResetPassword}>
                    {renderInput("resetEmail", "email", "이메일을 입력해주세요", formData.resetEmail)}
                    <div className="info-box"><strong>임시 비밀번호 발송 안내</strong><br />입력하신 이메일로 임시 비밀번호가 발송됩니다.</div>
                    <button className="login-action-button" type="submit" disabled={loading}>
                      {loading ? <span className="button-spinner" /> : "이메일 전송"}
                    </button>
                    <div className="links"><span onClick={() => showInquiry('account')}>이메일이 기억나지 않나요?</span></div>
                  </form>
                </div>
              )}

              {/* [SECTION] 3. Success View: 이메일 발송 완료 결과 화면 */}
              {view === "success" && (
                <div className="login-card active" id="success-section">
                  <div className="login-logo-mark">ESG DATA PLATFORM</div>
                  <h1>이메일 발송 완료</h1>
                  <div className="success-check-wrap"><div className="success-check-icon">✓</div></div>
                  <div className="success-message-box">
                    <div className="success-message-id">{maskEmail(formData.resetEmail)}</div>
                    <div className="success-message-main">임시 비밀번호를 발송했습니다.</div>
                    <div className="success-message-sub">메일이 보이지 않는다면 스팸 메일함을 확인해 주세요.<br />로그인 확인 후 비밀번호를 변경해 주세요.</div>
                  </div>
                  <button className="login-action-button success-button" onClick={() => setView("login")}>로그인으로 돌아가기</button>
                  <div className="success-help-links">
                    <span onClick={() => { setView("forgot"); setFormData(p => ({ ...p, resetEmail: "" })); }}>이메일 다시 받기</span>
                    <span className="divider">|</span>
                    <span onClick={() => showInquiry('support')}>고객센터 문의</span>
                  </div>
                </div>
              )}

            </div>
          </section>
        </div>
      </LoginBackground>
    </div>
  );
};

export default Login;