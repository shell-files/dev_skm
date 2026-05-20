/**
 * AlarmContext.jsx - 전역 알림 상태 관리 컨텍스트
 *
 * 1. 데이터 구조:
 *    - notifications: 현재 알림 목록 (id, type, title, content, isRead, targetRole 등)
 *    - unreadCount: 읽지 않은 알림 수 (파생값)
 *    - isAlarmOpen: 알림 사이드바 오픈 여부
 *
 * 2. 주요 기능 흐름:
 *    - 초기 로드: useEffect → USE_DUMMY_API 분기 → 더미 데이터 or REST API 호출
 *    - 실시간 수신: WebSocket(STOMP) 연결 → /user/queue/notifications 구독 → addNotification 호출
 *    - 수동 추가: Onboarding.jsx 등 내부 컴포넌트에서 sendNoti → addNotification 호출
 *    - 조작: removeNoti(삭제), markAllAsRead(읽음처리), clearAll(전체 비우기)
 *
 * 3. 외부 연동:
 *    - Alarm.jsx: 알림 목록과 조작 함수를 useAlarm()을 통해 구독
 *    - Onboarding.jsx: addNotification()을 통해 데이터 이벤트 알림 발송
 *    - AuthContext.jsx: user, selectedCompany를 참조하여 알림 범위 결정
 *
 * 4. 실서버 전환:
 *    - USE_DUMMY_API = false로 변경
 *    - STOMP 구독 블록 주석 해제 및 brokerURL 수정
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import { useAuth } from '@hooks/AuthContext.jsx';
// import { api } from '@utils/network.js';
// import * as StompJs from '@stomp/stompjs'; // 실시간 알림 연동 시 주석 해제

const AlarmContext = createContext();

// ── API 설정 ──
// USE_DUMMY_API: true일 경우 더미 알림 데이터를 사용합니다. 실서버 전환 시 false로 변경.
const USE_DUMMY_API = false;

// ── 더미 알림 데이터 (API 응답과 동일한 구조) ──
const DUMMY_NOTIFICATIONS = [
  {
    id: 1,
    type: 'USER',
    title: '담당자 초대 수신',
    content: 'ESG 담당자님으로부터 Onboarding 프로젝트 초대를 받았습니다.',
    time: '2 mins ago',
    isRead: false,
    targetRole: '부서 담당자'
  },
  {
    id: 2,
    type: 'CHECK',
    title: '데이터 검토 요청',
    content: '신규 데이터가 제출되어 검토 대기 중입니다.',
    time: '1 hour ago',
    isRead: false,
    meta: { text: 'G2-03', colorId: 'G' },
    targetRole: 'ESG담당자'
  },
  {
    id: 3,
    type: 'CHART',
    title: '분석 리포트 완료',
    content: '2025년 1분기 ESG 성과 분석 리포트 생성이 완료되었습니다.',
    time: '3 hours ago',
    isRead: false,
    targetRole: 'ESG담당자'
  },
  {
    id: 4,
    type: 'USER',
    title: '시스템 업데이트',
    content: '온실가스 배출량 산정 모듈이 업데이트 되었습니다.',
    time: 'Yesterday',
    isRead: true,
    targetRole: 'ESG담당자'
  },
  {
    id: 5,
    type: 'USER',
    title: '신규 기능 안내',
    content: '담당자 일괄 지정 및 알림 필터링 기능이 새롭게 추가되었습니다.',
    time: '2 days ago',
    isRead: true,
    targetRole: 'ALL'
  }
];

export const AlarmProvider = ({ children }) => {
  // [연결] useAuth(): 알림 범위 결정에 사용 (user, selectedCompany)
  const { user, selectedCompany } = useAuth();

  // [변수] isAlarmOpen: 사이드바 열림/닫힘 상태 (Alarm.jsx에서 구독)
  const [isAlarmOpen, setIsAlarmOpen] = useState(false);

  // [변수] isLoading: 알림 최초 로드 중 여부 (Alarm.jsx에서 로딩 UI 표시용)
  const [isLoading, setIsLoading] = useState(false);

  // [변수] notifications: 전체 알림 목록 (여기에 추가/삭제/읽음 처리가 반영됨)
  const [notifications, setNotifications] = useState([]);

  // [함수] toggleAlarm / closeAlarm: 사이드바 열기/닫기
  const toggleAlarm = () => setIsAlarmOpen(prev => !prev);
  const closeAlarm = () => setIsAlarmOpen(false);

  /**
   * [이펙트] 알림 초기 로드
   * - USE_DUMMY_API: true → DUMMY_NOTIFICATIONS 로드 (500ms 딜레이)
   * - USE_DUMMY_API: false → GET /alarm API 호출
   * - user 또는 selectedCompany가 없으면 알림 목록 초기화
   */
  useEffect(() => {
    if (USE_DUMMY_API) {
      setIsLoading(true);
      const timer = setTimeout(() => {
        setNotifications(DUMMY_NOTIFICATIONS);
        setIsLoading(false);
      }, 500);
      return () => clearTimeout(timer);
    }

    if (!user || !selectedCompany) {
      setNotifications([]);
      return;
    }

    const fetchNotifications = async () => {
      // setIsLoading(true);
      try {
        const res = await api.get('/alarm');
        setNotifications(res.data.data.notifications || []);
      } catch (err) {
        console.error("알림 로드 실패", err);
      } finally {
        setIsLoading(false);
      }
    };
    // fetchNotifications();
  }, [user, selectedCompany]);

  /**
   * [이펙트] WebSocket(STOMP) 실시간 알림 구독
   * - USE_DUMMY_API = false이고 user/selectedCompany가 있을 때만 활성화
   * - 연결 시 아래 블록 주석 해제 및 brokerURL 수정 필요
   */
  useEffect(() => {
    if (!user || !selectedCompany || USE_DUMMY_API) return;

    /* [STOMP 연결 가이드]
     * 1. 상단 StompJs import 주석을 해제하세요.
     * 2. brokerURL을 실제 백엔드 WebSocket 주소로 변경하세요.
     * 3. network.js의 인증 헤더 구성을 참고하세요.

    const client = new StompJs.Client({
      brokerURL: `${import.meta.env.VITE_WS_URL}/alarm`,
      connectHeaders: {
        Authorization: `Bearer ${localStorage.getItem("uuid")}`,
        company_id: String(selectedCompany.company_id),
      },
      onConnect: () => {
        client.subscribe('/user/queue/notifications', (message) => {
          const payload = JSON.parse(message.body);
          if (Number(payload.companyId) === Number(selectedCompany.company_id)) {
            addNotification(payload);
          }
        });
      },
      onStompError: (frame) => console.error('STOMP Error:', frame),
    });
    client.activate();
    return () => client.deactivate();
    */
  }, [user, selectedCompany]);

  /**
   * [함수] addNotification: 새 알림을 목록 최상단에 추가
   * - Onboarding.jsx의 sendNoti() → addNotification() 흐름으로 호출됨
   * - STOMP 수신 시에도 동일하게 호출
   */
  const addNotification = (notiObj) => {
    const newNoti = {
      id: notiObj.id || Date.now(),
      type: notiObj.type || 'USER',
      title: notiObj.title || '알림',
      content: notiObj.content || '',
      time: notiObj.time || 'Just now',
      isRead: false,
      path: notiObj.path || null,
      meta: notiObj.meta || {},
      targetRole: notiObj.targetRole || null
    };
    setNotifications(prev => [newNoti, ...prev]);
  };

  /**
   * [함수] removeNoti: 특정 알림 삭제
   * - [연결] DELETE /alarm/:id
   */
  const removeNoti = async (idToRemove) => {
    if (USE_DUMMY_API) {
      setNotifications(prev => prev.filter(n => n.id !== idToRemove));
      return;
    }
    try {
      const res = await api.delete(`/alarm/${idToRemove}`);
      if (res.data.data.notifications) {
        setNotifications(res.data.data.notifications);
      } else {
        setNotifications(prev => prev.filter(n => n.id !== idToRemove));
      }
    } catch (err) {
      console.error("알림 삭제 실패", err);
    }
  };

  /**
   * [함수] markAllAsRead: 현재 탭의 알림을 읽음 처리
   * @param {string[]|null} types - 읽음 처리할 type 배열, null이면 전체
   * - [연결] PATCH /alarm { types }
   */
  const markAllAsRead = async (types = null) => {
    if (USE_DUMMY_API) {
      setNotifications(prev => prev.map(n =>
        types === null || types.includes(n.type) ? { ...n, isRead: true } : n
      ));
      return;
    }
    try {
      const res = await api.patch('/alarm', { types });
      setNotifications(res.data.data.notifications || []);
    } catch (err) {
      console.error("읽음 처리 실패", err);
    }
  };

  /**
   * [함수] clearAll: 전체 알림 비우기
   * - [연결] DELETE /alarm
   */
  const clearAll = async () => {
    if (USE_DUMMY_API) {
      setNotifications([]);
      return;
    }
    try {
      await api.delete('/alarm');
      setNotifications([]);
    } catch (err) {
      console.error("전체 삭제 실패", err);
    }
  };

  // [파생값] unreadCount: 읽지 않은 알림 수 (배지 표시용)
  const unreadCount = notifications.filter(n => !n.isRead).length;

  return (
    <AlarmContext.Provider value={{
      isAlarmOpen, toggleAlarm, closeAlarm,
      notifications, unreadCount, isLoading,
      addNotification, removeNoti, markAllAsRead, clearAll
    }}>
      {children}
    </AlarmContext.Provider>
  );
};

/**
 * [훅] useAlarm: AlarmContext를 편리하게 사용하기 위한 커스텀 훅
 * - AlarmProvider 외부에서 사용 시 에러를 발생시킵니다.
 */
export const useAlarm = () => {
  const context = useContext(AlarmContext);
  if (!context) throw new Error("useAlarm은 AlarmProvider 내부에서만 사용할 수 있습니다.");
  return context;
};