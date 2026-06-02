import React, { useState, useEffect } from 'react';
import { useAuth } from '@hooks/AuthContext';
import { GET, POST } from '@utils/Network';
import { showDefaultAlert } from '@components/UI/ServiceAlert';
import "@styles/invite.css";

const USE_DUMMY_API = true;

const Invite = ({ activeService = 'disclosure' }) => {
  const { user } = useAuth();

  // --- 기존 상태 ---
  const [selectedRole, setSelectedRole] = useState('Company');
  const [selectedCategories, setSelectedCategories] = useState([]);

  // input
  const [companyEmailInput, setCompanyEmailInput] = useState("");
  const [consultantEmailInput, setConsultantEmailInput] = useState("");
  const [employeeEmailInput, setEmployeeEmailInput] = useState("");

  // lists
  const [companyEmails, setCompanyEmails] = useState([]);
  const [consultantEmails, setConsultantEmails] = useState([]);
  const [employeeEmails, setEmployeeEmails] = useState([]);

  // ❗추가 (누락된 상태)
  const [emails1, setEmails1] = useState([]);
  const [emails2, setEmails2] = useState([]);
  const [email2, setEmail2] = useState("");

  // --- 탭 & 페이지네이션 상태 ---
  const [historyPage, setHistoryPage] = useState(1);
  const [approvalPage, setApprovalPage] = useState(1);

  const itemsPerPage = 5;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const getSRTheme = (subIssueCode) => {
    if (USE_DUMMY_API === true) {
      const environmental = ["Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment"];
      const social = ["Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy"];
      const governance = ["Governance", "Risk", "Compliance", "Ethics", "Business Conduct", "Data Governance"];

      if (environmental.includes(subIssueCode)) return "E";
      if (social.includes(subIssueCode)) return "S";
      if (governance.includes(subIssueCode)) return "G";
      return "general";
    }

    if (USE_DUMMY_API === false) {
      if (subIssueCode.startsWith("E_")) return "E";
      if (subIssueCode.startsWith("S_")) return "S";
      if (subIssueCode.startsWith("G_")) return "G";
      return "general";
    }
  };

  const serviceCategories = {
    disclosure: [
      "Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment",
      "Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy",
      "Governance", "Risk", "Compliance", "Ethics", "Business Conduct", "Data Governance"
    ],
    carbon: ["Greenhouse Gas", "Energy Consumption", "Carbon Footprint", "Emission Reduction", "Carbon Offsetting", "Renewable Energy"],
    supply: ["Supplier Assessment", "Supply Chain Risk", "Ethical Sourcing", "Conflict Minerals", "Logistics Impact", "Supplier Diversity"]
  };

  const esgCategories = serviceCategories[activeService] || serviceCategories.disclosure;

  const [issueMap, setIssueMap] = useState([]);
  const [loadingIssues, setLoadingIssues] = useState(false);

  useEffect(() => {
    const fetchIssues = async () => {
      setLoadingIssues(true);
      try {
        const res = await POST("/issue");
        if (res.data.status) {
          setIssueMap(res.data.data);
        }
      } finally {
        setLoadingIssues(false);
      }
    };

    fetchIssues();
  }, []);

  // --- 최근 초대 내역 ---
  const [invitationHistory] = useState([
    { id: 1, email: "member1@gmail.com", role: "Manager", status: "대기중" },
    { id: 2, email: "consult1@naver.com", role: "Consultant", status: "만료" },
    { id: 3, email: "worker1@company.com", role: "Employee", status: "대기중" }
  ]);

  // --- 권한 요청 승인 대기 ---
  const [approvalList, setApprovalList] = useState([
    { id: 1, email: "req1@partner.com", currentRole: "Guest", requestedRole: "Company", requestDate: "2026-05-01" },
    { id: 2, email: "req2@partner.com", currentRole: "Guest", requestedRole: "Company", requestDate: "2026-05-03" }
  ]);

  const refreshEmail = () => {
    setCompanyEmailInput("");
    setConsultantEmailInput("");
    setEmployeeEmailInput("");

    setCompanyEmails([]);
    setConsultantEmails([]);
    setEmployeeEmails([]);

    setSelectedCategories([]);
  };

  // --- 핸들러 ---
  const inputCompanyEmail = (e) => {
    e.preventDefault();
    if (!companyEmailInput.trim() || !emailRegex.test(companyEmailInput.trim())) {
      showDefaultAlert("입력 오류", "이메일 형식을 확인해주세요", "error");
      return;
    }
    setCompanyEmails([...companyEmails, companyEmailInput.trim()]);
    setCompanyEmailInput("");
  };

  const inputConsultantEmail = (e) => {
    e.preventDefault();
    if (!consultantEmailInput.trim() || !emailRegex.test(consultantEmailInput.trim())) {
      showDefaultAlert("입력 오류", "이메일 형식을 확인해주세요", "error");
      return;
    }
    setConsultantEmails([...consultantEmails, consultantEmailInput.trim()]);
    setConsultantEmailInput("");
  };

  // ❗추가 (누락된 협력 요청 입력)
  const inputEmail2 = (e) => {
    e.preventDefault();
    if (!email2.trim() || !emailRegex.test(email2.trim())) {
      showDefaultAlert("입력 오류", "이메일 형식을 확인해주세요", "error");
      return;
    }
    setEmails2([...emails2, email2.trim()]);
    setEmail2("");
  };

  const inviteCompany = (e) => {
    e.preventDefault();
    if (companyEmails.length === 0) {
      showDefaultAlert("알림", "초대할 이메일을 입력해주세요.", "info");
      return;
    }
    setCompanyEmails([]);
  };

  const roleRequest = (e) => {
    e.preventDefault();
    if (companyEmails.length === 0) {
      showDefaultAlert("알림", "요청할 이메일을 입력해주세요.", "info");
      return;
    }
    setCompanyEmails([]);
  };

  const inviteConsultant = async (e) => {
    e.preventDefault();
    if (consultantEmails.length === 0) {
      showDefaultAlert("알림", "초대할 이메일을 입력해주세요.", "info");
      return;
    }

    try {
      await POST("/inviteConsultant", {
        email: [...consultantEmails],
        role: Number(3),
      });

      setConsultantEmails([]);
    } catch (err) {
      showDefaultAlert("실패", err.response?.data?.message || "오류", "error");
    }
  };

  const inviteEmployee = async (e) => {
    e.preventDefault();
    if (employeeEmails.length === 0) return;

    for (const item of employeeEmails) {
      await POST("/inviteMember", {
        uuid: user?.uuid,
        email: [item.email],
        issue: item.issue,
        role: Number(4)
      });
    }

    setEmployeeEmails([]);
  };

  const inputEmployeeEmail = (e) => {
    e.preventDefault();

    if (!employeeEmailInput.trim() || !emailRegex.test(employeeEmailInput.trim())) {
      alert("이메일을 확인해주세요");
      return;
    }

    if (selectedCategories.length === 0) {
      alert("이슈를 선택해주세요");
      return;
    }

    setEmployeeEmails([
      ...employeeEmails,
      {
        email: employeeEmailInput.trim(),
        issue: [...selectedCategories]
      }
    ]);

    setEmployeeEmailInput("");
    setSelectedCategories([]);
  };

  const handleApprove = (id) => {
    setApprovalList(approvalList.filter(item => item.id !== id));
  };

  const handleReject = (id) => {
    setApprovalList(approvalList.filter(item => item.id !== id));
  };

  const paginate = (data, currentPage) => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return data.slice(startIndex, startIndex + itemsPerPage);
  };

  const totalPages = (data) => Math.ceil(data.length / itemsPerPage) || 1;

  return (
    <main id="invite-page-root" className="content-body">
      <div className="invite-section">
        {/* 1. 권한 선택 그리드 */}
        <div className="role-grid">
          <div
            className={`role-card ${selectedRole === 'Company' ? 'selected' : ''}`}
            onClick={() => { setSelectedRole('Company'); refreshEmail(); }}
          >
            <h3>Company</h3>
            <p>시스템 설정 및 팀원 관리, 모든 데이터에 접근 가능합니다.</p>
          </div>
          <div
            className={`role-card ${selectedRole === 'Consultant' ? 'selected' : ''}`}
            onClick={() => { setSelectedRole('Consultant'); refreshEmail(); }}
          >
            <h3>Consultant</h3>
            <p>ESG 데이터를 입력하고 보고서를 관리하며 초대 할 수 있습니다.</p>
          </div>
          <div
            className={`role-card ${selectedRole === 'Employee' ? 'selected' : ''}`}
            onClick={() => { setSelectedRole('Employee'); refreshEmail(); }}
          >
            <h3>Employee</h3>
            <p>데이터 조회 및 입력만 가능합니다.</p>
          </div>
        </div>

        {/* 2. 초대 폼 영역 */}
        {selectedRole === "Company" && (
          <div className="invite-form-card">
            <div className="invite_company_left">
              <label className="form-label">협력사 초대</label>
              <div className="chip-input-container">
                <div className='email_list'>
                  {emails1.map((email, index) => (
                    <div key={index} className="email-chip" onClick={() =>
                      setEmployeeEmails(employeeEmails.filter((_, i) => i !== index))
                    }>
                      {email} <span>×</span>
                    </div>
                  ))}
                </div>
                <form onSubmit={inputCompanyEmail} className="email-form">
                  <input type="text" value={companyEmailInput}
                    onChange={(e) => setCompanyEmailInput(e.target.value)}
                    className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={inviteCompany} className="button-wrapper">
                <button type='submit' className="btn-primary">초대장 발송</button>
              </form>
            </div>
            <div className="center_bar"></div>
            <div className="invite_company_right">
              <label className="form-label">협력 권한 요청</label>
              <div className="chip-input-container">
                <div className='email_list'>
                  {emails2.map((email, index) => (
                    <div key={index} className="email-chip" onClick={() => setEmails2(emails2.filter((_, i) => i !== index))}>
                      {email} <span>×</span>
                    </div>
                  ))}
                </div>
                <form onSubmit={inputEmail2} className="email-form">
                  <input type="text" value={email2 || ""} onChange={(e) => setEmail2(e.target.value)} className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={roleRequest} className="button-wrapper">
                <button className="btn-primary">권한 요청 발송</button>
              </form>
            </div>
          </div>
        )}

        {selectedRole === "Consultant" && (
          <div className="invite-form-card single-section">
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
                <form onSubmit={inputConsultantEmail} className="email-form">
                  <input type="text" value={consultantEmailInput}
                    onChange={(e) => setConsultantEmailInput(e.target.value)}
                    className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={inviteConsultant} className="button-wrapper">
                <button type='submit' className="btn-primary">초대장 발송</button>
              </form>
            </div>
          </div>
        )}

        {selectedRole === "Employee" && (
          <div className="invite-form-card employee-grid">
            <div className="invite_company_left category-section">
              <label className="form-label">요청 카테고리 (중복 선택 가능)</label>
              <div className="checkbox-group-container">
                {esgCategories.map((item, idx) => {
                  const isSelected = selectedCategories.includes(item);
                  const theme = getSRTheme(item);
                  return (
                    <label
                      key={idx}
                      className={`category-checkbox-label sr-ig-chip sr-theme-${theme} ${isSelected ? 'active' : ''}`}
                      style={{
                        marginBottom: '8px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        width: 'fit-content',
                        opacity: isSelected ? 1 : 0.5,
                        borderStyle: isSelected ? 'solid' : 'dashed'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedCategories([...selectedCategories, item]);
                          else setSelectedCategories(selectedCategories.filter(c => c !== item));
                        }}
                        className="category-checkbox"
                      />
                      {item}
                    </label>
                  );
                })}
              </div>
            </div>
            <div className="center_bar"></div>
            <div className="invite_company_right email-section">
              <label className="form-label">직원 회원 가입 초대 (이메일)</label>
              <div className="chip-input-container">
                <div className='email_list'>
                  {employeeEmails.map((email, index) => (
                    <div key={index} className="email-chip" onClick={() =>
                      setEmployeeEmails(employeeEmails.filter((_, i) => i !== index))
                    }>
                      <span className="email-text">{email.email}</span>
                      <div className="chip-issue-list" style={{ display: 'flex', gap: '4px', marginLeft: '8px' }}>
                        {email.issue.map(iss => (
                          <span key={iss} className={`sr-ig-chip sr-theme-${getSRTheme(iss)}`} style={{ fontSize: '10px', padding: '1px 6px' }}>
                            {iss}
                          </span>
                        ))}
                      </div>
                      <span className="close-icon" style={{ marginLeft: '8px' }}>×</span>
                    </div>
                  ))}
                </div>
                <form onSubmit={inputEmployeeEmail} className="email-form">
                  <input type="text" value={employeeEmailInput}
                    onChange={(e) => setEmployeeEmailInput(e.target.value)}
                    className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={inputEmployeeEmail} className="button-wrapper">
                <button type='submit' className="btn-primary">권한 요청 발송</button>
              </form>
            </div>
          </div>
        )}

        {/* 3. 최근 초대 내역 & 권한 요청 승인 영역 */}
        <div className="management-dual-section">
          {/* 최근 초대 내역 테이블 */}
          <div className="history-container">
            <div className="history-header">최근 초대 내역</div>
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>대상 이메일</th>
                    <th>권한</th>
                    <th>상태</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {paginate(invitationHistory, historyPage).map((item) => (
                    <tr key={item.id}>
                      <td>{item.email}</td>
                      <td>{item.role}</td>
                      <td>
                        <span className={`status-badge ${item.status === '만료' ? 'expired' : ''}`}>
                          {item.status}
                        </span>
                      </td>
                      <td><button className="btn-resend">재발송</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination-wrapper">
              <button disabled={historyPage === 1} onClick={() => setHistoryPage(historyPage - 1)}>이전</button>
              <span>{historyPage} / {totalPages(invitationHistory)}</span>
              <button disabled={historyPage === totalPages(invitationHistory)} onClick={() => setHistoryPage(historyPage + 1)}>다음</button>
            </div>
          </div>

          {/* 권한 요청 승인 대기 */}
          <div className="history-container">
            <div className="history-header">권한 요청 승인 대기</div>
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>이메일</th>
                    <th>희망 권한</th>
                    <th>요청일</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {approvalList.length > 0 ? (
                    paginate(approvalList, approvalPage).map((item) => (
                      <tr key={item.id}>
                        <td>{item.email}</td>
                        <td><span className="role-badge">{item.requestedRole}</span></td>
                        <td>{item.requestDate}</td>
                        <td>
                          <div className="action-button-group">
                            <button className="btn-approve" onClick={() => handleApprove(item.id)}>승인</button>
                            <button className="btn-reject" onClick={() => handleReject(item.id)}>거절</button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="empty-text">대기 중인 요청이 없습니다.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="pagination-wrapper">
              <button disabled={approvalPage === 1} onClick={() => setApprovalPage(approvalPage - 1)}>이전</button>
              <span>{approvalPage} / {totalPages(approvalList)}</span>
              <button disabled={approvalPage === totalPages(approvalList)} onClick={() => setApprovalPage(approvalPage + 1)}>다음</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Invite;