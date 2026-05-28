/**
 * Mypage.jsx 페이지 구조 및 가이드
 * 
 * 1. 상태(State) 구성:
 *    - userData: 현재 사용자의 기본 정보 (이름, 이메일, 역할)
 *    - editForm: 개인 정보 수정을 위한 입력 데이터 통합 관리 (이름만 편집 가능)
 *    - passwordForm: 비밀번호 변경을 위한 입력 데이터 통합 관리
 *    - modal: 현재 활성화된 모달 상태 및 후속 액션 관리
 *    - isEditMode: 인라인 편집 모드 활성화 여부
 * 
 * 2. 주요 로직 흐름:
 *    - 정보 수정: 수정 버튼 클릭 -> 본인 확인 모달 -> 성공 시 isEditMode 전환 -> 저장 시 requestApi.updateProfile 호출
 *    - 비번 변경: 변경 버튼 클릭 -> 본인 확인 모달 -> 성공 시 비번 변경 모달 -> 저장 시 requestApi.changePassword 호출
 *    - 회원 탈퇴: 탈퇴 버튼 클릭 -> 최종 확인 알럿 -> 본인 확인 모달 -> 성공 시 requestApi.deleteAccount 호출
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@hooks/AuthContext.jsx';
import { GET, POST, PUT, PATCH, DELETE} from '@utils/Network';
import { showDefaultAlert, showConfirmAlert } from '@components/UI/ServiceAlert';
import '@styles/mypage.css';

// ── API 설정 ──
const USE_DUMMY_API = false;

// ── requestApi: 회원 정보 관련 통신 함수 모음 ──
const requestApi = {
  /** 
   * 1. updateProfile: 개인 정보 수정 (PATCH /user)
   * @param {string} name - 변경할 사용자 이름
   * @param {string} uuid - 사용자 식별자
  */
 updateProfile: async (name) => {
   if (USE_DUMMY_API) {
     await new Promise(r => setTimeout(r, 600));
     return { status: true, message: "회원 정보가 수정되었습니다." };
    }
    try {
      const res = await PATCH("/user", {  name });
      return { status: res.data.status, message: res.data.message };
    } catch (e) {
      return { status: false, message: e.response?.data?.message || "정보 수정 중 오류가 발생했습니다." };
    }
  },

  /** 
   * 2. changePassword: 비밀번호 변경 (PATCH /user)
   * @param {object} passwords - 새 비밀번호 객체
   * @param {string} uuid - 사용자 식별자
  */
 changePassword: async (passwords) => {
   if (USE_DUMMY_API) {
     await new Promise(r => setTimeout(r, 600));
     return { status: true, message: "비밀번호 변경 완료" };
    }
    try {
      const res = await PATCH("/user", { 
        newPassword: passwords.new, 
        newPasswordConfirm: passwords.confirm 
      });
      return { status: true, message: "비밀번호 변경 완료" };
    } catch (e) {
      return { status: false, message: e.response?.data?.message || "비밀번호 변경 중 오류가 발생했습니다." };
    }
  },
  
  /** 
   * 3. deleteAccount: 회원 탈퇴 (DELETE /user)
   * @param {string} uuid - 사용자 식별자
   */
  deleteAccount: async () => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 800));
      return { status: true, message: "탈퇴 완료" };
    }
    try {
      const res = await api.delete("/user", { data: {  } });
      return { status: true, message: "탈퇴 처리 완료" };
    } catch (e) {
      return { status: false, message: e.response?.data?.message || "탈퇴 처리 중 오류가 발생했습니다." };
    }
  },
  
  /** 4. checkPassword: 본인 확인용 비밀번호 체크 */
  checkPassword: async (password) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 400));
      return password === '1234' ? { status: true } : { status: false, message: "비밀번호가 일치하지 않습니다." };
    }
    try {
      const res = await PATCH("/auth", { password });
      console.log("=== API 응답 확인 ===", res); // 이걸로 데이터 구조를 먼저 확인하세요!
      
      const status = res.data?.status ?? res.status; 
      
      if (status) {
        return { status: true, data: res.data || res };
      }
      return { status: false, message: "비밀번호가 일치하지 않습니다." };
    } catch (e) {
      return { status: false, message: "오류 발생" };
    }
}
  };
  
  const Mypage = () => {
  const navigate = useNavigate();
  const { user, userName, selectedCompany, companies, isAuthReady, logout, handleLogout, toggleSidebarMobile, goHome, goMyPage, openAlarmCenter } = useAuth();

  // ── States ──

  // [데이터] 사용자 기본 정보 (이메일 고정)
  const [userData, setUserData] = useState({
    name: userName || '사용자',
    email: user?.email || selectedCompany?.email || '-',
    role: selectedCompany?.role
  });

  // [편집] 정보 수정 및 비밀번호 양식
  const [editForm, setEditForm] = useState({ name: '' });
  const [passwordForm, setPasswordForm] = useState({ new: '', confirm: '', current: '' });
  const [isEditMode, setIsEditMode] = useState(false);

  // [모달] 활성 모달 및 상태 메시지
  const [modal, setModal] = useState({ active: null, nextAction: null, error: '' });
  const [loading, setLoading] = useState(false);
  const authData = useAuth();
  useEffect(() => {
    if (isAuthReady) console.log(userName, selectedCompany, companies);
    console.log(userData.name)
    // --- 여기 추가 ---
    console.log("=== 지금 보내려는 user 객체 내용 ===", authData);
    setUserData({
      name: userName || '사용자',
      email: user?.email || selectedCompany?.email || '-',
      role: selectedCompany?.role_name 
    });
  }, [user, selectedCompany]);

  // ── Handlers ──

  /** [모달 제어] 모달 닫기 및 초기화 */
  const closeModal = () => {
    setModal({ active: null, nextAction: null, error: '' });
    setPasswordForm(p => ({ ...p, current: '', new: '', confirm: '' }));
  };

  /** [본인 확인] 각 액션 전 인증 절차 시작 */
  const startVerifyFlow = (action) => {
    setModal({ active: 'verify', nextAction: action, error: '' });
    setPasswordForm(p => ({ ...p, current: '' }));
  };

  /** [인증 승인] 본인 확인 성공 시 후속 작업 연결 */
  const handleVerifySubmit = async (e) => {
    if (e) e.preventDefault();
    
    if (!passwordForm.current) {
      setModal(p => ({ ...p, error: '현재 비밀번호를 입력해주세요.' }));
      return;
    }

    try {
      setLoading(true);
      const res = await requestApi.checkPassword(passwordForm.current, userData.email);
      if (res.status) {
        const action = modal.nextAction;
        if (action === 'edit') {
          setIsEditMode(true);
          setEditForm({ name: userData.name });
          closeModal();
        } else if (action === 'password') {
          setModal(p => ({ ...p, active: 'password', error: '' }));
        } else if (action === 'delete') {
          handleDeleteAccount();
        }
      } else {
        setModal(p => ({ ...p, error: res.message || '비밀번호가 일치하지 않습니다.' }));
      }
    } catch (err) {
      setModal(p => ({ ...p, error: '인증 중 오류가 발생했습니다.' }));
    } finally {
      setLoading(false);
    }
  };

  /** [액션: 정보 저장] 이름 수정 API 호출 */
  const handleSaveProfile = async () => {
    if (!editForm.name.trim()) {
      showDefaultAlert('오류', '이름을 입력해주세요.', 'error');
      return;
    }
    try {
      setLoading(true);
      const res = await requestApi.updateProfile(editForm.name);
      if (res.status) {
        setUserData(p => ({ ...p, name: editForm.name }));
        setIsEditMode(false);
        showDefaultAlert('수정 완료', res.message || '회원 정보가 수정되었습니다.', 'success');
      } else {
        showDefaultAlert('수정 실패', res.message || '오류가 발생했습니다.', 'error');
      }
    } finally { setLoading(false); }
  };

  /** [액션: 비번 변경] */
  const handleSavePassword = async (e) => {
    if (e) e.preventDefault();
    if (!passwordForm.new || passwordForm.new !== passwordForm.confirm) {
      setModal(p => ({ ...p, error: '새 비밀번호가 일치하지 않습니다.' }));
      return;
    }
    try {
      setLoading(true);
      const res = await requestApi.changePassword(passwordForm);
      if (res.status) {
        closeModal();
        showDefaultAlert('변경 완료', res.message || '비밀번호가 성공적으로 변경되었습니다.', 'success');
      } else {
        setModal(p => ({ ...p, error: res.message || '변경 중 오류 발생' }));
      }
    } finally { setLoading(false); }
  };

  /** [액션: 회원 탈퇴] */
  const handleDeleteAccount = async () => {
    try {
      setLoading(true);
      const res = await requestApi.deleteAccount(user?.uuid);
      if (res.status) {
        closeModal();
        showDefaultAlert('탈퇴 완료', '정상적으로 처리되었습니다. 초기 화면으로 이동합니다.', 'success');
        setTimeout(() => { logout(); navigate('/login'); }, 1500);
      } else {
        showDefaultAlert('탈퇴 실패', res.message || '오류가 발생했습니다.', 'error');
      }
    } catch (err) {
      showDefaultAlert('오류', '탈퇴 처리 중 문제가 발생했습니다.', 'error');
    } finally { setLoading(false); }
  };

  /** [탈퇴 확인] 첫 단계 알럿 */
  const confirmDeleteFlow = async () => {
    const ok = await showConfirmAlert('회원 탈퇴', '정말로 탈퇴하시겠습니까?<br/>보안을 위해 본인 확인이 진행됩니다.', 'warning');
    if (ok) startVerifyFlow('delete');
  };

  // ── Render Helpers ──

  /** 네이버 스타일 정보 행 렌더러 */
  const renderInfoRow = (label, valueKey, type = 'text', isReadOnly = false) => {
    const isEditingThis = isEditMode && !isReadOnly;
    return (
      <div className={`info-item-row ${isEditingThis ? 'editing' : ''} ${isReadOnly ? 'readonly' : ''}`}>
        <label>{label}</label>
        <div className="row-content">
          {isEditingThis ? (
            <input 
              type={type} 
              value={editForm[valueKey]}
              onChange={e => setEditForm(p => ({ ...p, [valueKey]: e.target.value }))}
              className="inline-input-field"
              autoFocus
            />
          ) : (
            <span className="value-text">{userData[valueKey]}</span>
          )}
        </div>
        {!isEditMode && !isReadOnly && (
          <button className="btn-inline-edit" onClick={() => startVerifyFlow('edit')}>수정</button>
        )}
        {isReadOnly && <div className="row-placeholder" />}
      </div>
    );
  };

  return (
    <div id="mypage_page">
      <div className="mypage-compact-container">
        
        {/* ── [SECTION] 1. 내 프로필 ── */}
        <section className="compact-hero-section">
          <div className="section-title"><i></i>내 프로필</div>
          <div className="compact-hero-card">
            <div className="hero-left">
              <div className="hero-profile-main">
                <div className="hero-avatar">{userData.name.charAt(0)}</div>
                <div className="hero-welcome">
                  <h1>{userData.name}님, 반갑습니다!</h1>
                  <p className="hero-subtitle">안전한 서비스 이용을 위해 정보를 관리하세요.</p>
                </div>
              </div>
            </div>

            <div className="hero-right">
              <div className="hero-top-actions">
                {isEditMode && (
                  <div className="edit-actions-wrap">
                    <button className="btn-save-primary" onClick={handleSaveProfile} disabled={loading}>
                      {loading ? '저장 중...' : '저장하기'}
                    </button>
                    <button className="btn-cancel-secondary" onClick={() => setIsEditMode(false)}>취소</button>
                  </div>
                )}
              </div>

              <div className="hero-bottom-info">
                <div className="naver-style-info-box">
                  {renderInfoRow('로그인 계정', 'email', 'email', true)} {/* 이메일은 읽기 전용으로 변경 */}
                  {renderInfoRow('사용자 이름', 'name')}
                  {renderInfoRow('현재 역할', 'role', 'text', true)}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── [SECTION] 2. 보안 센터 ── */}
        <section className="compact-security-section">
          <div className="section-title"><i></i>보안 센터</div>
          <div className="security-card-flat">
            <div className="security-row">
              <div className="row-text">
                <label>계정 비밀번호</label>
                <p>주기적인 비밀번호 변경으로 계정을 안전하게 보호하세요.</p>
              </div>
              <button className="btn-row-action" onClick={() => startVerifyFlow('password')}>변경하기</button>
            </div>
            <div className="security-row danger-row">
              <div className="row-text">
                <label>계정 관리</label>
                <p>탈퇴 시 계정의 모든 정보가 영구 삭제됩니다.</p>
              </div>
              <button className="btn-row-danger" onClick={confirmDeleteFlow}>회원 탈퇴</button>
            </div>
          </div>
        </section>

      </div>

      {/* ── [MODAL] 본인 확인 ── */}
      {modal.active === 'verify' && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeModal()}>
          <div className="modal-content bento-modal">
            <div className="modal-header">
              <h3>본인 확인</h3>
              <p>보안을 위해 현재 비밀번호를 입력해 주세요.</p>
            </div>
            <form className="modal-body" onSubmit={handleVerifySubmit}>
              <input
                type="password"
                placeholder="현재 비밀번호"
                className="modal-input"
                value={passwordForm.current}
                onChange={e => setPasswordForm(p => ({ ...p, current: e.target.value }))}
                autoFocus
              />
              {modal.error && <p className="modal-error">{modal.error}</p>}
              <div className="modal-btns">
                <button type="submit" className="btn-confirm">확인</button>
                <button type="button" className="btn-close" onClick={closeModal}>취소</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── [MODAL] 비밀번호 변경 ── */}
      {modal.active === 'password' && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeModal()}>
          <div className="modal-content bento-modal">
            <div className="modal-header">
              <h3>비밀번호 변경</h3>
              <p>새로 사용할 비밀번호를 설정해 주세요.</p>
            </div>
            <form className="modal-body" onSubmit={handleSavePassword}>
              <div className="modal-input-group">
                <label>새 비밀번호</label>
                <input
                  type="password"
                  className="modal-input"
                  value={passwordForm.new}
                  onChange={e => setPasswordForm(p => ({ ...p, new: e.target.value }))}
                  autoFocus
                />
              </div>
              <div className="modal-input-group">
                <label>새 비밀번호 확인</label>
                <input
                  type="password"
                  className="modal-input"
                  value={passwordForm.confirm}
                  onChange={e => setPasswordForm(p => ({ ...p, confirm: e.target.value }))}
                />
              </div>
              {modal.error && <p className="modal-error">{modal.error}</p>}
              <div className="modal-btns">
                <button type="submit" className="btn-confirm" disabled={loading}>
                  {loading ? '처리 중...' : '변경 완료'}
                </button>
                <button type="button" className="btn-close" onClick={closeModal}>취소</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Mypage;