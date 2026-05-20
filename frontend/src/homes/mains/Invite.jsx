import React, { useState } from 'react';
import { useAuth } from '@hooks/AuthContext';
// import { api } from '@utils/Network';
import { showDefaultAlert } from '@components/UI/ServiceAlert';
import "@styles/invite.css";

const USE_DUMMY_API = false;

const Invite = ({ activeService = 'disclosure' }) => {
  const { user } = useAuth();
  // --- 기존 상태 ---
  const [emails1, setEmails1] = useState([]);
  const [emails2, setEmails2] = useState([]);
  const [selectedRole, setSelectedRole] = useState('Company');
  const [email1, setEmail1] = useState("");
  const [email2, setEmail2] = useState("");
  const [selectedCategories, setSelectedCategories] = useState([]);

  // --- 탭 & 페이지네이션 상태 ---
  const [activeTab, setActiveTab] = useState('company'); 
  const [historyPage, setHistoryPage] = useState(1);
  const [approvalPage, setApprovalPage] = useState(1);
  const [memberPage, setMemberPage] = useState(1);
  
  const itemsPerPage = 5;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const getSRTheme = (groupName) => {
    const environmental = ["Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment"];
    const social = ["Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy"];
    const governance = ["Governance", "Risk", "Compliance", "Ethics", "Business Conduct", "Data Governance"];

    if (environmental.includes(groupName)) return "E";
    if (social.includes(groupName)) return "S";
    if (governance.includes(groupName)) return "G";
    return "general";
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

  // --- 구성원 목록 데이터 구조 (협력사 탭에 '관계' 데이터 추가) ---
  const [members] = useState({
    company: [
      { id: 1, companyName: "그린테크", email: "partner1@supply.com", date: "2026-03-20", relation: "원청-협력" }
    ],
    consultant: [
      { id: 1, name: "김컨설", email: "consult1@naver.com", phone: "010-1234-5678", date: "2026-01-15" }
    ],
    employee: [
      { id: 1, name: "이직원", email: "worker1@company.com", position: "ESG팀", date: "2026-02-01" }
    ]
  });

  const refreshEmail = () => {
    setEmail1(""); 
    setEmails1([]);
    setEmail2(""); 
    setEmails2([]);
  };

  // --- 핸들러 함수들 ---
  const inputEmail1 = (e) => {
    e.preventDefault();
    if (!email1.trim() || !emailRegex.test(email1.trim())) {
      showDefaultAlert("입력 오류", "이메일 형식을 확인해주세요", "error");
      return;
    }
    setEmails1([...emails1, email1]);
    setEmail1("");
  };

  const inputEmail2 = (e) => {
    e.preventDefault();
    if (!email2.trim() || !emailRegex.test(email2.trim())){
      alert("이메일을 확인해주세요");
      return;
    }
    setEmails2([...emails2, email2]);
    setEmail2("");
  };

  const inviteCompany = (e)=> { 
    e.preventDefault(); 
    if (emails1.length === 0) {
      showDefaultAlert("알림", "초대할 이메일을 입력해주세요.", "info");
      return;
    }
    console.log("Invite Company:", emails1); 
    showDefaultAlert("성공", "협력사 초대장이 발송되었습니다.", "success");
    setEmails1([]);
  };

  const roleRequest = (e) => { 
    e.preventDefault(); 
    if (emails2.length === 0) {
      showDefaultAlert("알림", "요청할 이메일을 입력해주세요.", "info");
      return;
    }
    console.log("Role Request:", emails2); 
    showDefaultAlert("성공", "권한 요청이 발송되었습니다.", "success");
    setEmails2([]);
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
        await api.post("/inviteConsultant", {
          uuid: String(user?.uuid),
          email: [...emails1],
          role: Number(3)
        });
      }
      showDefaultAlert("성공", "컨설턴트 초대장이 발송되었습니다.", "success");
      console.log("email:", typeof(emails1))
      console.log("uuid:", String(user?.uuid), "이메일 :", emails1, "룰 : ", Number(3));  
      setEmails1([]);
    } catch (err) {
      showDefaultAlert("실패", err.response?.data?.message || "초대 발송 중 오류가 발생했습니다.", "error");
    }
  };

  const inviteEmployee = async (e) => { 
    e.preventDefault(); 
    if (emails1.length === 0) {
      showDefaultAlert("알림", "초대할 이메일과 이슈를 등록해주세요.", "info");
      return;
    }

    try {
      if (USE_DUMMY_API) {
        await new Promise(r => setTimeout(r, 800));
      } else {
        // 직원(부서담당자) 초대는 이메일별로 이슈가 다를 수 있으나, 
        // API 규격이 단일 호출이라면 루프를 돌거나 가장 최근 규격에 맞춥니다.
        // 여기서는 화면에 쌓인 리스트를 하나씩 처리하거나, 묶어서 보냅니다.
        // 명세서상 email이 배열이므로, 동일 이슈 그룹에 대해 묶어서 보낼 수 있습니다.
        
        // 간단한 구현을 위해 각 항목별로 순차적으로 보냅니다.
        for (const item of emails1) {
          // console.log("uuid:", user?.uuid, "이메일 :", [item.email], "이슈 : ", item.issue, "룰 : ", Number(4));
          await api.post("/inviteMember", {
            "uuid": user?.uuid,
            "email": [item.email],
            "issue": item.issue,
            "role": Number(4)
          });
        }
      }
      // console.log("uuid:", user.uuid, "이메일 :", item.email, "이슈 : ", item.issue, "룰 : ", Number(4));
      showDefaultAlert("성공", "직원 초대장이 발송되었습니다.", "success");
      setEmails1([]);
    } catch (err) {
      // console.log("uuid:", user.uuid, "이메일 :", item.email, "이슈 : ", item.issue, "룰 : ", Number(4));
      showDefaultAlert("실패", err.response?.data?.message || "초대 발송 중 오류가 발생했습니다.", "error");
    }
  };

  const inputIssueEmail = (e) => {
    e.preventDefault();
    if (!email1.trim() || !emailRegex.test(email1.trim())){
      alert("이메일을 확인해주세요");
      return;
    }
    if (selectedCategories.length === 0) {
      alert("이슈를 선택해주세요");
      return;
    }
    setEmails1((prev) => [...prev, { email: email1, issue: [...selectedCategories] }]);
    setEmail1(""); 
    setSelectedCategories([]);
  };

  const handleApprove = (id) => {
    alert("권한 요청을 승인했습니다.");
    setApprovalList(approvalList.filter(item => item.id !== id));
  };

  const handleReject = (id) => {
    alert("권한 요청을 거절했습니다.");
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
            onClick={() => {setSelectedRole('Company'); refreshEmail();}}
          >
            <h3>Company</h3>
            <p>시스템 설정 및 팀원 관리, 모든 데이터에 접근 가능합니다.</p>
          </div>
          <div 
            className={`role-card ${selectedRole === 'Consultant' ? 'selected' : ''}`}
            onClick={() => {setSelectedRole('Consultant'); refreshEmail();}}
          >
            <h3>Consultant</h3>
            <p>ESG 데이터를 입력하고 보고서를 관리하며 초대 할 수 있습니다.</p>
          </div>
          <div 
            className={`role-card ${selectedRole === 'Employee' ? 'selected' : ''}`}
            onClick={() => {setSelectedRole('Employee'); refreshEmail();}}
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
                    <div key={index} className="email-chip" onClick={() => setEmails1(emails1.filter((_, i) => i !== index))}>
                      {email} <span>×</span>
                    </div>
                  ))}
                </div>
                <form onSubmit={inputEmail1} className="email-form">
                  <input type="text" value={email1 || ""} onChange={(e) => setEmail1(e.target.value)} className="email-input" placeholder="이메일 입력 후 엔터" />
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
                <form onSubmit={inputEmail1} className="email-form">
                  <input type="text" value={email1 || ""} onChange={(e) => setEmail1(e.target.value)} className="email-input" placeholder="이메일 입력 후 엔터" />
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
                  {emails1.map((email, index) => (
                    <div key={index} className="email-chip" onClick={() => setEmails1(emails1.filter((_, i) => i !== index))}>
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
                <form onSubmit={inputIssueEmail} className="email-form">
                  <input type="text" value={email1 || ""} onChange={(e) => setEmail1(e.target.value)} className="email-input" placeholder="이메일 입력 후 엔터" />
                </form>
              </div>
              <form onSubmit={inviteEmployee} className="button-wrapper">
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