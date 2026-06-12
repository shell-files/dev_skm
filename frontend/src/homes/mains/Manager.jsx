import React, { useMemo, useState, useEffect, useCallback } from 'react';
import '@styles/Manager.css';
import Invite from './Invite.jsx'
import UserTab from './UserTab';
import UserManagementModal from './modal/UserManagementModal';
import TabButton from '@components/UI/TabButton';
import PageHeader from '@components/UI/PageHeader';
import { useAuth } from '@hooks/AuthContext'

/**
 * [CONFIG]
 *  true: mock 데이터
 *  false: 실제 API
 */
const USE_DUMMY_API = false;

const PAGE_SIZE = 10;

const mockUsers = [
  // SKM 팀
  {
    id: 1, name: '이채훈', email: 'chaehoon@skm.com', company: 'SKM', role: '컨설턴트', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['기후변화 전환계획', '온실가스 배출', '에너지', '수자원', '생물다양성'], assignedMetricCount: 24 },
    ]
  },
  {
    id: 2, name: '김하영', email: 'hayoung@skm.com', company: 'SKM', role: '부서담당자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['수자원', '폐기물'], assignedMetricCount: 4 },
    ]
  },
  {
    id: 3, name: '이정빈', email: 'jungbin@skm.com', company: 'SKM', role: '관리자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['기후변화 전환계획', '온실가스 배출', '에너지'], assignedMetricCount: 8 },
    ]
  },
  {
    id: 4, name: '최수아', email: 'sua@skm.com', company: 'SKM', role: 'ESG담당자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['거버넌스', '준법'], assignedMetricCount: 6 },
    ]
  },

  // HG 팀
  {
    id: 5, name: '김지환', email: 'jihwan@hg.com', company: 'HG', role: '부서담당자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['노동', '안전보건'], assignedMetricCount: 10 },
    ]
  },
  {
    id: 6, name: '조윤주', email: 'yunju@hg.com', company: 'HG', role: '부서담당자', deleteYn: "N",
    assignmentScopes: []
  },
  {
    id: 7, name: '최가영', email: 'gayoung@hg.com', company: 'HG', role: 'ESG담당자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['생물다양성', '순환경제'], assignedMetricCount: 5 },
    ]
  },
  {
    id: 8, name: '최윤우', email: 'yunu@hg.com', company: 'HG', role: '컨설턴트', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['폐기물', '온실가스 배출'], assignedMetricCount: 6 },
    ]
  },

  // TV 팀
  {
    id: 9, name: '남영준', email: 'youngjun@tv.com', company: 'TV', role: '부서담당자', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['인권', '다양성'], assignedMetricCount: 7 },
    ]
  },
  {
    id: 10, name: '이나라', email: 'nara@tv.com', company: 'TV', role: '컨설턴트', deleteYn: "N",
    assignmentScopes: [
      { reportingYear: 2026, projectName: '2026 지속가능경영보고서', cycleType: 'POST_DMA_DISCLOSURE', assignedSubIssues: ['기후변화 전환계획', '온실가스 배출', '에너지'], assignedMetricCount: 18 },
    ]
  },
  { id: 11, name: '이현서', email: 'hyunseo@tv.com', company: 'TV', role: 'ESG담당자', deleteYn: "N", assignmentScopes: [] },
  { id: 12, name: '강사님', email: 'mentor@mt.com', company: 'MT', role: '컨설턴트', deleteYn: "N", assignmentScopes: [] },
];

const safeArray = (arr) => Array.isArray(arr) ? arr : [];

const Manager = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('user');
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userPage, setUserPage] = useState(1);

  // UserManagementModal state
  const [isUserMgmtModalOpen, setIsUserMgmtModalOpen] = useState(false);
  const [selectedUserForMgmt, setSelectedUserForMgmt] = useState(null);

  const { user, selectedCompany } = useAuth();

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      if (USE_DUMMY_API) {
        setUsers(mockUsers);
      }
    } catch (err) {
      console.error("Fetch Error:", err);
      if (USE_DUMMY_API) {
        setUsers(mockUsers);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  const handleOpenUserManagement = (userItem) => {
    setSelectedUserForMgmt(userItem);
    setIsUserMgmtModalOpen(true);
  };

  return (
    <div id="manager_page">
      <div className="manager-content-container">
        <div className="page-header">
          <div className="page-title-area">
            <PageHeader
              category="시스템"
              title="ESG 통합 관리 시스템"
              description="사용자, 프로젝트, 승인 데이터를 통합 조회합니다."
              iconClass="bi-building-fill"
            />
          </div>

          <TabButton.Category
            tabs={[
              { label: '사용자 관리', value: 'user' },
              { label: '관계·초대 관리', value: 'Invite' }
            ]}
            activeTab={activeTab}
            onTabChange={(val) => !isLoading && setActiveTab(val)}
            className="manager-main-tabs"
          />
        </div>

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
            onOpenUserManagement={handleOpenUserManagement}
          />
        )}

        {activeTab === 'Invite' && (
          <section className="fade-in">
            <Invite />
          </section>
        )}

        <UserManagementModal
          isOpen={isUserMgmtModalOpen}
          onClose={() => setIsUserMgmtModalOpen(false)}
          userItem={selectedUserForMgmt}
        />
      </div>
    </div>
  );
};

export default Manager;