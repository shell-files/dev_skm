import React, { useMemo, useState, useEffect, useCallback } from 'react';
// import { GET } from '@utils/Network';
import '@styles/Manager.css';
import Invite from './Invite.jsx'
import UserTab from './UserTab';
import DataTab from './DataTab.jsx'
import TabButton from '@components/UI/TabButton';
import { showDefaultAlert, showConfirmAlert } from '@components/UI/ServiceAlert';
import { useAuth } from '@hooks/AuthContext'
import INITIAL_METRICS from '@assets/data/onboardingData';
import ServiceTabs from '@components/UI/ServiceTabs';

/**
 * [CONFIG]
 *  true: mock 데이터
 *  false: 실제 API
 */
const USE_DUMMY_API = true;

/**
 * [CONSTANTS]
 */
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

const AllIssueGroups = [
  ...CATEGORY_MAP.general,
  ...CATEGORY_MAP.environmental,
  ...CATEGORY_MAP.social,
  ...CATEGORY_MAP.governance
];
const mockUsers = [
  // SKM 팀
  { id: 1, name: '이채훈', email: 'chaehoon@skm.com', company: 'SKM', role: '컨설턴트', deleteYn: "N", relations: { consultant: true, employee: false }, groups: AllIssueGroups },
  { id: 2, name: '김하영', email: 'hayoung@skm.com', company: 'SKM', role: '부서담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Water', 'Waste'] },
  { id: 3, name: '이정빈', email: 'jungbin@skm.com', company: 'SKM', role: '관리자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: AllIssueGroups },
  { id: 4, name: '최수아', email: 'sua@skm.com', company: 'SKM', role: 'ESG담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Governance', 'Tax'] },

  // HG 팀
  { id: 5, name: '김지환', email: 'jihwan@hg.com', company: 'HG', role: '부서담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: AllIssueGroups },
  { id: 6, name: '조윤주', email: 'yunju@hg.com', company: 'HG', role: '부서담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Social', 'Community'] },
  { id: 7, name: '최가영', email: 'gayoung@hg.com', company: 'HG', role: 'ESG담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Biodiversity', 'Circular Economy'] },
  { id: 8, name: '최윤우', email: 'yunu@hg.com', company: 'HG', role: '컨설턴트', deleteYn: "N", relations: { consultant: true, employee: false }, groups: ['Waste', 'Greenhouse Gas'] },

  // TV 팀
  { id: 9, name: '남영준', email: 'youngjun@tv.com', company: 'TV', role: '부서담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Human Rights', 'Diversity'] },
  { id: 10, name: '이나라', email: 'nara@tv.com', company: 'TV', role: '컨설턴트', deleteYn: "N", relations: { consultant: true, employee: false }, groups: AllIssueGroups },
  { id: 11, name: '이현서', email: 'hyunseo@tv.com', company: 'TV', role: 'ESG담당자', deleteYn: "N", relations: { consultant: false, employee: true }, groups: ['Supply Chain', 'Data Privacy'] },

  // MT (강사님)
  { id: 12, name: '강사님', email: 'mentor@mt.com', company: 'MT', role: '컨설턴트', deleteYn: "N", relations: { consultant: true, employee: false }, groups: AllIssueGroups },
];

// 각 이슈그룹별로 최소 1개 이상의 지표를 샘플링하여 더미 데이터 생성
const getSamplingData = () => {
  const groups = {};
  INITIAL_METRICS.forEach(m => {
    // 서비스별/이슈그룹별로 각각 샘플링하여 데이터가 섞이지 않게 함
    const key = `${m.service || 'disclosure'}_${m.issueGroup}`;
    if (!groups[key]) {
      groups[key] = m;
    }
  });
  return Object.values(groups);
};

const mockInputs = getSamplingData().map((m) => {
  const statuses = ['PENDING', 'REVIEWED', 'APPROVED', 'REJECTED'];
  const status = statuses[Math.floor(Math.random() * statuses.length)];
  return {
    ...m,
    id: m.issueId,
    userName: Math.random() > 0.6 ? '이채훈' : Math.random() > 0.3 ? '김하영' : '이나라',
    status: status,
    value: m.unit !== '-' ? `${Math.floor(Math.random() * 500) + 100} ${m.unit}` : '증빙 완료',
    attachmentFile: Math.random() > 0.5 ? 'onboarding_evidence.pdf' : null
  };
});
console.log("[Manager] Data Unified with valid workflow statuses (PENDING-APPROVED):", mockInputs.length);
const PAGE_SIZE = 10;

const safeArray = (arr) => Array.isArray(arr) ? arr : [];

const Manager = () => {


  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('data');
  const [activeService, setActiveService] = useState('disclosure');

  const [inputs, setInputs] = useState([]);
  const [users, setUsers] = useState([]);

  const [activeSubCategory, setActiveSubCategory] = useState('all');
  const [isDisconnectModalOpen, setIsDisconnectModalOpen] = useState(false);

  const [selectedIds, setSelectedIds] = useState([]);

  const [disconnectTarget, setDisconnectTarget] = useState(null);
  const [disconnectLoading, setDisconnectLoading] = useState(false);

  const [rejectReason, setRejectReason] = useState("");
  const [rejectTargetId, setRejectTargetId] = useState(null);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);

  const [totalCount, setTotalCount] = useState(0);
  const [activeDataCategory, setActiveDataCategory] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [userSearch, setUserSearch] = useState("");
  const [userPage, setUserPage] = useState(1);
  const [dataPage, setDataPage] = useState(1);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  const { user, selectedCompany } = useAuth();
  const role = user?.role;

  const getSRTheme = useCallback((groupName) => {
    if (CATEGORY_MAP.environmental.includes(groupName)) return "E";
    if (CATEGORY_MAP.social.includes(groupName)) return "S";
    if (CATEGORY_MAP.governance.includes(groupName)) return "G";
    return "general";
  }, []);

  const authInfo = useMemo(() => ({
    uuid: user?.uuid ?? '',
    companyId: selectedCompany?.company_id ?? '',
    role: selectedCompany?.role ?? user?.role ?? 'guest'
  }), [user, selectedCompany]);

  // 서비스별 이슈그룹 필터링용 헬퍼
  const getGroupsByService = useCallback((service) => {
    if (service === 'carbon') return ["Carbon_Scope1", "Carbon_Scope2"];
    if (service === 'supply') return ["Supply_Audit", "협력사 평가"];
    // disclosure: 탄소/공급망을 제외한 모든 그룹
    const carbonSupplyGroups = ["Carbon_Scope1", "Carbon_Scope2", "Supply_Audit", "협력사 평가"];
    return AllIssueGroups.filter(g => !carbonSupplyGroups.includes(g));
  }, []);

  const currentServiceGroups = useMemo(() => getGroupsByService(activeService), [activeService, getGroupsByService]);

  const userRole = authInfo.role; // ROLE_CONSULTANT, ROLE_ESG, ROLE_ADMIN 등

  const hasConsultant = useMemo(() => {
    if (!selectedCompany?.name) return false;
    return safeArray(users).some(u =>
      (u.role?.includes('컨설턴트') || u.role?.includes('CONSULTANT') || u.role?.includes('ROLE_CONSULTANT')) &&
      u.company === selectedCompany.name
    );
  }, [users, selectedCompany]);


  /**
   * [FETCH] 데이터 로드 (더미/실서버 분기)
   */
  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      if (USE_DUMMY_API) {
        // 더미 데이터 모드
        setInputs(mockInputs);
        setUsers(mockUsers);
      } else {
        // 실서버 모드
        const [resData, resUsers] = await Promise.all([
          api.patch("/onboard", { company_id: authInfo.companyId, uuid: authInfo.uuid }),
          api.get("/users")
        ]);
        setInputs(safeArray(resData?.data));
        setUsers(safeArray(resUsers?.data));
      }
    } catch (err) {
      console.error("Fetch Error:", err);
      if (USE_DUMMY_API) {
        setInputs(mockInputs);
        setUsers(mockUsers);
      }
    } finally {
      setIsLoading(false);
    }
  }, [USE_DUMMY_API, authInfo]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /**
   * FILTER INPUTS
   */
  const filteredInputs = useMemo(() => {
    let list = safeArray(inputs).filter(i => (i.service || 'disclosure') === activeService);
    if (activeDataCategory !== 'all') {
      list = list.filter(i =>
        CATEGORY_MAP[activeDataCategory]?.includes(i.issueGroup)
      );
    }
    if (activeSubCategory !== 'all') {
      list = list.filter(i => i.issueGroup === activeSubCategory);
    }
    if (statusFilter !== 'all') {
      list = list.filter(i => {
        const s = i.status.toUpperCase();
        if (statusFilter === 'PENDING') return s === 'PENDING' || s === 'REVIEWED';
        return s === statusFilter;
      });
    }

    // [지능형 단계별 노출] 
    // 3단계 워크플로우(hasConsultant)에서 ESG 담당자는 컨설턴트가 검토 중인(pending) 항목을 숨깁니다.
    // 단, 더미 데이터 모드일 때는 테스트를 위해 모두 보여줍니다.
    if (!USE_DUMMY_API && hasConsultant && (userRole?.includes('ESG') || userRole?.includes('관리자'))) {
      list = list.filter(i => i.status.toUpperCase() !== 'PENDING');
    }

    return list;
  }, [inputs, activeDataCategory, activeSubCategory, statusFilter, hasConsultant, userRole, activeService]);

  const pagedInputs = useMemo(() =>
    filteredInputs.slice((dataPage - 1) * PAGE_SIZE, dataPage * PAGE_SIZE),
    [filteredInputs, dataPage]
  );
  const totalDataPages = useMemo(() =>
    Math.ceil(filteredInputs.length / PAGE_SIZE),
    [filteredInputs]
  );

  /**
   * USERS
   */
  const filteredUsers = useMemo(() => {
    const keyword = userSearch.toLowerCase();
    return safeArray(users).filter(u =>
      u.deleteYn === "N" &&
      (
        (u.name || "").toLowerCase().includes(keyword) ||
        (u.company || "").toLowerCase().includes(keyword)
      )
    );
  }, [users, userSearch]);
  const pagedUsers = useMemo(() =>
    filteredUsers.slice((userPage - 1) * PAGE_SIZE, userPage * PAGE_SIZE),
    [filteredUsers, userPage]
  );
  const canDisconnect = useMemo(() => {
    return user?.role === "ESG담당자";
  }, [user]);

  /**
   * KPI
   */
  const kpi = useMemo(() => {
    const serviceInputs = inputs.filter(i => (i.service || 'disclosure') === activeService);
    return serviceInputs.reduce((acc, i) => {
      const s = i.status;
      if (s === 'PENDING' || s === 'pending' || s === 'REVIEWED' || s === 'reviewed') acc.waiting++;
      else if (s === 'APPROVED' || s === 'approved') acc.approved++;
      else if (s === 'REJECTED' || s === 'rejected') acc.rejected++;
      return acc;
    }, { approved: 0, waiting: 0, rejected: 0 });
  }, [inputs, activeService]);

  /**
   * SELECT
   */
  const toggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id)
        ? prev.filter(v => v !== id)
        : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    const ids = pagedInputs.map(i => i.id);
    const allSelected = ids.every(id => selectedIds.includes(id));
    setSelectedIds(allSelected
      ? selectedIds.filter(id => !ids.includes(id))
      : [...new Set([...selectedIds, ...ids])]
    );
  };

  /**
   * ACTION
   */
  const handleAction = async (id, status) => {
    if (status === 'rejected') {
      setRejectTargetId(id);
      setIsRejectModalOpen(true);
      return;
    }
    const ok = await showConfirmAlert("확인", "처리하시겠습니까?", "question");
    if (!ok) return;
    setInputs(prev =>
      prev.map(i => i.id === id ? { ...i, status } : i)
    );
  };
  const permission = useMemo(() => ({
    canDisconnect: role === "ESG담당자" || role === "관리자" || USE_DUMMY_API,
    canConsult: role === "컨설턴트",
    canEmployee: role === "부서담당자",
    canAdmin: role === "관리자",
  }), [role]);

  /**
   * BULK ACTION
   */
  const handleBulkAction = async (status) => {
    if (!selectedIds.length) return;
    const ok = await showConfirmAlert("일괄 처리", "진행하시겠습니까?", "question");
    if (!ok) return;
    setInputs(prev =>
      prev.map(i =>
        selectedIds.includes(i.id)
          ? { ...i, status }
          : i
      )
    );
    setSelectedIds([]);
  };
  const handleMainCategoryChange = (category) => {
    setActiveDataCategory(category);
    setActiveSubCategory('all');
    setDataPage(1);
  };
  const handleDisconnectClick = async (targetUser, type) => {
    const ok = await showConfirmAlert(
      "연결 해제",
      `${targetUser.name}의 ${type === "consultant" ? "컨설턴트" : "직원"} 연결을 해제하시겠습니까?`,
      "warning"
    );
    if (!ok) return;
    setUsers(prev =>
      prev.map(u =>
        u.id === targetUser.id
          ? {
            ...u,
            deleteYn: "Y",
            relations: {
              ...u.relations,
              [type]: false
            }
          }
          : u
      )
    );
  };
  /**
   * GROUP UPDATE
   */
  const toggleGroup = (group) => {
    if (!currentUser) return;

    setCurrentUser(prev => {
      const groups = prev.groups || [];
      const updated = groups.includes(group)
        ? groups.filter(g => g !== group)
        : [...groups, group];

      return { ...prev, groups: updated };
    });
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  return (

    <div id="manager_page">
      <div className="manager-content-container">

        {/* 1. KPI 영역 */}
        <div className='kpi-container'>
          {[
            { key: 'APPROVED', label: '승인 완료', count: kpi.approved },
            { key: 'PENDING', label: '승인 대기', count: kpi.waiting },
            { key: 'REJECTED', label: '반려됨', count: kpi.rejected }
          ].map(item => (
            <div
              key={item.key}
              onClick={() => !isLoading && setStatusFilter(item.key === statusFilter ? 'all' : item.key)}
              className={`kpi-card ${statusFilter === item.key ? 'active' : ''} ${isLoading ? 'disabled' : ''}`}

            >
              <div className='kpi-label'>{item.label}</div>
              <div className='kpi-value'>{item.count}</div>
            </div>
          ))}
        </div>

        {/* 2. 헤더 및 탭 */}
        <div className="page-header">
          <div className="page-title-area">
            <h2 className="page-title">ESG 통합 관리 시스템</h2>
            
            <ServiceTabs 
              activeService={activeService} 
              onServiceChange={(service) => {
                setActiveService(service);
                setDataPage(1);
                setUserPage(1);
                setActiveDataCategory('all');
                setActiveSubCategory('all');
              }} 
            />
          </div>

          <TabButton.Category
            tabs={[
              { label: '데이터 승인', value: 'data' },
              { label: '유저 관리', value: 'user' },
              { label: '초대 관리', value: 'Invite' }
            ]}
            activeTab={activeTab}
            onTabChange={(val) => !isLoading && setActiveTab(val)}
            className="manager-main-tabs"
          />
        </div>

        {/* ============================================================ */}
        {/* 유저 관리 탭 */}
        {/* ============================================================ */}
        {activeTab === 'user' && (
          <UserTab
            isLoading={isLoading}
            userSearch={userSearch}
            setUserSearch={setUserSearch}
            fetchData={fetchData}
            pagedUsers={pagedUsers}
            filteredUsers={filteredUsers}
            PAGE_SIZE={PAGE_SIZE}
            userPage={userPage}
            setUserPage={setUserPage}
            setCurrentUser={setCurrentUser}
            setIsModalOpen={setIsModalOpen}
            setDisconnectTarget={setDisconnectTarget}
            handleDisconnectClick={handleDisconnectClick}
            user={user}
            authRole={user?.role}
            canDisconnect={canDisconnect}
            permission={permission}
            setIsDisconnectModalOpen={setIsDisconnectModalOpen}
            activeService={activeService}
          />
        )}

        {/* ============================================================ */}
        {/* 데이터 승인 탭 */}
        {/* ============================================================ */}
        {activeTab === 'data' && (
          <div className="manager-data-tab-container">
            <DataTab
              activeService={activeService}
              isLoading={isLoading}
              activeDataCategory={activeDataCategory}
              activeSubCategory={activeSubCategory}
              selectedIds={selectedIds}
              setSelectedIds={setSelectedIds}
              pagedInputs={pagedInputs}
              totalDataPages={totalDataPages}
              dataPage={dataPage}
              userRole={userRole}
              hasConsultant={hasConsultant}
              handleMainCategoryChange={handleMainCategoryChange}
              setActiveSubCategory={setActiveSubCategory}
              handleBulkAction={handleBulkAction}
              fetchData={fetchData}
              setDataPage={setDataPage}
              handleAction={handleAction}
              toggleSelect={toggleSelect}
              toggleSelectAll={toggleSelectAll}
            />
          </div>
        )}
        {activeTab === 'Invite' && (
          <section className="fade-in">
            <Invite activeService={activeService} />
          </section>
        )}

        {/* ============================================================ */}
        {/* 모달: 이슈 그룹 관리 */}
        {/* ============================================================ */}

        {isModalOpen && currentUser && (
          <div className="modal-overlay">
            <div className="modal-window">
              <div className="modal-header">
                <h3>{currentUser.name} 권한 설정</h3>
                <button className="close-x" onClick={() => setIsModalOpen(false)} style={{ border: 'none', background: 'none', fontSize: '20px', cursor: 'pointer' }}>×</button>
              </div>

              <div className="modal-body">
                <div className="modal-section">
                  <p className="section-label" style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>현재 할당된 그룹 (클릭 시 제거)</p>
                  <div className="modal-tag-group">
                    {currentUser.groups?.filter(g => currentServiceGroups.includes(g)).map(g => (
                      <button
                        key={g}
                        className={`sr-ig-chip sr-theme-${getSRTheme(g)}`}
                        onClick={() => toggleGroup(g)}
                        style={{ cursor: 'pointer', padding: '6px 12px' }}
                      >
                        {g} ×
                      </button>
                    ))}
                  </div>
                </div>

                <div className="modal-section" style={{ marginTop: '20px' }}>
                  <p className="section-label" style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>추가 가능한 그룹 (클릭 시 추가)</p>
                  <div className="modal-tag-group">
                    {currentServiceGroups
                      .filter(g => !currentUser.groups.includes(g))
                      .map(g => (
                        <button
                          key={g}
                          className="sr-ig-chip"
                          onClick={() => toggleGroup(g)}
                          style={{ cursor: 'pointer', padding: '6px 12px', borderStyle: 'dashed' }}
                        >
                          + {g}
                        </button>
                      ))}
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  className="btn-confirm"
                  onClick={async () => {
                    try {
                      if (!USE_DUMMY_API) {
                        const res = await api.patch('/user', {
                          userId: currentUser.id,
                          groups: currentUser.groups,
                          ...authInfo
                        });

                        if (!res.data.status) {
                          throw new Error('저장 실패');
                        }
                      }

                      showDefaultAlert("성공", "권한 설정이 저장되었습니다.", "success");
                      setIsModalOpen(false);

                    } catch (e) {
                      showDefaultAlert("실패", "권한 저장 중 오류 발생", "error");
                    }
                  }}
                >설정 완료</button>
              </div>
            </div>
          </div>
        )}
        {isRejectModalOpen && (
          <div className="modal-overlay">
            <div className="modal-window">
              <div className="modal-header">
                <h3>반려 사유 입력</h3>

                <button
                  className="close-x"
                  onClick={() => setIsRejectModalOpen(false)}
                >
                  ×
                </button>
              </div>

              <div className="modal-body">
                {/* 기존 반려 사유 (있을 경우만) */}
                {inputs.find(i => i.id === rejectTargetId)?.reason && (
                  <div style={{ marginBottom: '10px', fontSize: '13px', color: '#888' }}>
                    기존 사유: {inputs.find(i => i.id === rejectTargetId)?.reason}
                  </div>
                )}
                <textarea
                  className="reject-textarea"
                  placeholder="반려 사유를 입력해주세요"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  style={{
                    width: '100%',
                    height: '120px',
                    padding: '10px',
                    border: '1px solid #ddd',
                    borderRadius: '6px'
                  }}
                />
              </div>

              <div className="modal-footer">
                <button
                  className="btn-confirm"
                  onClick={async () => {
                    if (!rejectReason.trim()) {
                      showDefaultAlert("알림", "반려 사유를 입력해주세요.", "info");
                      return;
                    }

                    try {
                      if (!USE_DUMMY_API) {
                        await api.patch('/board', {
                          id: rejectTargetId,
                          status: 'rejected',
                          reason: rejectReason,
                          ...authInfo
                        });
                      }

                      setInputs(prev =>
                        prev.map(i =>
                          i.id === rejectTargetId
                            ? { ...i, status: 'rejected', reason: rejectReason }
                            : i
                        )
                      );

                      showDefaultAlert("완료", "반려 처리되었습니다.", "success");
                      setIsRejectModalOpen(false);

                    } catch (e) {
                      showDefaultAlert("실패", "처리 중 오류 발생", "error");
                    }
                  }}
                >
                  반려 확정
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default Manager;