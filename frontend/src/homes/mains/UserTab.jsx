import React from 'react';

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
  setCurrentUser,
  setIsModalOpen,
  setIsDisconnectModalOpen,
  setDisconnectTarget,
  handleDisconnectClick,
  permission,
  user,
  activeService = 'disclosure'
}) => {
  const getSRTheme = (groupName) => {
    // [공시] 섹션
    const environmental = ["Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment", "Carbon_Scope1", "Carbon_Scope2"];
    const social = ["Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy", "Supply_Audit", "협력사 평가"];
    const governance = ["Governance", "Risk", "compliance", "Ethics", "Business Conduct", "Data Governance"];

    if (environmental.includes(groupName)) return "E";
    if (social.includes(groupName)) return "S";
    if (governance.includes(groupName)) return "G";
    return "general";
  };

  const handleDisconnectClickLocal = (targetUser, type) => {
    // 부모(Manager.jsx)에서 직접 처리 함수를 내려줬다면 그걸 사용 (직접 컨펌창 방식)
    if (handleDisconnectClick) {
      handleDisconnectClick(targetUser, type);
      return;
    }

    const role = user?.role;

    if (role === "ESG담당자") {
      setDisconnectTarget(targetUser);
      setIsDisconnectModalOpen(true);
      return;
    }

    if (role === "컨설턴트") {
      showDefaultAlert("컨설턴트", "별도 로직 실행", "info");
      return;
    }

    showDefaultAlert("권한 없음", "접근 권한이 없습니다", "error");
  };
  return (
    <section className="fade-in">

      <div className="filter-bar">
        <input
          className="search-input"
          placeholder="사용자명 또는 회사명 / 이슈그룹 검색"
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
                <th>할당 이슈 그룹</th>
                <th>관리</th>
              </tr>
            </thead>

            <tbody>
              {pagedUsers.map(u => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.name}</strong><br />
                    <small>{u.email}</small>
                  </td>

                  <td>
                    {u.company}
                    <span className="depth-tag">{u.role}</span>
                  </td>

                  <td>
                    <div className="tag-container">
                      {(() => {
                        // 1. 현재 서비스에 맞는 그룹만 먼저 필터링
                        const serviceFilteredGroups = u.groups.filter(g => {
                          if (activeService === 'carbon') return ["Carbon_Scope1", "Carbon_Scope2"].includes(g);
                          if (activeService === 'supply') return ["Supply_Audit", "협력사 평가"].includes(g);
                          // disclosure (나머지 모든 공시 그룹)
                          const isCarbonOrSupply = ["Carbon_Scope1", "Carbon_Scope2", "Supply_Audit", "협력사 평가"].includes(g);
                          return !isCarbonOrSupply;
                        });

                        // 2. 필터링된 결과 중 3개만 노출
                        const displayGroups = serviceFilteredGroups.slice(0, 3);
                        const overflowCount = serviceFilteredGroups.length - displayGroups.length;

                        return (
                          <>
                            {displayGroups.map(g => (
                              <span key={g} className={`sr-ig-chip sr-theme-${getSRTheme(g)}`}>
                                {g}
                              </span>
                            ))}
                            {overflowCount > 0 && (
                              <span className="sr-ig-chip" style={{ background: '#eee', color: '#666' }}>
                                +{overflowCount}
                              </span>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </td>

                  <td>
                    <button
                      className="btn-outline"
                      onClick={() => {
                        setCurrentUser(u);
                        setIsModalOpen(true);
                      }}
                      disabled={isLoading}
                    >
                      이슈 그룹 수정
                    </button>
                    {permission.canDisconnect && (
                      <>
                        {/* 컨설턴트일 때만 */}
                        {u.role === "컨설턴트" && (
                          <button
                            className="btn-outline"
                            onClick={() => handleDisconnectClickLocal(u, "consultant")}
                            disabled={isLoading}
                          >
                            컨설턴트 연결 해제
                          </button>
                        )}

                        {/* 부서담당자일 때만 */}
                        {u.role === "부서담당자" && (
                          <button
                            className="btn-outline"
                            onClick={() => handleDisconnectClickLocal(u, "employee")}
                            disabled={isLoading}
                          >
                            직원 연결 해제
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* 페이지네이션 */}
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