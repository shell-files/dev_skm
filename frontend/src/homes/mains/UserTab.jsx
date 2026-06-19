/**
 * UserTab.jsx
 * 레이어: Component (mains)
 * 역할: Manager 페이지의 사용자 관리 탭 — 사용자 검색·목록 테이블 렌더링, 역할·연결 상태·담당 영역 표시, 개별 관리 모달 진입을 담당
 *
 * Props:
 *   isLoading — 데이터 로딩 여부
 *   userSearch — 검색 키워드
 *   setUserSearch — 검색어 상태 업데이트 함수
 *   fetchData — 사용자 목록 새로고침 핸들러
 *   pagedUsers — 현재 페이지에 표시할 사용자 배열
 *   filteredUsers — 검색 필터 적용된 전체 사용자 배열 (페이지네이션 계산용)
 *   PAGE_SIZE — 페이지당 표시 건수
 *   userPage — 현재 페이지 번호
 *   setUserPage — 페이지 번호 업데이트 함수
 *   onOpenUserManagement — 사용자 관리 모달 열기 핸들러
 */
import React, { useState } from 'react';

const UserTab = ({
  isLoading,
  userSearch,
  setUserSearch,
  fetchData,
  pagedUsers,
  filteredUsers,
  PAGE_SIZE,
  userPage,
  setUserPage,
  onOpenUserManagement,
}) => {
  const getConnectionStatus = (u) => {
    if (u.role === '컨설턴트' || u.role === 'CONSULTANT') return '컨설턴트 연결';
    if (u.role === '관리자' || u.role === 'ADMIN' || u.role === 'ESG_MANAGER') return '정상 연결';
    if (u.role === 'ESG담당자') return '정상 연결';
    if (u.role === '부서담당자' || u.role === 'EMPLOYEE' || u.role === 'ASSIGNEE') return '부서 연결';
    return '미확인';
  };

  const getConnectionCls = (status) => {
    if (status.includes('정상') || status.includes('컨설턴트') || status.includes('부서')) return 'connected';
    return 'unknown';
  };

  const getRoleLabel = (u) => {
    const roleMap = {
      '관리자': '관리자',
      'ADMIN': '관리자',
      'ESG담당자': 'ESG 담당자',
      'ESG_MANAGER': 'ESG 담당자',
      '컨설턴트': '컨설턴트',
      'CONSULTANT': '컨설턴트',
      '부서담당자': '부서담당자',
      'EMPLOYEE': '부서담당자',
      'ASSIGNEE': '부서담당자',
    };
    return roleMap[u.role] || u.role || '-';
  };

  return (
    <section className="fade-in">
      <div className="filter-bar">
        <input
          className="search-input"
          placeholder="사용자명 또는 회사명 검색"
          value={userSearch}
          onChange={(e) => setUserSearch(e.target.value)}
          disabled={isLoading}
        />
        <button className="btn-primary" onClick={fetchData} disabled={isLoading}>
          조회
        </button>
      </div>

      <div className="table-wrapper">
        {isLoading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>사용자 데이터를 불러오는 중...</p>
          </div>
        ) : pagedUsers.length === 0 ? (
          <div className="empty-container">
            <p>조회된 사용자가 없습니다.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>사용자 정보</th>
                <th>소속 회사</th>
                <th>역할</th>
                <th>할당 프로젝트·담당 영역</th>
                <th>연결 상태</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {pagedUsers.map(u => {
                const connStatus = getConnectionStatus(u);
                const connCls = getConnectionCls(connStatus);
                const scopes = u.assignmentScopes || [];
                return (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.name}</strong><br />
                      <small>{u.email}</small>
                    </td>
                    <td>{u.company}</td>
                    <td>
                      <span className="depth-tag">{getRoleLabel(u)}</span>
                    </td>
                    <td>
                      <div className="tag-container">
                        {scopes.length > 0 ? (
                          <>
                            {scopes.slice(0, 1).map((scope, idx) => (
                              <div key={idx} style={{ fontSize: '13px', lineHeight: 1.5 }}>
                                <span style={{ fontWeight: 600, color: '#1e293b' }}>
                                  {scope.projectName}
                                </span>
                                <br />
                                <span style={{ color: '#64748b', fontSize: '12px' }}>
                                  {scope.assignedSubIssues?.slice(0, 2).join(' · ')}
                                  {scope.assignedSubIssues?.length > 2 && ` 외 ${scope.assignedSubIssues.length - 2}개`}
                                </span>
                                <br />
                                <span style={{ color: '#94a3b8', fontSize: '11px' }}>
                                  담당 metric {scope.assignedMetricCount}개
                                </span>
                              </div>
                            ))}
                            {scopes.length > 1 && (
                              <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                                +{scopes.length - 1} 프로젝트
                              </span>
                            )}
                          </>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '13px' }}>할당 없음</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`ob1-status-pill ${connCls}`} style={{
                        fontSize: '12px',
                        padding: '3px 10px',
                        borderRadius: '12px',
                        background: connCls === 'connected' ? '#dcfce7' : '#f1f5f9',
                        color: connCls === 'connected' ? '#16a34a' : '#94a3b8',
                      }}>
                        {connStatus}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn-outline"
                        onClick={() => onOpenUserManagement?.(u)}
                        disabled={isLoading}
                      >
                        관리
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {!isLoading && Math.ceil(filteredUsers.length / PAGE_SIZE) > 1 && (
          <div className='pagination'>
            {Array.from({ length: Math.ceil(filteredUsers.length / PAGE_SIZE) }).map((_, i) => (
              <button
                key={i}
                onClick={() => setUserPage(i + 1)}
                className={`page-btn ${userPage === i + 1 ? 'active' : ''}`}
                style={
                  userPage === i + 1
                    ? { backgroundColor: '#03a94d', color: '#fff', border: 'none' }
                    : {}
                }
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

export default UserTab;