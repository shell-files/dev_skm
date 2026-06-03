import React, { useState, useMemo } from 'react';
import TabButton from '@components/UI/TabButton';
import BatchActionBar from '@components/UI/BatchActionBar';
import Step12UiPreviewPanel from "@components/dev/Step12UiPreviewPanel";
import ApprovalDetailModal from "./modal/ApprovalDetailModal";
import { 
  STEP12_UI_FIXTURE_ENABLED, 
  mergeApprovalFixtureRows, 
  ONBOARDING_SCENARIOS, 
  APPROVAL_SCENARIOS, 
  ROLLUP_SCENARIOS 
} from "../../mocks/step12UiFixtures";
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
    general: ["기업개요", "사업구조", "보고정보", "거버넌스개요", "전략", "정책", "이해관계자", "재무·경제가치", "투자·R&D", "생산·판매", "인증·특허"],
    environmental: [
      "Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment",
      "Carbon_Scope1", "Carbon_Scope2"
    ],
    social: [
      "Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy",
      "Supply_Audit", "협력사 평가"
    ],
    governance: ["Governance", "Risk", "compliance", "Ethics", "Business Conduct", "Data Governance"]
  };

  const [previewRole, setPreviewRole] = useState("ESG 담당자");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(ONBOARDING_SCENARIOS.UNASSIGNED);
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(APPROVAL_SCENARIOS.NO_CONSULTANT);
  const [previewRollupScenario, setPreviewRollupScenario] = useState(ROLLUP_SCENARIOS.PARENT_PENDING);

  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedItemForDetail, setSelectedItemForDetail] = useState(null);

  const effectiveViewerRole = STEP12_UI_FIXTURE_ENABLED ? previewRole : (userRole || "ESG담당자");
  const isConsultant = effectiveViewerRole.includes('CONSULTANT') || effectiveViewerRole.includes('컨설턴트');

  const displayInputs = useMemo(() => {
    if (!STEP12_UI_FIXTURE_ENABLED) return pagedInputs;
    return mergeApprovalFixtureRows(pagedInputs, previewApprovalScenario);
  }, [pagedInputs, previewApprovalScenario]);

  const handleBulkReview = () => handleBulkAction('reviewed');
  const handleBulkApprove = () => handleBulkAction('approved');
  const handleBulkReject = () => handleBulkAction('rejected');

  const handleOpenApprovalDetail = (item) => {
    setSelectedItemForDetail(item);
    setIsDetailModalOpen(true);
  };

  return (
    <section id="datatap_page" className="fade-in">
      <div className="ob-body" style={{ padding: 0 }}>
        <div className="data-control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          
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

            <BatchActionBar 
              selectedCount={selectedIds.length}
              actions={[
                ...(isConsultant ? [
                  { label: '선택 검토 완료', onClick: handleBulkReview, className: 'submit' }
                ] : [
                  { label: '선택 최종 승인', onClick: handleBulkApprove, className: 'submit' }
                ]),
                { label: '선택 반려', onClick: handleBulkReject, className: 'reject' }
              ]}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-primary" onClick={fetchData} disabled={isLoading}>
              {isLoading ? "로딩 중..." : "데이터 새로고침"}
            </button>
          </div>
        </div>

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
                  <th style={{ width: '44px' }}>
                    <input
                      type="checkbox"
                      className="ob-checkbox"
                      checked={displayInputs.length > 0 && displayInputs.every(i => selectedIds.includes(i.id))}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th style={{ width: '100px' }}>Metric ID</th>
                  <th>지표명</th>
                  <th style={{ width: '100px' }}>담당자</th>
                  <th style={{ width: '80px' }}>입력 완료</th>
                  <th style={{ width: '60px' }}>누락</th>
                  <th style={{ width: '90px' }}>제출 상태</th>
                  <th style={{ width: '90px' }}>검토 상태</th>
                  <th style={{ width: '90px' }}>승인 상태</th>
                  <th style={{ width: '110px' }}>제출일</th>
                  <th style={{ width: '180px' }}>관리</th>
                </tr>
              </thead>
              <tbody>
                {displayInputs.length === 0 ? (
                  <tr>
                    <td colSpan="11" style={{ padding: '80px 0', color: '#94a3b8', textAlign: 'center', background: '#fff' }}>
                      <div style={{ marginBottom: '8px', fontSize: '24px' }}>📂</div>
                      해당 조건에 맞는 데이터가 없습니다.
                    </td>
                  </tr>
                ) : (
                  displayInputs.map(item => {
                    const isReviewed = item.reviewStatus === 'REVIEWED';
                    const canApprove = isConsultant ? false : (!hasConsultant || isReviewed);
                    
                    return (
                      <tr key={item.id} className={selectedIds.includes(item.id) ? "selected" : ""}>
                        <td>
                          <input
                            type="checkbox"
                            className="ob-checkbox"
                            checked={selectedIds.includes(item.id)}
                            onChange={() => toggleSelect(item.id)}
                          />
                        </td>
                        <td style={{ fontSize: '13px', fontWeight: '600', color: '#475569' }}>
                          {item.metricId || item.id}
                        </td>
                        <td className="st-left">{item.metricName || item.checklistQuestion}</td>
                        <td>{item.assigneeName || item.userName}</td>
                        
                        <td className="ob-completion-cell">{item.inputCompletedCount || 0}</td>
                        <td className="ob-completion-cell">{item.inputMissingCount || 0}</td>
                        
                        <td className="cell-status">
                          <span className={`ob-status ${item.submitStatus === 'SUBMITTED' ? 'st-submitted' : 'st-draft'}`}>
                            {item.submitStatus === 'SUBMITTED' ? '제출완료' : '미제출'}
                          </span>
                        </td>
                        
                        <td className="cell-status">
                          <span className={`ob-status ${item.reviewStatus === 'REVIEWED' ? 'st-approved' : 'st-draft'}`}>
                            {item.reviewStatus === 'REVIEWED' ? '검토완료' : '검토대기'}
                          </span>
                        </td>
                        
                        <td className="cell-status">
                          <span className={`ob-status ${item.approvalStatus === 'APPROVED' ? 'st-approved' : item.approvalStatus === 'REJECTED' ? 'st-rejected' : 'st-draft'}`}>
                            {item.approvalStatus === 'APPROVED' ? '승인완료' : item.approvalStatus === 'REJECTED' ? '반려' : '미승인'}
                          </span>
                        </td>
                        
                        <td>{item.submittedAt || '-'}</td>
                        
                        <td>
                          <div className="ob-actions">
                            <button className="ob-act-btn ob-act-draft ob-detail-btn" onClick={() => handleOpenApprovalDetail(item)}>상세 보기</button>
                            
                            {isConsultant ? (
                              <>
                                <button className="ob-act-btn ob-act-submit" onClick={() => handleAction(item.id, 'REVIEWED')}>검토 완료</button>
                                <button className="ob-act-btn ob-act-reject" onClick={() => handleAction(item.id, 'REJECTED')}>반려</button>
                              </>
                            ) : (
                              <>
                                <button 
                                  className="ob-act-btn ob-act-submit" 
                                  onClick={() => handleAction(item.id, 'APPROVED')}
                                  disabled={!canApprove}
                                  title={!canApprove ? '컨설턴트 검토가 완료되어야 승인할 수 있습니다.' : ''}
                                  style={!canApprove ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                                >
                                  최종 승인
                                </button>
                                <button className="ob-act-btn ob-act-reject" onClick={() => handleAction(item.id, 'REJECTED')}>반려</button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
        </div>

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

      <ApprovalDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        metricItem={selectedItemForDetail}
        viewerRole={effectiveViewerRole}
        onReview={(id) => { handleAction(id, 'REVIEWED'); setIsDetailModalOpen(false); }}
        onApprove={(id) => { handleAction(id, 'APPROVED'); setIsDetailModalOpen(false); }}
        onReject={(id, reason) => { handleAction(id, 'REJECTED'); setIsDetailModalOpen(false); }}
      />

      <Step12UiPreviewPanel
        role={previewRole}
        onboardingScenario={previewOnboardingScenario}
        approvalScenario={previewApprovalScenario}
        rollupScenario={previewRollupScenario}
        onRoleChange={setPreviewRole}
        onOnboardingScenarioChange={setPreviewOnboardingScenario}
        onApprovalScenarioChange={setPreviewApprovalScenario}
        onRollupScenarioChange={setPreviewRollupScenario}
      />
    </section>
  );
};

export default DataTab;