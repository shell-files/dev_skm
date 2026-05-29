/**
 * Onboarding.jsx 페이지 흐름 및 구조 가이드
 * 
 * 1. 데이터 흐름 (Data Flow):
 *    - 원본 데이터: metrics (onboardingData.js에서 로드 및 localStorage와 동기화)
 *    - 필터링 데이터: filteredData (검색어, 카테고리, 이슈그룹, 상태 필터가 적용된 결과)
 *    - 페이지 데이터: pageData (filteredData를 15개씩 자른 현재 페이지 데이터)
 * 
 * 2. 상태(State) 구성:
 *    - activeCategory / selectedIGs: 도메인 및 이슈그룹 필터링 상태
 *    - activeStatusFilters: 상태별 필터링
 *    - selectedIds: 일괄 처리 대상 관리
 *    - isIgExpanded: 이슈그룹 필터 탭 확장 여부
 * 
 * 3. 주요 핸들러 로직:
 *    - handleSaveDraft / handleSubmit: 데이터 저장 및 제출 (승인 프로세스는 제외)
 *    - handleBatch: 선택 항목 일괄 처리
 * 
 * 4. 변경 사항:
 *    - 이슈그룹/R&R 컬럼 유지 (단, 담당자 초대/지정 기능만 제거)
 *    - 도메인별 4가지 고유 컬러 테마 복구 (상단 탭, 이슈그룹 탭, 테이블 셀 등)
 */

import { useMemo, useState, useRef, useEffect } from "react";
import "@styles/onboarding.css";
import initialMetrics from "@assets/data/onboardingData.js";

import { CategoryTabs, SubTabs } from "@components/UI/TabButton";
import BatchActionBar from "@components/UI/BatchActionBar";
import { showDefaultAlert, showConfirmAlert } from "@components/UI/ServiceAlert";
import ServiceTabs from "@components/UI/ServiceTabs";

import { useAuth } from '@hooks/AuthContext.jsx';

// import { skmApi } from "@utils/Network";
// 모달 임포트
import OnboardingModalShell from "./components/modal/OnboardingModalShell";

// ── 0. API 설정 ──
const USE_DUMMY_API = false;

const requestApi = {
  
  saveDraft: async (id, payload) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 400));
      return { status: true, message: "임시 저장되었습니다.", data: { metricId: id, status: "DRAFT" } };
    }
    // [TODO] 백엔드 API 준비 시 주석 해제
    // const res = await skmApi.put("/onboard", { 
    //   metrics: [{ issue_id: id, value: payload.value, unit: payload.unit }]
    // });
    // return res.data;
    return { status: true };
  },
  submit: async (id) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 500));
      return { status: true, message: "제출되었습니다.", data: { metricId: id, status: "SUBMITTED" } };
    }
    // [TODO] 백엔드 API 준비 시 주석 해제
    // const res = await skmApi.post("/onboard", {
    //   action: 'SUBMIT',
    //   issue_ids: [id]
    // });
    // return res.data;
    return { status: true };
  },
  uploadEvidence: async (id, file) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 700));
      return { status: true, data: { metricId: id, fileName: file.name } };
    }
    // [TODO] 백엔드 API 준비 시 주석 해제
    // const formData = new FormData();
    // formData.append("file", file);
    // formData.append("issue_id", id);
    // const res = await skmApi.post("/onboard/upload", formData, {
    //   headers: { "Content-Type": "multipart/form-data" }
    // });
    // return res.data;
    return { status: true };
  }
};

// ── 2. Constants & Config ──
const categoryTabs = ["전체", "경영일반", "E", "S", "G"];
const rowsPerPage = 15;

const StatusCfg = {
  NOT_STARTED: { label: "미입력", cls: "st-not-started" },
  DRAFT: { label: "작성중", cls: "st-draft" },
  SUBMITTED: { label: "승인대기", cls: "st-submitted" },
  PENDING: { label: "승인대기", cls: "st-submitted" },
  REVIEWED: { label: "검토완료", cls: "st-submitted" },
  APPROVED: { label: "승인완료", cls: "st-approved" },
  REJECTED: { label: "반려", cls: "st-rejected" },
};

const CATEGORY_MAP = {
  environmental: ["Climate", "Energy", "Water", "Pollution", "Circularity", "Biodiversity", "Product_env", "Supply Chain_env", "Sustainable investment", "Carbon_Scope1", "Carbon_Scope2"],
  social: ["Labor", "Safety", "Talent", "Diversity", "Human Rights", "Supply Chain_social", "Community", "Product_resp", "Privacy", "Supply_Audit", "협력사 평가"],
};

const StatusFilterOptions = [
  { key: "DRAFT", label: "작성중", cls: "st-draft", icon: "edit3" },
  { key: "SUBMITTED", label: "승인대기", cls: "st-submitted", icon: "send" },
  { key: "REVIEWED", label: "검토완료", cls: "st-submitted", icon: "check" },
  { key: "REJECTED", label: "반려", cls: "st-rejected", icon: "xCircle" },
];

const Icon = ({ type, size = 14, ...props }) => {
  const icons = {
    chevronDown: <polyline points="6 9 12 15 18 9" />,
    filter: <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />,
    reset: <><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></>,
    edit3: <><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></>,
    send: <><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></>,
    xCircle: <><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></>,
    check: <polyline points="20 6 9 17 4 12" />
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      {icons[type]}
    </svg>
  );
};

const getActions = (status) => {
  const acts = [];
  if (["NotStarted", "DRAFT", "REJECTED", "EDITING_SUBMITTED"].includes(status)) acts.push("저장");
  if (["DRAFT", "REJECTED", "EDITING_SUBMITTED"].includes(status)) acts.push("제출");
  if (status === "SUBMITTED") acts.push("재제출");
  return acts;
};

/** [헬퍼] rnrDisplay: 담당자 텍스트 표시용 */
const rnrDisplay = (assignees = []) => {
  const accepted = assignees.filter(a => a.status === "ACCEPTED");
  if (!accepted.length) return null;
  return accepted.length > 1 ? `${accepted[0].name} 외 ${accepted.length - 1}명` : accepted[0]?.name;
};

const Onboarding = () => {
  const { selectedCompany } = useAuth();
  const [metrics, setMetrics] = useState(() => JSON.parse(localStorage.getItem('onboarding_metrics_dummy')) || initialMetrics);

  const [searchTerm, setSearchTerm] = useState("");
  const [activeFlow, setActiveFlow] = useState('G0'); // 'G0' | 'GENERAL'
  const [activeCategory, setActiveCategory] = useState("전체");
  const [selectedIGs, setSelectedIGs] = useState([]);
  const [activeService, setActiveService] = useState('disclosure');
  const [isIgExpanded, setIsIgExpanded] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState([]);
  const [errors, setErrors] = useState({});
  const [shakeIds, setShakeIds] = useState({});
  const [isStatusPanelOpen, setIsStatusPanelOpen] = useState(false);
  const [activeStatusFilters, setActiveStatusFilters] = useState([]);

  const statusMenuRef = useRef(null);
  const tableWrapRef = useRef(null);

  useEffect(() => localStorage.setItem('onboarding_metrics_dummy', JSON.stringify(metrics)), [metrics]);
  const currentRoleName = selectedCompany?.role || "ESG담당자";

  useEffect(() => {
    const handleOutside = (e) => statusMenuRef.current && !statusMenuRef.current.contains(e.target) && setIsStatusPanelOpen(false);
    if (isStatusPanelOpen) document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [isStatusPanelOpen]);

  const availableIGs = useMemo(() => activeCategory === "전체" ? [] : [...new Set(metrics.filter(m => m.category === activeCategory).map(m => m.issueGroup))], [metrics, activeCategory]);

  const filteredData = useMemo(() => {
    const s = searchTerm.toLowerCase();
    return metrics.filter(m => {
      if ((m.service || 'disclosure') !== activeService) return false;
      if (activeFlow === 'G0' && m.category !== '경영일반') return false;
      if (activeFlow === 'GENERAL' && m.category === '경영일반') return false;
      if (activeStatusFilters.length && !activeStatusFilters.includes(m.status)) return false;
      if (!activeStatusFilters.length) {
        if (activeCategory !== "전체" && m.category !== activeCategory) return false;
        if (selectedIGs.length && !selectedIGs.includes(m.issueGroup)) return false;
      }
      if (s && !m.issueId.toLowerCase().includes(s) && !m.issueName.toLowerCase().includes(s) && !m.checklistQuestion.toLowerCase().includes(s)) return false;
      return true;
    });
  }, [metrics, searchTerm, activeCategory, selectedIGs, activeStatusFilters, activeService]);

  const pageCount = Math.ceil(filteredData.length / rowsPerPage);
  const pageData = useMemo(() => filteredData.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage), [filteredData, currentPage]);

  const rowSpans = useMemo(() => {
    const spans = {};
    pageData.forEach((item, i) => {
      if (i === 0 || pageData[i - 1].issueGroup !== item.issueGroup) {
        let span = 1;
        for (let j = i + 1; j < pageData.length && pageData[j].issueGroup === item.issueGroup; j++) span++;
        spans[i] = span;
      }
    });
    return spans;
  }, [pageData]);

  const handleSaveDraft = async (id) => {
    const m = metrics.find(x => x.issueId === id);
    const res = await requestApi.saveDraft(id, { value: m.value, unit: m.unit });
    if (res.status) {
      setMetrics(prev => prev.map(x => x.issueId === id ? { ...x, status: x.status === "NotStarted" ? "DRAFT" : x.status } : x));
      setErrors(p => ({ ...p, [id]: false }));
      return true;
    }
    return false;
  };

  const handleSubmit = async (id) => {
    const m = metrics.find(x => x.issueId === id);
    if (!m.value?.trim()) {
      setErrors(p => ({ ...p, [id]: true }));
      setShakeIds(p => ({ ...p, [id]: true }));
      setTimeout(() => setShakeIds(p => ({ ...p, [id]: false })), 400);
      return false;
    }
    const res = await requestApi.submit(id);
    if (res.status) {
      setMetrics(prev => prev.map(x => x.issueId === id ? { ...x, status: "SUBMITTED" } : x));
      setErrors(p => ({ ...p, [id]: false }));
      return true;
    }
    return false;
  };

  const handleBatch = async (type) => {
    const actionText = type === 'save' ? '임시저장' : '제출';
    const selectedItems = metrics.filter(m => selectedIds.includes(m.issueId));

    // 1. 상태상 처리가 가능한 대상 필터링
    let targets = [];
    if (type === 'save') {
      targets = selectedItems.filter(m => ["NOT_STARTED", "DRAFT", "REJECTED", "EDITING_SUBMITTED"].includes(m.status));
    } else {
      targets = selectedItems.filter(m => ["DRAFT", "REJECTED", "EDITING_SUBMITTED"].includes(m.status));
    }

    // 2. 입력 값 유무 체크 (임시저장/제출 모두 값이 있는 것만 처리)
    const validTargets = targets.filter(m => m.value?.trim());
    const emptyCount = targets.length - validTargets.length;

    if (validTargets.length === 0) {
      const hasAlreadyDone = selectedItems.some(m => ["SUBMITTED", "APPROVED"].includes(m.status));

      if (emptyCount > 0) {
        showDefaultAlert("알림", `입력된 값이 없는 항목은 ${actionText}할 수 없습니다.`, "info");
      } else if (hasAlreadyDone) {
        showDefaultAlert("알림", "이미 제출(또는 완료)된 상태입니다.", "info");
      } else {
        showDefaultAlert("알림", "처리할 수 있는 항목이 없습니다.", "info");
      }
      return;
    }

    const alreadyDoneCount = selectedItems.filter(m => ["SUBMITTED", "APPROVED"].includes(m.status)).length;
    const notStartedNoValueCount = selectedItems.filter(m => m.status === "NOT_STARTED" && !m.value?.trim()).length;
    const otherNoValueCount = emptyCount - notStartedNoValueCount;

    // 3. 자연스러운 컨펌 문구 구성
    let details = [];
    if (alreadyDoneCount > 0) details.push(`이미 완료된 ${alreadyDoneCount}건`);
    if (notStartedNoValueCount > 0) details.push(`미입력 ${notStartedNoValueCount}건`);
    if (otherNoValueCount > 0) details.push(`내용 없는 ${otherNoValueCount}건`);

    let confirmMsg = `선택한 ${validTargets.length}건의 지표를 ${actionText}하시겠습니까?`;
    if (details.length > 0) {
      confirmMsg += `<br/><small style="color:#94a3b8">(${details.join(", ")} 제외)</small>`;
    }

    const confirm = await showConfirmAlert("일괄 처리", confirmMsg, "question");
    if (!confirm) return;

    // 4. 유효한 대상만 처리
    for (const item of validTargets) {
      if (type === 'save') await handleSaveDraft(item.issueId);
      else await handleSubmit(item.issueId);
    }

    setSelectedIds([]);
    showDefaultAlert("처리 완료", `${validTargets.length}건이 성공적으로 ${actionText}되었습니다.`, "success");
  };
  // OnBoard 컴포넌트 내부 상태 정의 구역
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  // const handleModalSave = async (id, value, file) => {
  //   // 1. 파일이 있으면 먼저 업로드 프로세스 수행
  //   if (file && file.raw !== selectedItem.evidenceFileName) {
  //     await requestApi.uploadEvidence(id, file);
  //   }
  //   // 2. 임시저장 데이터 업데이트 로직 실행
  //   await handleSaveDraft(id, value); // 기존에 정의된 함수 활용 혹은 매개변수 구조에 맞춰 래핑
  //   setIsModalOpen(false);
  // };

  // const handleModalSubmit = async (id, value, file) => {
  //   // 저장 후 제출 시퀀스 실행
  //   if (file) await requestApi.uploadEvidence(id, file);
  //   await handleSaveDraft(id, value);
  //   await handleSubmit(id);
  //   setIsModalOpen(false);
  // };
  const getSubMetrics = (issueGroup) => {
    return metrics.filter(m => m.issueGroup === issueGroup);
  };
  return (
    <div id="onboarding_page">
      <main className="ob-body">
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
          <button 
            type="button"
            className={`ob-btn ${activeFlow === 'G0' ? 'ob-btn-primary' : 'ob-btn-secondary'}`}
            style={{ padding: '8px 20px', borderRadius: '24px', fontSize: '0.95rem' }}
            onClick={() => { setActiveFlow('G0'); setCurrentPage(1); setActiveCategory("전체"); }}
          >
            📋 1단계: G0 (회사 프로파일) 입력
          </button>
          <button 
            type="button"
            className={`ob-btn ${activeFlow === 'GENERAL' ? 'ob-btn-primary' : 'ob-btn-secondary'}`}
            style={{ padding: '8px 20px', borderRadius: '24px', fontSize: '0.95rem' }}
            onClick={() => { setActiveFlow('GENERAL'); setCurrentPage(1); setActiveCategory("전체"); }}
          >
            ✅ 2단계: 일반 온보딩 (DMA 확정 지표)
          </button>
        </div>
        <div className="ob-header-row">
          <div className="ob-header-left">
            <div className="ob-cat-tabs-container">
              <CategoryTabs
                tabs={categoryTabs.map(tab => ({
                  value: tab,
                  label: (
                    <>
                      {tab}
                      {activeCategory === tab && tab !== "전체" && (
                        <div className={`ob-tab-expander ${isIgExpanded ? "expanded" : ""}`} onClick={(e) => { e.stopPropagation(); setIsIgExpanded(!isIgExpanded); }}>
                          <Icon type="chevronDown" strokeWidth="3" />
                        </div>
                      )}
                    </>
                  )
                }))}
                activeTab={activeCategory}
                onTabChange={(val) => {
                  setActiveCategory(val);
                  setSelectedIGs([]);
                  setIsIgExpanded(false);
                  setCurrentPage(1);
                }}
              />

              <div className="ob-status-floating-wrap" ref={statusMenuRef}>
                <button type="button" className={`ob-status-circular-trigger ${isStatusPanelOpen ? "active" : ""} ${activeStatusFilters.length ? "filtering" : ""}`} onClick={() => setIsStatusPanelOpen(!isStatusPanelOpen)}>
                  <Icon type="filter" size={18} />
                  {activeStatusFilters.length > 0 && <div className="ob-status-dot" />}
                </button>
                <div className={`ob-status-radial-menu ${isStatusPanelOpen ? "open" : ""}`}>
                  <button className="ob-radial-item reset" style={{ "--idx": 0, "--total": 4 }} onClick={() => setActiveStatusFilters([])}>
                    <div className="ob-radial-icon"><Icon type="reset" size={12} /></div>
                    <span className="ob-radial-label">해제</span>
                  </button>
                  {StatusFilterOptions.map((opt, i) => (
                    <button key={opt.key} className={`ob-radial-item ${opt.cls} ${activeStatusFilters.includes(opt.key) ? "selected" : ""}`} style={{ "--idx": i + 1, "--total": 4 }}
                      onClick={() => setActiveStatusFilters(p => p.includes(opt.key) ? p.filter(k => k !== opt.key) : [...p, opt.key])}>
                      <div className="ob-radial-icon"><Icon type={opt.icon === "edit-3" ? "edit3" : opt.icon === "send" ? "send" : "xCircle"} size={12} /></div>
                      <span className="ob-radial-label">{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 대분류 필터를 필터들 바로 옆으로 이동 */}
              <div className="ob-service-filter">
                <ServiceTabs 
                  activeService={activeService} 
                  onServiceChange={(service) => {
                    setActiveService(service);
                    setCurrentPage(1);
                    setActiveCategory("전체");
                    setSelectedIGs([]);
                    setIsIgExpanded(false);
                  }} 
                />
              </div>
            </div>
          </div>

          <BatchActionBar
            selectedCount={selectedIds.length}
            actions={[
              { label: '선택 저장', onClick: () => handleBatch('save'), className: 'save' },
              { label: '선택 제출', onClick: () => handleBatch('submit'), className: 'submit' }
            ]}
          />

          <div className="ob-toolbar-right">
            <span className="ob-count">총 {filteredData.length.toLocaleString()}건</span>
            <div className="ob-current-auth-badge">
              <span style={{ fontWeight: 600, color: '#3b82f6' }}>{selectedCompany?.company_name || "A회사"}</span>
              <span className="ob-badge-dot"></span>
              <span>{currentRoleName}</span>
            </div>
            <input type="text" className="ob-search" placeholder="지표 검색..." value={searchTerm} onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }} />
          </div>
        </div>

        <div className={`ob-ig-tabs-wrap ${(isIgExpanded && activeCategory !== "전체" && availableIGs.length) ? "expanded" : ""}`}>
          <div className="ob-ig-tabs-inner">
            <SubTabs
              tabs={availableIGs}
              activeTab={selectedIGs}
              categoryTheme={activeCategory}
              onTabChange={(ig) => {
                setSelectedIGs(p => p.includes(ig) ? p.filter(g => g !== ig) : [...p, ig]);
                setCurrentPage(1);
              }}
            />
          </div>
        </div>

        <div className="ob-table-wrap" ref={tableWrapRef}>
          <table className="ob-table">
            <thead>
              <tr>
                <th style={{ width: "6%" }}><div className="cell-id-head"><input type="checkbox" className="ob-checkbox" checked={selectedIds.length > 0 && selectedIds.length === pageData.length} onChange={(e) => setSelectedIds(e.target.checked ? pageData.map(d => d.issueId) : [])} />ID</div></th>
                <th style={{ width: "12%" }}>이슈그룹 / R&R</th>
                <th style={{ width: "29%" }}>체크리스트 내용</th>
                <th style={{ width: "23%" }}>데이터 입력</th>
                <th style={{ width: "6%" }}>단위</th>
                <th style={{ width: "8%" }}>증빙</th>
                <th style={{ width: "7%" }}>상태</th>
                <th style={{ width: "9%" }}>액션</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map((item, i) => {
                const st = StatusCfg[item.status] || StatusCfg.NOT_STARTED;
                const acts = getActions(item.status);
                return (
                  <tr key={item.issueId} className={`ob-tr-status-${item.status.toLowerCase()} ${rowSpans[i] ? "group-start" : ""}`}>
                    <td className={`cell-id theme-${item.category}`}><div className="cell-id-inner"><input type="checkbox" className="ob-checkbox" checked={selectedIds.includes(item.issueId)} onChange={() => setSelectedIds(p => p.includes(item.issueId) ? p.filter(x => x !== item.issueId) : [...p, item.issueId])} />{item.issueId}</div></td>

                    {rowSpans[i] && (
                      <td className={`cell-issue-group theme-${item.category}`} rowSpan={rowSpans[i]}>
                        <div className="ob-ig-container">
                          <span className={`ob-ig-badge theme-${item.category}`}>{item.issueGroup}</span>
                          <div className="ob-ig-rnr">
                            <span className={`ob-rnr-text theme-${item.category}`}>
                              {rnrDisplay(item.assignees) || "-"}
                            </span>
                          </div>
                        </div>
                      </td>
                    )}

                    <td className="cell-checklist"><span className="checklist-text">{item.checklistQuestion}</span></td>
                    {/* 기존 td 구조를 아래와 같이 변경 */}
                      <td className="ob-td-value">
                        <div 
                          className="ob-value-trigger-cell"
                          onClick={() => {
                            const groupMetrics = getSubMetrics(item.issueGroup);

                            setSelectedItem({
                              parent: item,
                              metrics: groupMetrics
                            });

                            setIsModalOpen(true);
                          }}
                          style={{ 
                            cursor: 'pointer', 
                            padding: '8px', 
                            borderRadius: '4px', 
                            background: item.value ? '#f0faf4' : '#f8fafc',
                            border: '1px dashed #cbd5e1',
                            textAlign: 'center',
                            minHeight: '34px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}
                        >
                          {item.value ? (
                            <span style={{ fontWeight: '600', color: '#1e293b' }}>
                              {item.value} <span style={{ fontSize: '12px', color: '#64748b' }}>{item.unit}</span>
                            </span>
                          ) : (
                            <span style={{ color: '#94a3b8', fontSize: '13px' }}>클릭하여 입력</span>
                          )}
                        </div>
                      </td>
                    <td className="cell-unit"><span className="unit-text">{item.unit !== "-" ? item.unit : ""}</span></td>
                    <td className="cell-evidence">
                      <button type="button" className={`ob-evidence-btn ${item.evidenceAttached ? "attached" : ""}`} onClick={async () => {
                        const res = await requestApi.uploadEvidence(item.issueId, { name: "evidence.pdf" });
                        if (res.status) setMetrics(p => p.map(x => x.issueId === item.issueId ? { ...x, evidenceAttached: !x.evidenceAttached, evidenceFileName: !x.evidenceAttached ? res.data.fileName : "" } : x));
                      }}>
                        {item.evidenceAttached ? "첨부됨" : "미첨부"}
                      </button>
                    </td>
                    <td className="cell-status"><div className="ob-status-wrap"><span className={`ob-status ${st.cls}`}>{st.label}</span></div></td>
                    <td className="cell-action">
                      <div className="ob-actions">
                        {acts.map(label => (
                          <button key={label} type="button" className={`ob-act-btn ob-act-${label === "저장" ? "draft" : "submit"}`}
                            onClick={() => {
                              if (label === "저장") handleSaveDraft(item.issueId);
                              if (label === "제출") handleSubmit(item.issueId);
                              if (label === "재제출") setMetrics(p => p.map(x => x.issueId === item.issueId ? { ...x, status: "DRAFT" } : x));
                            }}>{label}</button>
                        ))}
                        {!acts.length && <span className="ob-action-badge-empty">-</span>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {pageCount > 1 && (
          <div className="ob-pagination">
            <button type="button" className="ob-page-btn ob-page-nav" disabled={currentPage <= 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>‹</button>
            <div className="ob-page-numbers">
              {Array.from({ length: Math.min(10, pageCount) }, (_, i) => {
                const p = Math.max(1, Math.min(pageCount - 9, currentPage - 5)) + i;
                if (p > pageCount || p < 1) return null;
                return <button key={p} type="button" className={`ob-page-btn ${p === currentPage ? "active" : ""}`} onClick={() => setCurrentPage(p)}>{p}</button>;
              })}
            </div>
            <button type="button" className="ob-page-btn ob-page-nav" disabled={currentPage >= pageCount} onClick={() => setCurrentPage(p => Math.min(pageCount, p + 1))}>›</button>
          </div>
        )}
      </main>
      <OnboardingModalShell 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricItem={selectedItem?.parent}
        subMetrics={selectedItem?.metrics || []}
        modalType="MIXED"
        onSaveAndSubmit={async (values, files, status) => {
          if (!selectedItem) return;

          try {
            // 1. 파일 업로드
            for (const issueId in files) {
              const file = files[issueId];

              if (file && file.name) {
                await requestApi.uploadEvidence(issueId, file);
              }
            }
            const targetIds = selectedItem.metrics.map(m => m.issueId);
            // 2. metrics 상태 업데이트
            setMetrics(prev =>
              prev.map(metric => {
                if (targetIds.includes(metric.issueId)) {
                  return {
                    ...metric,
                    value: values[metric.issueId] || "",
                    status: status || "SUBMITTED",
                    evidenceAttached: !!files[metric.issueId],
                    evidenceFileName: files[metric.issueId]?.name || ""
                  };
                }

                return metric;
              })
            );

            // 3. 제출 API
            for (const issueId in values) {
              await requestApi.saveDraft(issueId, {
                value: values[issueId]
              });

              if (status === 'SUBMITTED') {
                await requestApi.submit(issueId);
              }
            }

            showDefaultAlert(
              "완료",
              status === 'DRAFT' ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.",
              "success"
            );

            setIsModalOpen(false);

          } catch (err) {
            console.error(err);

            showDefaultAlert(
              "오류",
              "처리 중 오류가 발생했습니다.",
              "error"
            );
          }
        }}
      />
    </div>
  );
};

export default Onboarding;