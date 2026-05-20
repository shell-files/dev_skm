/**
 * Alarm.jsx - 알림 센터 사이드바 컴포넌트
 *
 * 1. 화면 흐름:
 *    - 열기/닫기: HeaderNav의 알림 아이콘 → toggleAlarm() → isAlarmOpen 상태 변경 → 슬라이딩 애니메이션
 *    - 탭 필터링: 상단 탭(All/Users/Data/Service) 클릭 → activeFilter 변경 → filteredNotifications 재계산
 *    - 읽음 처리: '알림 모두 읽음' 클릭 → handleMarkAllAsRead → 현재 탭 타입만 읽음 처리
 *    - 단건 삭제: 'x' 버튼 → removeNoti(id)
 *    - 전체 삭제: '전체 알림 비우기' 클릭 → clearAll()
 *
 * 2. 권한(Role) 필터링:
 *    - 각 알림의 targetRole을 현재 로그인 권한과 비교하여 본인 알림만 표시
 *    - TESTING_ROLE을 사용하는 경우 localStorage('onboarding_test_role')를 우선 참조
 *
 * 3. 외부 연동:
 *    - useAlarm(): notifications, removeNoti, markAllAsRead 등 AlarmContext 데이터 구독
 *    - useAuth(): user, selectedCompany 정보 (헤더 사용자명 표시용)
 *    - useNavigate(): 알림 클릭 시 관련 페이지로 이동
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useAlarm } from '@hooks/AlarmContext.jsx';
import { useAuth } from '@hooks/AuthContext.jsx';
import "@styles/alarm.css";

// ── 아이콘 에셋 임포트 (경로 수정: @assets/icons/alarm/) ──
import userIcon from '@assets/icons/alarm/user.png';
import dataIcon from '@assets/icons/alarm/data.png';
import serviceIcon from '@assets/icons/alarm/service.png';
import robotIcon from '@assets/icons/alarm/robot.png';
import alarmSettingIcon from '@assets/icons/alarm/alarmsetting.png';

// ── 알림 타입별 아이콘/색상 맵 ──
const ALARM_TYPES = {
  USER:  { icon: userIcon,    color: '#03A94D' },
  CHECK: { icon: dataIcon,    color: '#3498db' },
  CHART: { icon: serviceIcon, color: '#9b59b6' },
  LEAF:  { icon: serviceIcon, color: '#a29bfe' },
  CUBE:  { icon: serviceIcon, color: '#6c5ce7' }
};

// ── 상단 필터 탭 구성 ──
const FILTER_TABS = [
  { id: 'ALL',     label: 'All',     icon: null },
  { id: 'USER',    label: 'Users',   icon: userIcon },
  { id: 'CHECK',   label: 'Data',    icon: dataIcon },
  { id: 'SERVICE', label: 'Service', icon: serviceIcon, subTypes: ['CHART', 'LEAF', 'CUBE'] }
];

const Alarm = () => {
  // [연결] useNavigate(): 알림 클릭 시 관련 페이지 이동
  const navigate = useNavigate();

  // [연결] useAlarm(): 알림 목록과 조작 함수 구독
  const { isAlarmOpen, closeAlarm, toggleAlarm, notifications, unreadCount, isLoading, removeNoti, markAllAsRead, clearAll } = useAlarm();

  // [연결] useAuth(): 헤더에 사용자명 표시용
  const { user, selectedCompany } = useAuth();

  // [변수] activeFilter: 현재 선택된 탭 ID ('ALL' | 'USER' | 'CHECK' | 'SERVICE')
  const [activeFilter, setActiveFilter] = useState('ALL');

  // [변수] sliderStyle: 탭 하단 슬라이더 위치 및 너비 (CSS 애니메이션용)
  const tabsRef = useRef([]);
  const [sliderStyle, setSliderStyle] = useState({ left: 0, width: 0 });

  /**
   * [이펙트] 탭 변경 및 창 크기 변경 시 슬라이더 위치 재계산
   * - isAlarmOpen이 포함된 이유: 사이드바가 열릴 때 DOM이 반영된 후 위치를 다시 측정
   */
  useEffect(() => {
    const updateSlider = () => {
      const activeIndex = FILTER_TABS.findIndex(t => t.id === activeFilter);
      const activeTab = tabsRef.current[activeIndex];
      if (activeTab) setSliderStyle({ left: activeTab.offsetLeft, width: activeTab.offsetWidth });
    };
    updateSlider();
    window.addEventListener("resize", updateSlider);
    const timer = setTimeout(updateSlider, 50); // 사이드바 오픈 애니메이션 이후 보정
    return () => { window.removeEventListener("resize", updateSlider); clearTimeout(timer); };
  }, [activeFilter, isAlarmOpen]);

  /**
   * [파생값] filteredNotifications: 권한(Role) + 탭(Type) 필터 적용 후 미읽음 상단 정렬
   * - 권한 필터: localStorage의 test_role 또는 selectedCompany.role과 targetRole 비교
   */
  const filteredNotifications = notifications
    .filter(noti => {
      const testRole = localStorage.getItem('onboarding_test_role') || selectedCompany?.role || "ESG담당자";
      if (noti.targetRole && noti.targetRole !== testRole && noti.targetRole !== 'ALL') return false;
      if (activeFilter === 'ALL') return true;
      const currentFilter = FILTER_TABS.find(tab => tab.id === activeFilter);
      return currentFilter?.subTypes ? currentFilter.subTypes.includes(noti.type) : noti.type === activeFilter;
    })
    .sort((a, b) => a.isRead === b.isRead ? 0 : a.isRead ? 1 : -1);

  /**
   * [핸들러] handleMarkAllAsRead: 현재 탭의 알림들만 읽음 처리
   * - ALL 탭: 전체 읽음 (markAllAsRead(null))
   * - 개별 탭: 해당 타입만 읽음 처리
   */
  const handleMarkAllAsRead = () => {
    if (activeFilter === 'ALL') {
      markAllAsRead(null);
    } else {
      const currentFilter = FILTER_TABS.find(tab => tab.id === activeFilter);
      markAllAsRead(currentFilter?.subTypes || [activeFilter]);
    }
  };

  /**
   * [핸들러] handleNotificationClick: 알림 클릭 시 연결된 path로 이동
   */
  const handleNotificationClick = (noti) => {
    if (noti.path) { closeAlarm(); navigate(noti.path); }
  };

  /**
   * [함수] getChipFromMeta: 알림의 meta 정보를 기반으로 배지 Chip 데이터 파생
   */
  const getChipFromMeta = (noti) => {
    if (noti.chip) return noti.chip;
    if (!noti.meta) return null;
    if (noti.type === 'CHECK' && noti.meta.issueGroupCode) return { text: noti.meta.issueGroupCode, colorId: 'G' };
    if (noti.type === 'USER' && noti.meta.issueGroupCode) return { text: noti.meta.issueGroupCode, colorId: 'E' };
    return noti.meta.text ? { text: noti.meta.text, colorId: noti.meta.colorId || 'default' } : null;
  };

  /**
   * [함수] getDisplayName: 현재 역할에 맞는 표시 이름 반환 (테스트 권한 고려)
   */
  const getDisplayName = () => {
    const testRole = localStorage.getItem('onboarding_test_role');
    if (testRole === "부서 담당자") return "이부서";
    if (testRole === "컨설턴트") return "김컨설";
    return user?.name || '차성자';
  };

  return (
    <>
      {/* 오버레이: 바깥 영역 클릭 시 사이드바 닫기 */}
      <div
        id="alarm-overlay"
        onClick={e => e.target.id === 'alarm-overlay' && closeAlarm()}
        style={{ opacity: isAlarmOpen ? 1 : 0, pointerEvents: isAlarmOpen ? 'auto' : 'none' }}
      />

      <div id="alarm-container" style={{ transform: isAlarmOpen ? 'translateX(0)' : 'translateX(100%)' }}>
        {/* 1. 헤더: 제목 + 현재 사용자 정보 + 설정 아이콘 + 닫기 버튼 */}
        {/* 1. 헤더: 제목 + 현재 사용자 정보 + 설정 아이콘 + 닫기 버튼 */}
        <div id="alarm-header">
          <div className="alarm-title-box">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2>Notification Center</h2>
              <img src={alarmSettingIcon} alt="settings" className="alarm-setting-icon" onClick={() => {/* 설정 모달 열기 */}} />
            </div>
            <div className="alarm-auth-info">
              <span>{selectedCompany?.company_name || 'A회사'}</span>
              <span className="dot-sep">•</span>
              <span>{getDisplayName()}님</span>
            </div>
          </div>
          <span onClick={closeAlarm} className="alarm-close-btn">×</span>
        </div>

        {/* 2. 필터 탭: All / Users / Data / Service */}
        <div id="alarm-filter-tabs">
          <div className="alarm-tab-slider" style={sliderStyle} />
          {FILTER_TABS.map((tab, idx) => (
            <button
              key={tab.id}
              ref={el => tabsRef.current[idx] = el}
              onClick={() => setActiveFilter(tab.id)}
              className={`alarm-filter-btn ${activeFilter === tab.id ? 'active' : ''}`}
            >
              {tab.icon && <img src={tab.icon} alt="" />}
              {tab.label}
            </button>
          ))}
        </div>

        {/* 3. 액션 바: 미읽음 배지 + 전체 읽음 버튼 */}
        <div id="alarm-action-bar">
          <div className="alarm-badge-new">{unreadCount} NEW</div>
          <button className="alarm-read-all-btn" onClick={handleMarkAllAsRead}>알림 모두 읽음</button>
        </div>

        {/* 4. 알림 목록 */}
        <div id="alarm-list">
          {isLoading ? (
            <div className="alarm-empty">알림을 불러오는 중...</div>
          ) : filteredNotifications.length === 0 ? (
            <div className="alarm-empty">
              <img src={robotIcon} alt="no notifications" />
              <span>현재 알림이 없습니다. <br /> 알림이 생기면 안내해 드릴게요!</span>
            </div>
          ) : (
            filteredNotifications.map(noti => {
              const config = ALARM_TYPES[noti.type];
              const chip = getChipFromMeta(noti);
              return (
                <div
                  key={noti.id}
                  className="alarm-item"
                  onClick={() => handleNotificationClick(noti)}
                  style={{ cursor: noti.path ? 'pointer' : 'default' }}
                >
                  <div className="alarm-icon-box" style={{ backgroundColor: `${config?.color}26` }}>
                    <img src={config?.icon} alt="" />
                  </div>
                  <div className="alarm-content">
                    <div className="alarm-content-header">
                      <div className="alarm-content-title-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="alarm-content-title">{noti.title}</span>
                        {chip && (
                          <span className={`alarm-chip bg-${chip.colorId} ${/^[A-Z]\d+/.test(chip.text) ? 'type-id' : 'type-ig'}`}>
                            {chip.text}
                          </span>
                        )}
                      </div>
                      {!noti.isRead && <div className="alarm-unread-dot" />}
                    </div>
                    <span className="alarm-text">{noti.content || noti.text}</span>
                    <span className="alarm-time">{noti.time}</span>
                  </div>
                  {/* 삭제 버튼: 이벤트 전파 중단 필요 */}
                  <div className="alarm-delete-btn" onClick={e => { e.stopPropagation(); removeNoti(noti.id); }}>
                    <span>x</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* 5. 푸터: 전체 알림 비우기 */}
        <div id="alarm-footer">
          <button className="alarm-view-all-btn" onClick={clearAll}>전체 알림 비우기</button>
        </div>
      </div>
    </>
  );
};

export default Alarm;