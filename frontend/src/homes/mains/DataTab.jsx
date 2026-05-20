import React from 'react';
import TabButton from '@components/UI/TabButton';
import BatchActionBar from '@components/UI/BatchActionBar';
import "@styles/Manager.css";
import "@styles/TabButton.css";

const DataTab = ({
  activeService,
  isLoading,
  activeDataCategory,
  activeSubCategory,
  selectedIds,
  setSelectedIds,
  pagedInputs,
  totalDataPages,
  dataPage,
  userRole,
  hasConsultant,

  handleMainCategoryChange,
  setActiveSubCategory,
  toggleSelect,
  toggleSelectAll,
  handleBulkAction,
  fetchData,
  setDataPage,
  handleAction
}) => {
  const CATEGORY_MAP = {
    // [공시] 지표 그룹
    general: ["기업개요", "사업구조", "보고정보", "거버넌스개요", "전략", "정책", "이해관계자", "재무·경제가치", "투자·R&D", "생산·판매", "인증·특허"],
    environmental: [
      "Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment", // 공시
      "Carbon_Scope1", "Carbon_Scope2" // [탄소관리]
    ],
    social: [
      "Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy", // 공시
      "Supply_Audit", "협력사 평가" // [공급망 관리]
    ],
    governance: ["Governance", "Risk", "compliance", "Ethics", "Business Conduct", "Data Governance"] // 공시
  };

  return (
    <section id="datatap_page" className="fade-in">
      <div className="ob-body" style={{ padding: 0 }}>
        <div className="data-control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>

        {/* 👇 기존 그대로 유지 */}
        {/* 상단 카테고리 탭 (표준 컴포넌트 교체) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flex: 1 }}>
          <TabButton.Category 
            tabs={[
              { label: '전체', value: 'all' },
              { label: '경영일반', value: 'general' },
              { label: 'E', value: 'environmental' },
              { label: 'S', value: 'social' },
              { label: 'G', value: 'governance' }
            ]}
            activeTab={activeDataCategory}
            onTabChange={(val) => handleMainCategoryChange(val)}
            className="data-category-tabs"
          />

          {/* 일괄 처리 바를 탭 옆으로 배치 (온보딩 스타일) */}
          <BatchActionBar 
            selectedCount={selectedIds.length}
            actions={[
              // 1. 컨설턴트 전용
              ...(userRole?.includes('CONSULTANT') || userRole?.includes('컨설턴트') ? [
                { label: '선택 검토 완료', onClick: () => handleBulkAction('reviewed'), className: 'submit' }
              ] : []),
              
              // 2. ESG 담당자/관리자 전용
              ...(userRole?.includes('ESG') || userRole?.includes('관리자') || userRole?.includes('ADMIN') ? [
                { label: '최종 승인', onClick: () => handleBulkAction('approved'), className: 'submit' }
              ] : []),

              // 3. 공통
              { label: '선택 반려', onClick: () => handleBulkAction('rejected'), className: 'reject' }
            ]}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-primary" onClick={fetchData} disabled={isLoading}>
            {isLoading ? "로딩 중..." : "데이터 새로고침"}
          </button>
        </div>
      </div>

      {/* 하위 이슈그룹 탭 + 표 영역 (온보딩 스타일 wrapper 적용) */}
      <div className="ob-table-main-container" style={{ marginTop: '30px' }}>
        {activeDataCategory !== 'all' && (
          <div style={{ marginBottom: '-1px', position: 'relative', zIndex: 2 }}>
            <TabButton.Sub 
              tabs={[
                { label: '전체 그룹', value: 'all' },
                ...(() => {
                  const allGroups = CATEGORY_MAP[activeDataCategory] || [];
                  const carbonSupplyGroups = ["Carbon_Scope1", "Carbon_Scope2", "Supply_Audit", "협력사 평가"];
                  
                  if (activeService === 'carbon') {
                    return allGroups.filter(g => ["Carbon_Scope1", "Carbon_Scope2"].includes(g));
                  }
                  if (activeService === 'supply') {
                    return allGroups.filter(g => ["Supply_Audit", "협력사 평가"].includes(g));
                  }
                  // disclosure: 탄소/공급망 제외 모든 그룹
                  return allGroups.filter(g => !carbonSupplyGroups.includes(g));
                })().map(g => ({ label: g, value: g }))
              ]}
              activeTab={activeSubCategory}
              onTabChange={(val) => setActiveSubCategory(val)}
              categoryTheme={
                activeDataCategory === 'environmental' ? 'E' :
                activeDataCategory === 'social' ? 'S' :
                activeDataCategory === 'governance' ? 'G' : '경영일반'
              }
              className="data-sub-tabs"
            />
          </div>
        )}

        {/* 👇 테이블 영역 */}
        {isLoading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>데이터를 처리하고 있습니다...</p>
          </div>
        ) : (
          <div className="ob-table-wrap" style={{ borderTopLeftRadius: activeDataCategory === 'all' ? '12px' : '0' }}>
            <table className="ob-table">
            <thead>
              <tr>
                <th style={{ width: '120px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '8px' }}>
                    <input
                      type="checkbox"
                      className="ob-checkbox"
                      checked={pagedInputs.length > 0 && pagedInputs.every(i => selectedIds.includes(i.id))}
                      onChange={toggleSelectAll}
                    />
                    <span>ID</span>
                  </div>
                </th>
                <th>이슈 그룹</th>
                <th>지표명</th>
                <th>입력값</th>
                <th>첨부</th>
                <th>담당자</th>
                <th>상태</th>
                <th style={{ width: '180px' }}>관리</th>
              </tr>
            </thead>
            <tbody>
              {pagedInputs.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ padding: '80px 0', color: '#94a3b8', textAlign: 'center', background: '#fff' }}>
                    <div style={{ marginBottom: '8px', fontSize: '24px' }}>📂</div>
                    해당 조건에 맞는 데이터가 없습니다.
                  </td>
                </tr>
              ) : (
                pagedInputs.map(item => (
                <tr key={item.id} className={selectedIds.includes(item.id) ? "selected" : ""}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '8px' }}>
                      <input
                        type="checkbox"
                        className="ob-checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelect(item.id)}
                      />
                      <span style={{ fontSize: '13px', fontWeight: '600', color: '#475569' }}>
                        {item.issueId || item.id}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={`sr-ig-chip sr-theme-${item.category}`}>
                      {item.issueGroup}
                    </span>
                  </td>
                  <td className="st-left">{item.checklistQuestion || item.questionName}</td>
                  <td><strong>{item.value || '-'}</strong></td>
                  <td>{item.attachmentFile ? '📎 파일' : '-'}</td>
                  <td>{item.userName}</td>
                  <td className="cell-status">
                    {(item.status === 'PENDING' || item.status === 'SUBMITTED' || item.status === 'pending') && <span className="ob-status st-submitted">승인대기</span>}
                    {(item.status === 'REVIEWED' || item.status === 'reviewed') && <span className="ob-status st-submitted">검토완료</span>}
                    {(item.status === 'APPROVED' || item.status === 'approved') && <span className="ob-status st-approved">승인완료</span>}
                    {(item.status === 'REJECTED' || item.status === 'rejected') && <span className="ob-status st-rejected">반려</span>}
                  </td>
                  <td>
                    {/* [디버깅] 버튼이 안 나올 경우 아래 주석을 풀어 확인 가능 */}
                    {/* <div style={{fontSize:'10px', color:'#ccc'}}>{userRole} / {item.status}</div> */}

                    {/* 1. 컨설턴트/관리자 공통: 역할에 맞는 워크플로우 로직 */}
                    <div className="ob-actions">
                      {/* [컨설턴트 전용] PENDING 상태일 때 검토 완료 가능 */}
                      {(userRole?.includes('CONSULTANT') || userRole?.includes('컨설턴트')) && (item.status === 'PENDING' || item.status === 'pending') && (
                        <button className="ob-act-btn ob-act-submit" onClick={() => handleAction(item.id, 'REVIEWED')}>검토 완료</button>
                      )}

                      {/* [ESG 담당자/관리자 전용] 승인 로직 */}
                      {(userRole?.includes('ESG') || userRole?.includes('관리자')) && (
                        <>
                          {/* 2단계 워크플로우: 컨설턴트가 없으면 PENDING에서 바로 최종 승인 가능 */}
                          {!hasConsultant && (item.status === 'PENDING' || item.status === 'pending') && (
                            <button className="ob-act-btn ob-act-submit" onClick={() => handleAction(item.id, 'APPROVED')}>최종 승인</button>
                          )}
                          {/* 3단계 워크플로우: 컨설턴트가 있으면 REVIEWED 상태에서 최종 승인 가능 */}
                          {(item.status === 'REVIEWED' || item.status === 'reviewed') && (
                            <button className="ob-act-btn ob-act-submit" onClick={() => handleAction(item.id, 'APPROVED')}>최종 승인</button>
                          )}
                        </>
                      )}

                      {/* [공통] 반려 기능 (승인된 항목 제외) */}
                      {(userRole?.includes('CONSULTANT') || userRole?.includes('컨설턴트') || userRole?.includes('ESG') || userRole?.includes('관리자')) && 
                       (item.status === 'PENDING' || item.status === 'pending' || item.status === 'REVIEWED' || item.status === 'reviewed') && (
                        <button className="ob-act-btn ob-act-reject" onClick={() => handleAction(item.id, 'REJECTED')} style={{ marginLeft: '4px' }}>반려</button>
                      )}

                      {/* [컨설턴트 전용] 이미 검토한 항목 취소 기능 */}
                      {(userRole?.includes('CONSULTANT') || userRole?.includes('컨설턴트')) && (item.status === 'REVIEWED' || item.status === 'reviewed') && (
                        <button className="ob-act-btn ob-act-draft" onClick={() => handleAction(item.id, 'PENDING')}>검토 취소</button>
                      )}

                      {/* 처리 완료된 항목 되돌리기 (수정하기) */}
                      {(item.status === 'APPROVED' || item.status === 'approved' || item.status === 'REJECTED' || item.status === 'rejected') && (
                        <button 
                          className="ob-act-btn ob-act-draft" 
                          onClick={() => handleAction(item.id, 'PENDING')}
                        >
                          수정하기
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      )}
      </div>

      {/* 페이지네이션 그대로 */}
      {!isLoading && totalDataPages > 1 && (
        <div className='pagination'>
          {Array.from({ length: totalDataPages }).map((_, i) => (
            <button
              key={i}
              onClick={() => setDataPage(i + 1)}
              className={`page-btn ${dataPage === i + 1 ? 'active' : ''}`}
              style={dataPage === i + 1 ? { backgroundColor: '#03a94d', color: '#fff', border: 'none' } : {}}
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

export default DataTab;