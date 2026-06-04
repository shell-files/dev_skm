import React, { useState } from 'react';
import { useAuth } from '@hooks/AuthContext';
import { POST } from '@utils/Network';
import { showDefaultAlert } from '@components/UI/ServiceAlert';
import "@styles/invite.css";

const USE_DUMMY_API = false;

const FIXTURE_ACTIVE_CONSULTANTS = [
  { id: 1, name: '이채훈', email: 'chaehoon@skm.com', approvedDate: '2026-01-15', connectionStatus: '활동 중' },
  { id: 2, name: '이나라', email: 'nara@tv.com', approvedDate: '2026-02-20', connectionStatus: '활동 중' },
  { id: 3, name: '최윤우', email: 'yunu@hg.com', approvedDate: '2026-03-10', connectionStatus: '활동 중' },
];

const FIXTURE_SUBSIDIARIES = [
  { id: 1, companyName: '그린테크', companyCode: 'GT-001', relationStatus: '연결됨', connectedDate: '2026-03-20' },
  { id: 2, companyName: 'SK에너지', companyCode: 'SKE-002', relationStatus: '연결됨', connectedDate: '2026-04-01' },
];

const FIXTURE_INVITATION_HISTORY = [
  { id: 1, type: 'CONSULTANT', email: 'consult1@naver.com', status: '승인완료', sentDate: '2026-05-01' },
  { id: 2, type: 'SUBSIDIARY_RELATION', email: 'partner@greentec.com', status: '대기중', sentDate: '2026-05-15' },
  { id: 3, type: 'CONSULTANT', email: 'expert@esg.co.kr', status: '만료', sentDate: '2026-04-20' },
  { id: 4, type: 'EMPLOYEE', email: 'dept_manager@skm.com', status: '승인완료', sentDate: '2026-05-25' },
];

const FIXTURE_RELATION_REQUESTS = [
  { id: 1, direction: 'RECEIVED', companyName: '에코솔루션', requestDate: '2026-05-20', desiredRelation: '자회사', status: '승인대기' },
  { id: 2, direction: 'SENT', companyName: '그린파워', requestDate: '2026-05-18', desiredRelation: '자회사', status: '승인대기' },
];

const Invite = () => {
  const { user } = useAuth();
  const [emails1, setEmails1] = useState([]);
  const [selectedRole, setSelectedRole] = useState('Company');
  const [email1, setEmail1] = useState("");

  // Company 탭: 자회사 초대 이메일/코드
  const [subsidiaryInput, setSubsidiaryInput] = useState("");

  const [historyPage, setHistoryPage] = useState(1);
  const [approvalPage, setApprovalPage] = useState(1);

  const itemsPerPage = 5;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const refreshEmail = () => {
    setEmail1("");
    setEmails1([]);
  };

  const inputEmail1 = (e) => {
    e.preventDefault();
    if (!email1.trim() || !emailRegex.test(email1.trim())) {
      showDefaultAlert("입력 오류", "이메일 형식을 확인해주세요", "error");
      return;
    }
    setEmails1([...emails1, email1]);
    setEmail1("");
  };

  const inviteConsultant = async (e) => {
    e.preventDefault();
    if (emails1.length === 0) {
      showDefaultAlert("알림", "초대할 이메일을 입력해주세요.", "info");
      return;
    }

    try {
      if (USE_DUMMY_API) {
        await new Promise(r => setTimeout(r, 800));
      } else {
        await POST("/inviteConsultant", {
          email: [...emails1],
          role: Number(3),
        });
      }
      showDefaultAlert("성공", "컨설턴트 초대장이 발송되었습니다.", "success");
      setEmails1([]);
    } catch (err) {
      showDefaultAlert("실패", err.response?.data?.message || "초대 발송 중 오류가 발생했습니다.", "error");
    }
  };

  const handlePreviewAction = (label) => {
    showDefaultAlert("안내", `${label} API는 후속 단계에서 연결됩니다.`, "info");
  };

  const paginate = (data, currentPage) => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return data.slice(startIndex, startIndex + itemsPerPage);
  };

  const totalPages = (data) => Math.ceil(data.length / itemsPerPage) || 1;

  return (
    <main id="invite-page-root" className="content-body">
      <div className="invite-section">
        {/* 1. 권한 선택 그리드 — Employee 제거 */}
        <div className="role-grid">
          <div
            className={`role-card ${selectedRole === 'Company' ? 'selected' : ''}`}
            onClick={() => {setSelectedRole('Company'); refreshEmail();}}
          >
            <h3>Company</h3>
            <p>그룹사의 연결 기준으로 데이터를 송수신할 수 있습니다.</p>
          </div>
          <div
            className={`role-card ${selectedRole === 'Consultant' ? 'selected' : ''}`}
            onClick={() => {setSelectedRole('Consultant'); refreshEmail();}}
          >
            <h3>Consultant</h3>
            <p>ESG 데이터를 입력하고 보고서를 관리하며 초대 할 수 있습니다.</p>
          </div>
        </div>

        {/* 2. Company 탭 — 자회사 관계 관리 */}
        {selectedRole === "Company" && (
          <div className="invite-form-card">
            <div className="invite_company_left">
              <label className="form-label">자회사 초대</label>
              <div className="chip-input-container">
                <form onSubmit={(e) => { e.preventDefault(); handlePreviewAction('자회사 관계 등록·승인·해제'); }} className="email-form">
                  <input
                    type="text"
                    value={subsidiaryInput}
                    onChange={(e) => setSubsidiaryInput(e.target.value)}
                    className="email-input"
                    placeholder="자회사 이메일 또는 회사 코드 입력"
                  />
                </form>
              </div>
              <div className="button-wrapper">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => handlePreviewAction('자회사 관계 등록·승인·해제')}
                >
                  관계 요청 보내기
                </button>
              </div>
            </div>
            <div className="center_bar"></div>
            <div className="invite_company_right">
              <label className="form-label">자회사 목록</label>
              <div className="table-responsive">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>회사명</th>
                      <th>회사 코드</th>
                      <th>관계 상태</th>
                      <th>연결일</th>
                      <th>관리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FIXTURE_SUBSIDIARIES.map(item => (
                      <tr key={item.id}>
                        <td>{item.companyName}</td>
                        <td><span style={{ fontSize: '12px', color: '#64748b' }}>{item.companyCode}</span></td>
                        <td><span className="status-badge">{item.relationStatus}</span></td>
                        <td>{item.connectedDate}</td>
                        <td>
                          <button className="btn-resend" disabled onClick={() => handlePreviewAction('관계 해제')}>관계 해제</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 3. Consultant 탭 — 초대 + 활동 컨설턴트 2블록 */}
        {selectedRole === "Consultant" && (
          <div className="invite-form-card">
            <div className="invite_company_left">
              <label className="form-label">컨설턴트 초대</label>
              <div className="chip-input-container">
                <div className='email_list'>
                  {emails1.map((email, index) => (
                    <div key={index} className="email-chip" onClick={() => setEmails1(emails1.filter((_, i) => i !== index))}>
                      {email} <span>×</span>
                    </div>
                  ))}
                </div>
                <form onSubmit={inputEmail1} className="email-form">
                  <input type="text" value={email1 || ""} onChange={(e) => setEmail1(e.target.value)} className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={inviteConsultant} className="button-wrapper">
                <button type='submit' className="btn-primary">초대장 발송</button>
              </form>
            </div>
            <div className="center_bar"></div>
            <div className="invite_company_right">
              <label className="form-label">활동 중인 컨설턴트</label>
              <div className="table-responsive">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>이름</th>
                      <th>이메일</th>
                      <th>초대 승인일</th>
                      <th>연결 상태</th>
                      <th>관리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FIXTURE_ACTIVE_CONSULTANTS.map(item => (
                      <tr key={item.id}>
                        <td><strong>{item.name}</strong></td>
                        <td>{item.email}</td>
                        <td>{item.approvedDate}</td>
                        <td><span className="status-badge">{item.connectionStatus}</span></td>
                        <td>
                          <button className="btn-resend" disabled onClick={() => handlePreviewAction('컨설턴트 관리')}>관리</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 4. 최근 초대·발송 내역 + 관계 요청 승인 대기 */}
        <div className="management-dual-section">
          <div className="history-container">
            <div className="history-header">최근 초대·발송 내역</div>
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>유형</th>
                    <th>대상 이메일 또는 회사</th>
                    <th>상태</th>
                    <th>발송일</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {paginate(FIXTURE_INVITATION_HISTORY, historyPage).map((item) => (
                    <tr key={item.id}>
                      <td><span style={{ fontSize: '11px', background: '#f1f5f9', padding: '2px 8px', borderRadius: '4px' }}>{item.type}</span></td>
                      <td>{item.email}</td>
                      <td>
                        <span className={`status-badge ${item.status === '만료' ? 'expired' : ''}`}>
                          {item.status}
                        </span>
                      </td>
                      <td>{item.sentDate}</td>
                      <td><button className="btn-resend" disabled onClick={() => handlePreviewAction('재발송')}>재발송</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination-wrapper">
              <button disabled={historyPage === 1} onClick={() => setHistoryPage(historyPage - 1)}>이전</button>
              <span>{historyPage} / {totalPages(FIXTURE_INVITATION_HISTORY)}</span>
              <button disabled={historyPage === totalPages(FIXTURE_INVITATION_HISTORY)} onClick={() => setHistoryPage(historyPage + 1)}>다음</button>
            </div>
          </div>

          <div className="history-container">
            <div className="history-header">관계 요청 승인 대기</div>
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>요청 방향</th>
                    <th>회사명</th>
                    <th>요청일</th>
                    <th>희망 관계</th>
                    <th>상태</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {FIXTURE_RELATION_REQUESTS.length > 0 ? (
                    paginate(FIXTURE_RELATION_REQUESTS, approvalPage).map((item) => (
                      <tr key={item.id}>
                        <td>
                          <span style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: item.direction === 'RECEIVED' ? '#dbeafe' : '#fef3c7',
                            color: item.direction === 'RECEIVED' ? '#1d4ed8' : '#92400e',
                          }}>
                            {item.direction === 'RECEIVED' ? '수신' : '발신'}
                          </span>
                        </td>
                        <td>{item.companyName}</td>
                        <td>{item.requestDate}</td>
                        <td>{item.desiredRelation}</td>
                        <td><span className="role-badge">{item.status}</span></td>
                        <td>
                          <div className="action-button-group">
                            {item.direction === 'RECEIVED' && (
                              <>
                                <button className="btn-approve" disabled onClick={() => handlePreviewAction('승인')}>승인</button>
                                <button className="btn-reject" disabled onClick={() => handlePreviewAction('거절')}>거절</button>
                              </>
                            )}
                            {item.direction === 'SENT' && (
                              <button className="btn-resend" disabled onClick={() => handlePreviewAction('관계 해제')}>관계 해제</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="empty-text">대기 중인 요청이 없습니다.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="pagination-wrapper">
              <button disabled={approvalPage === 1} onClick={() => setApprovalPage(approvalPage - 1)}>이전</button>
              <span>{approvalPage} / {totalPages(FIXTURE_RELATION_REQUESTS)}</span>
              <button disabled={approvalPage === totalPages(FIXTURE_RELATION_REQUESTS)} onClick={() => setApprovalPage(approvalPage + 1)}>다음</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Invite;