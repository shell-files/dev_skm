/**
 * CompanySelect.jsx
 * 레이어: Page
 * 역할: 로그인 후 접속할 회사를 검색·선택하고 세션에 반영하는 회사 선택 페이지
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { useAuth } from '@hooks/AuthContext.jsx';
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import "@styles/company.css"
import { useDispatch, useSelector } from "react-redux";
import { updateCompanyName } from "@stores/authSlice";

const CompanySelect = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { companies } = useAuth();

  // USE_DUMMY_API 플래그에 따라 데이터 소스 결정
  // const companies = realCompanies || [];

  // 1. 상태 관리
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState();

  // 2. 검색어에 따라 필터링된 리스트 계산
  const filteredCompanies = companies.filter((company) => {
    const name = company.company_name || company.name || "";
    return name.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // 3. 선택 완료 핸들러
  const handleSubmit = async () => {
    if (!selectedCompanyId) {
      alert("회사를 먼저 선택해주세요!");
      return;
    }
    try {
      const res = await POST("/company", { companyId: selectedCompanyId });
      if (res.status === true) {
        const company = filteredCompanies.filter(c => {
          return c.company_id === Number(selectedCompanyId);
        })
        if(company.length > 0) {
          dispatch(updateCompanyName(company[0]));
        }
        navigate("/");
      }
    } catch (e) {
      showDefaultAlert("회사 선택 실패", "선택한 회사에 접근 권한이 없습니다.", "error");
    }
  };

  return (
    <div id="select_company">
      <div className="select-container">
        <div className="select-code">회사 선택</div>
        
        <p className="select-desc">
          접속할 회사를 선택해 주세요.
        </p>
        
        {/* 검색 입력 창 */}
        <div className="input-group">
          <label htmlFor="search">회사명 검색</label>
          <input
            type="text"
            id="search"
            className="search-input"
            placeholder="회사 이름을 입력하세요"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* 회사 선택 셀렉트 박스 */}
        <div className="input-group">
          <label htmlFor="companyList">회사 선택</label>
          <select
            id="companyList"
            className="company-select"
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId( e.target.value)}
          >
            <option value="">회사를 선택해주세요</option>
            {filteredCompanies.map((company) => (
              <option key={company.company_id} value={company.company_id}>
                {company.company_name}
              </option>
            ))}
          </select>
        </div>

        <button type="button" className="btn-submit" onClick={handleSubmit}>
          선택 완료
        </button>
        
        <p className="info-text">목록에 회사가 없다면 관리자에게 문의하세요.</p>
      </div>
    </div>
  );
};

export default CompanySelect;
