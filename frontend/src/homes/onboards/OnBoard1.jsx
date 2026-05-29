import { useMemo, useState, useEffect } from "react";
import "@styles/onboarding1.css";
import initialMetrics from "@assets/data/onboardingData.js";
import { useAuth } from '@hooks/AuthContext.jsx';
import { showDefaultAlert, showConfirmAlert } from "@components/UI/ServiceAlert";
import OnboardingModalShell from "./components/modal/OnboardingModalShell";

const USE_DUMMY_API = false;

const requestApi = {
  saveDraft: async (id, payload) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 400));
      return { status: true, message: "임시 저장되었습니다.", data: { metricId: id, status: "DRAFT" } };
    }
    return { status: true };
  },
  submit: async (id) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 500));
      return { status: true, message: "제출되었습니다.", data: { metricId: id, status: "SUBMITTED" } };
    }
    return { status: true };
  },
  uploadEvidence: async (id, file) => {
    if (USE_DUMMY_API) {
      await new Promise(r => setTimeout(r, 700));
      return { status: true, data: { metricId: id, fileName: file.name } };
    }
    return { status: true };
  }
};

const rowsPerPage = 20;

// Helper to determine fake input type for display
const getInputTypeInfo = (metric) => {
  if (metric.category === 'E') return { label: '계산형', cls: 'calc' };
  if (metric.category === 'S') return { label: '정량 직접입력', cls: 'direct' };
  if (metric.category === 'G') return { label: '계산형', cls: 'calc' };
  return { label: '문장형', cls: 'narrative' };
};

const getStatusInfo = (status) => {
  switch (status) {
    case 'NOT_STARTED': return { label: '미입력', cls: 'not-started' };
    case 'DRAFT': return { label: '입력 진행중', cls: 'draft' };
    case 'SUBMITTED':
    case 'APPROVED': return { label: '입력 완료', cls: 'approved' };
    default: return { label: '미입력', cls: 'not-started' };
  }
};

const OnBoard1 = () => {
  const { selectedCompany } = useAuth();
  const [metrics, setMetrics] = useState(() => JSON.parse(localStorage.getItem('onboarding_metrics_dummy')) || initialMetrics);

  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("전체");
  const [filterStatus, setFilterStatus] = useState("전체");
  const [currentPage, setCurrentPage] = useState(1);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);

  useEffect(() => localStorage.setItem('onboarding_metrics_dummy', JSON.stringify(metrics)), [metrics]);

  const filteredData = useMemo(() => {
    const s = searchTerm.toLowerCase();
    return metrics.filter(m => {
      
      // 1. 입력유형 필터 (mock logic)
      const tInfo = getInputTypeInfo(m);
      if (filterType !== "전체" && tInfo.label !== filterType) return false;
      
      // 2. 상태 필터
      const sInfo = getStatusInfo(m.status);
      if (filterStatus !== "전체" && sInfo.label !== filterStatus) return false;

      // 3. 검색
      if (s && !m.issueId.toLowerCase().includes(s) && !m.issueName.toLowerCase().includes(s) && !m.checklistQuestion.toLowerCase().includes(s)) return false;
      
      return true;
    });
  }, [metrics, searchTerm, filterType, filterStatus]);

  const pageCount = Math.ceil(filteredData.length / rowsPerPage);
  const pageData = useMemo(() => filteredData.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage), [filteredData, currentPage]);

  const rowSpansSub = useMemo(() => {
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

  const rowSpansId = useMemo(() => {
    const spans = {};
    pageData.forEach((item, i) => {
      if (i === 0 || pageData[i - 1].issueId !== item.issueId) {
        let span = 1;
        for (let j = i + 1; j < pageData.length && pageData[j].issueId === item.issueId; j++) span++;
        spans[i] = span;
      }
    });
    return spans;
  }, [pageData]);

  // 대시보드 통계 계산
  const totalCount = metrics.length;
  let completedCount = 0;
  let inProgressCount = 0;
  let notStartedCount = 0;
  
  let typeCount = { direct: 0, calc: 0, narrative: 0 };

  metrics.forEach(m => {
    const s = getStatusInfo(m.status).label;
    if (s === '입력 완료') completedCount++;
    else if (s === '입력 진행중') inProgressCount++;
    else notStartedCount++;

    const t = getInputTypeInfo(m).cls;
    if (t === 'direct') typeCount.direct++;
    else if (t === 'calc') typeCount.calc++;
    else typeCount.narrative++;
  });

  const completionRate = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleResetFilters = () => {
    setSearchTerm("");
    setFilterType("전체");
    setFilterStatus("전체");
    setCurrentPage(1);
  };

  const handleBatch = async (type) => {
    const actionText = type === 'save' ? '임시저장' : '제출';
    const selectedItems = metrics.filter(m => selectedIds.includes(m.issueId));

    if (selectedItems.length === 0) {
      showDefaultAlert("알림", "선택된 항목이 없습니다.", "info");
      return;
    }

    const confirm = await showConfirmAlert("일괄 처리", `선택한 ${selectedItems.length}건을 일괄 ${actionText} 하시겠습니까?`, "question");
    if (!confirm) return;

    for (const item of selectedItems) {
      if (type === 'save') await requestApi.saveDraft(item.issueId, { value: item.value });
      else await requestApi.submit(item.issueId);
    }

    setMetrics(prev => prev.map(m => {
      if (selectedIds.includes(m.issueId)) {
        return { ...m, status: type === 'save' ? (m.status === 'NOT_STARTED' ? 'DRAFT' : m.status) : 'SUBMITTED' };
      }
      return m;
    }));

    setSelectedIds([]);
    showDefaultAlert("처리 완료", `${selectedItems.length}건이 성공적으로 ${actionText}되었습니다.`, "success");
  };

  const rnrDisplay = (assignees = []) => {
    const accepted = assignees.filter(a => a.status === "ACCEPTED");
    if (!accepted.length) return { name: "-", team: "" };
    return { name: accepted[0].name, team: "환경경영팀" }; // Dummy team mapping
  };

  const getSubMetrics = (issueGroup) => {
    return metrics.filter(m => m.issueGroup === issueGroup);
  };

  return (
    <div id="ob1-page">
      <div className="ob1-content-layout">
        
        {/* 2. 좌측 사이드바 대시보드 */}
        <div className="ob1-sidebar">
          <div className="ob1-sidebar-section">
            <div className="ob1-company-name">{selectedCompany?.company_name || "SKM전자(주)"}</div>
            <div className="ob1-report-year">보고연도 2025</div>
            <div className="ob1-status-badge-main">진행 중</div>
          </div>

          <div className="ob1-sidebar-section" style={{ alignItems: 'center' }}>
            <div className="ob1-donut-chart" style={{ "--percent": completionRate }}>
              <div className="ob1-donut-inner">
                <span className="ob1-donut-percent">{completionRate}%</span>
                <span className="ob1-donut-sub">{completedCount} / {totalCount}</span>
              </div>
            </div>
          </div>

          <div className="ob1-sidebar-section ob1-stat-list-vertical">
            <div className="ob1-stat-item-row">
              <span className="ob1-stat-label">전체 지표</span>
              <span className="ob1-stat-val neutral">{totalCount}</span>
            </div>
            <div className="ob1-stat-item-row">
              <span className="ob1-stat-label">입력 완료</span>
              <span className="ob1-stat-val success">{completedCount}</span>
            </div>
            <div className="ob1-stat-item-row">
              <span className="ob1-stat-label">입력 진행중</span>
              <span className="ob1-stat-val warning">{inProgressCount}</span>
            </div>
            <div className="ob1-stat-item-row">
              <span className="ob1-stat-label">미입력</span>
              <span className="ob1-stat-val neutral">{notStartedCount}</span>
            </div>
          </div>

          <div className="ob1-sidebar-section ob1-deadline-box">
            <span className="ob1-deadline-label">마감기한</span>
            <span className="ob1-deadline-date">2026-06-30</span>
            <span className="ob1-deadline-dday">D-37</span>
          </div>

          <div className="ob1-sidebar-section ob1-type-dist">
            <div className="ob1-type-dist-title">입력 유형 분포</div>
            <div className="ob1-type-row">
              <span className="ob1-type-badge direct">정량 직접입력</span>
              <span className="ob1-type-count">{typeCount.direct}</span>
            </div>
            <div className="ob1-type-row">
              <span className="ob1-type-badge calc">계산형</span>
              <span className="ob1-type-count">{typeCount.calc}</span>
            </div>
            <div className="ob1-type-row">
              <span className="ob1-type-badge narrative">문장형</span>
              <span className="ob1-type-count">{typeCount.narrative}</span>
            </div>
          </div>
        </div>

        {/* 우측 메인 컨텐츠 영역 */}
        <div className="ob1-main-area">
          {/* 3. 필터 바 */}
          <div className="ob1-filter-bar">
            <input 
              type="text" 
              className="ob1-search-input" 
              placeholder="지표명, 서브이슈, Metrics ID 검색"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              style={{ flex: 1 }}
            />

        <div className="ob1-filter-group">
          <span className="ob1-filter-label">입력 유형</span>
          <select className="ob1-select" value={filterType} onChange={(e) => { setFilterType(e.target.value); setCurrentPage(1); }}>
            <option value="전체">전체</option>
            <option value="정량 직접입력">정량 직접입력</option>
            <option value="계산형">계산형</option>
            <option value="문장형">문장형</option>
          </select>
        </div>

        <div className="ob1-filter-group">
          <span className="ob1-filter-label">진행상태</span>
          <select className="ob1-select" value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setCurrentPage(1); }}>
            <option value="전체">전체</option>
            <option value="입력 완료">입력 완료</option>
            <option value="입력 진행중">입력 진행중</option>
            <option value="미입력">미입력</option>
          </select>
        </div>

        <button type="button" className="ob1-btn-reset" onClick={handleResetFilters}>
          초기화
        </button>

        <div className="ob1-filter-right" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button type="button" className="ob1-btn-reset" style={{ marginTop: 0 }} onClick={() => handleBatch('save')}>
            일괄 저장
          </button>
          <button type="button" className="ob1-btn-reset" style={{ marginTop: 0, background: '#16a34a', color: '#fff', border: 'none' }} onClick={() => handleBatch('submit')}>
            일괄 제출
          </button>
          <button type="button" className="ob1-btn-excel" style={{ marginTop: 0 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            엑셀 다운로드
          </button>
        </div>
      </div>

      {/* 4. 데이터 테이블 */}
      <div className="ob1-table-container">
        <div className="ob1-table-scroll">
          <table className="ob1-table">
            <thead>
            <tr>
              <th style={{ width: '4%' }}>
                <input 
                  type="checkbox" 
                  checked={selectedIds.length > 0 && selectedIds.length === pageData.length} 
                  onChange={(e) => setSelectedIds(e.target.checked ? pageData.map(d => d.issueId) : [])} 
                />
              </th>
              <th style={{ width: '12%' }}>서브이슈</th>
              <th style={{ width: '10%' }}>Metrics ID</th>
              <th className="ob1-th-name" style={{ width: '42%' }}>지표명</th>
              <th style={{ width: '12%' }}>R&R 담당자</th>
              <th style={{ width: '10%' }}>마감기한</th>
              <th style={{ width: '8%' }}>진행상태</th>
              <th style={{ width: '6%' }}>데이터 입력</th>
            </tr>
          </thead>
          <tbody>
            {pageData.map((item, i) => {
              const tInfo = getInputTypeInfo(item);
              const sInfo = getStatusInfo(item.status);
              const rnr = rnrDisplay(item.assignees);

              return (
                <tr key={`${item.issueId}-${i}`}>
                  {rowSpansId[i] && (
                    <td rowSpan={rowSpansId[i]}>
                      <input 
                        type="checkbox" 
                        checked={selectedIds.includes(item.issueId)} 
                        onChange={() => setSelectedIds(p => p.includes(item.issueId) ? p.filter(x => x !== item.issueId) : [...p, item.issueId])} 
                      />
                    </td>
                  )}
                  {rowSpansSub[i] && <td className="ob1-td-sub" rowSpan={rowSpansSub[i]}>{item.issueGroup}</td>}
                  {rowSpansId[i] && <td className="ob1-td-id" rowSpan={rowSpansId[i]}>{item.issueId}</td>}
                  <td className="ob1-td-name">{item.checklistQuestion}</td>
                  <td className="ob1-td-rnr">
                    <svg className="ob1-rnr-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                    <div className="ob1-rnr-info">
                      <span className="ob1-rnr-name">{rnr.name}</span>
                      <span className="ob1-rnr-team">{rnr.team}</span>
                    </div>
                  </td>
                  <td>2026-06-30</td>
                  <td><span className={`ob1-status-pill ${sInfo.cls}`}>{sInfo.label}</span></td>
                  <td>
                    <button type="button" className="ob1-btn-input" onClick={() => {
                      setSelectedItem({ parent: item, metrics: getSubMetrics(item.issueGroup) });
                      setIsModalOpen(true);
                    }}>
                      입력하기
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
        
        {/* 간이 Pagination */}
        {pageCount > 1 && (
          <div className="ob1-pagination-wrap">
            <span className="ob1-total-count">전체 {filteredData.length}건</span>
            <div className="ob1-page-controls">
              <button className="ob1-page-btn" disabled={currentPage <= 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>‹</button>
              {Array.from({ length: Math.min(5, pageCount) }, (_, i) => {
                const p = Math.max(1, Math.min(pageCount - 4, currentPage - 2)) + i;
                if (p > pageCount || p < 1) return null;
                return <button key={p} className={`ob1-page-btn ${p === currentPage ? 'active' : ''}`} onClick={() => setCurrentPage(p)}>{p}</button>;
              })}
              <button className="ob1-page-btn" disabled={currentPage >= pageCount} onClick={() => setCurrentPage(p => Math.min(pageCount, p + 1))}>›</button>
            </div>
          </div>
        )}
      </div>
      </div> {/* End ob1-main-area */}
      </div> {/* End ob1-content-layout */}

      <OnboardingModalShell 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricItem={selectedItem?.parent}
        subMetrics={selectedItem?.metrics || []}
        modalType="MIXED"
        onSaveAndSubmit={async (values, files, status) => {
          if (!selectedItem) return;

          try {
            for (const issueId in files) {
              if (files[issueId] && files[issueId].name) {
                await requestApi.uploadEvidence(issueId, files[issueId]);
              }
            }
            const targetIds = selectedItem.metrics.map(m => m.issueId);
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

            for (const issueId in values) {
              await requestApi.saveDraft(issueId, { value: values[issueId] });
              if (status === 'SUBMITTED') await requestApi.submit(issueId);
            }

            showDefaultAlert("완료", status === 'DRAFT' ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.", "success");
            setIsModalOpen(false);
          } catch (err) {
            console.error(err);
            showDefaultAlert("오류", "처리 중 오류가 발생했습니다.", "error");
          }
        }}
      />
    </div>
  );
};

export default OnBoard1;
