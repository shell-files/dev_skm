/**
 * Draft.jsx
 * 레이어: Page
 * 역할: SR 템플릿 기반 ESG 보고서 초안을 페이지 단위로 미리보기·편집하고, PDF/PPT 내보내기 및 데이터 추적 패널을 제공하는 보고서 초안 작성 페이지
 *
 * 의존 컴포넌트:
 *   TrendChart — 지표 연도별 추이 SVG 차트
 *   subIssues (registry) — 서브이슈별 SR 페이지 컴포넌트 레지스트리
 *   buildMetricsFromEdits (srHelpers) — 편집값과 DB 지표를 병합해 MetricsMap 반환
 *   exportPdf, exportPptNative (draftExport) — PDF·PPT 내보내기 유틸
 */
import { useEffect, useRef, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import "@styles/draft.css";
import { useSelector, useDispatch } from "react-redux";
import { GET, POST, DELETE } from "@utils/Network";
import { showConfirmAlert, showDefaultAlert } from "@components/UI/ServiceAlert";

import TrendChart from "./srTemplates/core/TrendChart";
import { buildMetricsFromEdits } from "./srTemplates/core/srHelpers";
import { exportPdf, exportPptNative, exportPptImg } from "./srTemplates/core/draftExport";
import { subIssues } from "./srTemplates/registry";
import { PAGES, SR_FIELD_MAP } from "./draftData";
import "@styles/sr-page.css";

const Draft = () => {
  const [currentPid, setCurrentPid] = useState(null);
  const [metricOpen, setMetricOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(0); // 현재 보고서 페이지 인덱스
  const [pdfMode, setPdfMode] = useState(false); // PDF 내보내기용 전체 페이지 렌더 모드
  const [editMetricsByPage, setEditMetricsByPage] = useState({}); // { pageKey: { metric_id: 표시값 } }
  const [editNarrativeByPage, setEditNarrativeByPage] = useState({}); // { pageKey: 본문 }
  const [inlineEdit, setInlineEdit] = useState(null); // 본문 값 인라인 편집 팝업 {id, top, left, width, value}
  const [trackId, setTrackId] = useState(null); // 근거 추적 패널: 선택된 탭 metric_id
  const [trackCtx, setTrackCtx] = useState(null);
  const [panelMetricIds, setPanelMetricIds] = useState([]); // 패널에 표시할 탭 목록
  const [metricTrend, setMetricTrend] = useState({}); // { metricId → { trend, unit } }
  const [savedAt, setSavedAt] = useState(null); // 마지막 저장 시각
  const [metricRows, setMetricRows] = useState([]); // DB에서 로드한 지표 rows
  const [aiSections, setAiSections] = useState({}); // { subIssueId → { reportText, metricIds } }
  const [aiLoading, setAiLoading] = useState(false);

  // ── 상태 정의 ──
  const [isEditing, setIsEditing] = useState(false); // 본문 수정 모드 상태
  const [exportMenuOpen, setExportMenuOpen] = useState(false); // 내보내기 드롭다운 상태

  const dropdownRef = useRef(null);
  const previewRef = useRef(null);
  const navigate = useNavigate();

  // ── SR 템플릿 데이터 연결 (페이지별 웹 편집 → 미리보기/PDF 동일 반영) ──
  const actualMetricRows = metricRows; // API에서 로드한 지표 rows

  // 특정 페이지의 metrics Map / 본문 (페이지 키별 편집값 + 소속 서브이슈 adapter)
  const buildPageMetrics = (pageObj) =>
    buildMetricsFromEdits(pageObj.adapter, editMetricsByPage[pageObj.key], actualMetricRows);
  const buildPageNarrative = (key, subIssueId) => {
    const t = (editNarrativeByPage[key] || "").trim();

    const looksLikeTemplate =
      t.includes("{") && t.includes("}");

    const section = subIssueId && aiSections[subIssueId];

    if (t && !looksLikeTemplate) {
      return t;
    }

    return section?.reportText || t || null;
  };

  const getAiMetricIds = (subIssueId) => {
    const section = subIssueId && aiSections[subIssueId];
    return section ? (section.metricIds || []) : [];
  };

  const STORAGE_KEY = "draft-sr-edits-v1";
  const { reportData, currentYear } = useSelector(state => state.report);
  const selectedCompany = useSelector(state => state.auth.selectedCompany);
  const companyId = selectedCompany?.company_id;
  const year = currentYear;


  useEffect(() => {
    if (!reportData) {
      return;
    }
  }, [reportData]);
  // 저장된 편집값 불러오기: API 우선, 실패 시 localStorage 폴백
  useEffect(() => {
    const load = async () => {
      if (companyId && year) {
        const json = await GET("/draft/load", { companyId, year });
        if (json?.success && json?.data) {
          if (json.data.metrics) setEditMetricsByPage(json.data.metrics);
          if (json.data.narrative) setEditNarrativeByPage(json.data.narrative);
          if (json.data.savedAt) setSavedAt(json.data.savedAt);
          return;
        }
      }
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed.metrics) setEditMetricsByPage(parsed.metrics);
        if (parsed.narrative) setEditNarrativeByPage(parsed.narrative);
        if (parsed.savedAt) setSavedAt(parsed.savedAt);
      } catch (e) { console.warn("저장된 편집값 로드 실패:", e); }
    };
    load();
  }, [companyId, year]);

  // 지표 데이터 로드 (DB → adapter → MetricsMap)
  useEffect(() => {
    if (!companyId || !year) return;
    GET("/draft/metrics", { companyId, year })
      .then(d => { if (d?.success) setMetricRows(d.data || []); });
  }, [companyId, year]);

  // AI 생성 본문 로드 (서브이슈별)
  const loadAiSections = () => {

    if (!companyId || !year) return;
    setAiLoading(true);
    const promises = subIssues.map(si =>
      GET("/draft/section", { companyId, year, subIssueId: si.id })
        .then(d => {
          if (d?.success && d.data != null) {
            setAiSections(prev => ({
              ...prev,
              [si.id]: { reportText: d.data?.reportText || "", metricIds: d.data.metricIds || [] },
            }));
          }
        })
    );

    Promise.all(promises).finally(() => setAiLoading(false));
  };

  useEffect(() => {
    loadAiSections();
  }, [companyId, year]);

  // trackId 선택 시 정량 지표만 연도별 추이 API 조회 (정성은 스킵)
  useEffect(() => {
    if (!trackId || !companyId || !year) return;
    if (/__QL/.test(trackId)) return;
    if (metricTrend[trackId]) return; // 이미 로드됨
    GET("/draft/metric-trend", { companyId, year, metricId: trackId })
      .then(d => {
        if (d?.success && d.data) {
          const rawUnit = d.data.unit ?? "";
          const isKrw = rawUnit.toUpperCase() === "KRW";
          const unit = isKrw ? "억 원" : rawUnit;
          // TrendChart 형식으로 변환: [{y, v}] — KRW는 1억 단위로 스케일
          const trend = (d.data.trend || [])
            .filter(t => t.value != null)
            .map(t => ({
              y: String(t.year),
              v: isKrw ? Math.round((t.value / 100_000_000) * 10) / 10 : t.value,
            }));
          setMetricTrend(prev => ({
            ...prev,
            [trackId]: {
              trend: trend.length > 0 ? trend : null,
              unit,
              isRollup: d.data.isRollup ?? false,
              breakdown: d.data.breakdown || [],
            },
          }));
        }
      });
  }, [trackId, companyId, year]);

  // 페이지 이동 시 현재 페이지의 [data-source] 요소만 스캔해 패널 목록 구성
  // trackId는 리셋 — 패널은 사용자가 직접 클릭할 때만 열린다
  useEffect(() => {
    const container = previewRef.current;
    if (!container) return;
    const seen = new Set();
    container.querySelectorAll("[data-source]").forEach(el => {
      el.getAttribute("data-source").split(",").forEach(id => {
        const t = id.trim();
        if (t && SR_FIELD_MAP[t]) seen.add(t);
      });
    });
    setPanelMetricIds([...seen]);
    setTrackId(null);
  }, [currentPage]);

  // trackId 변경 시 미리보기에서 해당 [data-source] 요소 하이라이트
  useEffect(() => {
    const container = previewRef.current;
    if (!container) return;
    container.querySelectorAll("[data-source].tracking-active").forEach(el => {
      el.classList.remove("tracking-active");
    });
    if (!trackId) return;
    container.querySelectorAll("[data-source]").forEach(el => {
      const srcs = el.getAttribute("data-source").split(",").map(s => s.trim());
      if (srcs.includes(trackId)) el.classList.add("tracking-active");
    });
  }, [trackId, currentPage]);

  // useEffect(() => {
  //   const id = setInterval(() => {
  //     GET("/auth").catch(() => {});
  //   }, 4 * 60 * 1000);
  //   return () => clearInterval(id);
  // }, []);

  // 저장: API 우선, 실패 시 localStorage 폴백
  const handleSaveEdits = async () => {
    const now = new Date().toISOString();
    const pageSubIssueMap = Object.fromEntries(PAGES.map(p => [p.key, p.subIssueId]));
    const payload = { metrics: editMetricsByPage, narrative: editNarrativeByPage, savedAt: now };
    if (companyId && year) {
      const json = await POST("/draft/save", { companyId, year, pageSubIssueMap, ...payload });
      if (json?.success) { setSavedAt(json.savedAt || now); return; }
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      setSavedAt(now);
    } catch (e) {
      console.warn("편집값 저장 실패:", e);
      alert("저장에 실패했습니다. 브라우저 저장 권한을 확인해 주세요.");
    }
  };

  // 되돌리기: DB + localStorage 편집값 전체 삭제
  const handleResetEdits = async () => {
    const confirmed = await showConfirmAlert(
      "수정 내용 전체 삭제",
      "저장된 모든 편집값(지표 수정·본문 수정)이 삭제되고 원본으로 되돌아갑니다. 계속하시겠습니까?",
      "warning"
    );
    if (!confirmed) return;
    if (companyId && year) {
      await DELETE(`/draft/reset?companyId=${companyId}&year=${year}`);
    }
    localStorage.removeItem(STORAGE_KEY);
    setEditMetricsByPage({});
    setEditNarrativeByPage({});
    setSavedAt(null);
    setIsEditing(false);
    showDefaultAlert("되돌리기 완료", "모든 편집 내용이 삭제되었습니다.", "success");
  };

  // ── 페이지 이동 핸들러 (목차 / 이전·다음 / subnav 탭 공용) ──
  const goToPage = (i) => {
    if (i < 0 || i >= PAGES.length || i === currentPage) return;
    setCurrentPage(i);
    // 페이지 전환 시 미리보기 상단으로 스크롤
    requestAnimationFrame(() => {
      document
        .querySelector(".draft-sr-preview")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };
  const prevPage = () => goToPage(currentPage - 1);
  const nextPage = () => goToPage(currentPage + 1);

  // ── 본문(오른쪽 페이지)에서 값/토큰 클릭 → 그 자리에서 인라인 편집 ──
  const openInlineEdit = (e) => {
    // 보기 모드에서 AI 문단(.sr-prose) 클릭 → 현재 패널의 첫 번째로 이동
    if (!isEditing) {
      const proseEl = e.target.closest(".sr-prose");
      if (proseEl) {
        if (panelMetricIds.length > 0 && !trackId) setTrackId(panelMetricIds[0]);
        return;
      }
    }

    const el = e.target.closest("[data-source]");
    if (!el) return;
    const src = el.getAttribute("data-source");
    if (!src) return;

    // ── 보기 모드: 클릭된 지표 선택 (목록은 DOM 스캔으로 이미 구성됨) ──
    if (!isEditing) {
      const clickedId = src.split(",")[0].trim();
      setTrackId(clickedId);
      return;
    }

    // ── 수정 모드: 값 인라인 편집 ──
    if (src.includes(",")) return;
    e.stopPropagation();
    const r = el.getBoundingClientRect();
    const pk = PAGES[currentPage].key;
    const cur = (editMetricsByPage[pk] && editMetricsByPage[pk][src]) ?? "";
    setInlineEdit({ id: src, top: r.bottom + 4, left: r.left, width: Math.max(r.width, 160), value: cur });
  };

  const commitInlineEdit = (val) => {
    if (!inlineEdit) return;
    const pk = PAGES[currentPage].key;
    const id = inlineEdit.id;
    setEditMetricsByPage((prev) => ({ ...prev, [pk]: { ...(prev[pk] || {}), [id]: val } }));
    setInlineEdit(null);
  };

  const steps = [
    { id: 1, title: "벤치마킹 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7" /><line x1="15.5" y1="15.5" x2="21" y2="21" /><line x1="7" y1="13" x2="7" y2="11" /><line x1="10" y1="13" x2="10" y2="8.5" /><line x1="13" y1="13" x2="13" y2="7" /><line x1="6" y1="13" x2="14" y2="13" /></svg>, path: "/benchmk" },
    { id: 2, title: "미디어 분석", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /><polyline points="5,13 8,10 11,12 14,8 19,6" /></svg>, path: "/media" },
    { id: 3, title: "이해관계자 설문", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><polyline points="9,11 10.5,12.5 13,10" /><polyline points="9,16 10.5,17.5 13,15" /><line x1="13" y1="11" x2="16" y2="11" /><line x1="13" y1="16" x2="16" y2="16" /></svg>, path: "/survey" },
    { id: 4, title: "전체 결과", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="20" x2="21" y2="20" /><line x1="3" y1="4" x2="3" y2="20" /><rect x="5" y="13" width="3" height="7" /><rect x="10" y="10" width="3" height="10" /><rect x="15" y="8" width="3" height="12" /><circle cx="19" cy="4" r="3" /><polyline points="17.5,4 18.5,5 21,2.5" /></svg>, path: "/result" },
    { id: 5, title: "보고서 초안", icon: <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z" /></svg>, path: "/draft" },
  ];
  const activeIndex = 4;

  // 수정 모드 진입 시 모든 textarea 높이를 내용에 맞게 재계산
  useEffect(() => {
    if (!isEditing) return;
    const textareas = document.querySelectorAll(".edit-para-textarea");
    textareas.forEach((el) => {
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    });
  }, [isEditing]);

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setExportMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const handleExport = async (type) => {
    setExportMenuOpen(false);
    if (type === "PDF") return exportPdf(setPdfMode);
    if (type === "PPT_NATIVE") return exportPptNative(setPdfMode);
    if (type === "PPT") return exportPptImg(setPdfMode);
  };



  // 문단 선택 핸들러
  const selectParagraph = (pid) => {
    if (isEditing) return; // 수정 모드일 때는 클릭 패널 전환 차단
    if (currentPid === pid) {
      setCurrentPid(null);
      return;
    }
    setCurrentPid(pid);
    setMetricOpen(true);
  };

  // 텍스트 실시간 변경 핸들러
  const handleTextChange = (pid, val) => {
    setTexts(prev => ({
      ...prev,
      [pid]: val
    }));
  };

  const data = currentPid ? paragraphData[currentPid] : null;
  const metric = data ? data.metrics[0] : null;

  // ── 근거 추적 패널: 선택된 SR 지표 정보 ──
  const srTrendData = trackId ? (metricTrend[trackId] || null) : null;
  // metric_id의 atomic 파트가 G로 시작하면 연결(롤업) 지표 (예: E1-06__G0003)
  const srIsRollup = trackId ? /__G\d/.test(trackId) : false;
  // 현재 페이지 metrics에서 선택 지표의 표시값 조회
  const srCurrentVal = (() => {
    if (!trackId) return null;
    const m = buildPageMetrics(PAGES[currentPage]);
    return m[trackId]?.displayValue ?? null;
  })();
  const srMetric = trackId
    ? {
      metricId: trackId,
      disclosure: trackId.includes("__") ? trackId.split("__")[0] : "",
      atomicId: trackId.includes("__") ? trackId.split("__").slice(1).join("__") : trackId,
      name: (SR_FIELD_MAP[trackId] && SR_FIELD_MAP[trackId].label) || trackId,
      subIssueLabel: (SR_FIELD_MAP[trackId] && SR_FIELD_MAP[trackId].subIssueLabel) || "",
      dataType: /__QL/.test(trackId) ? "정성 (Qualitative)" : "정량 (Quantitative)",
      value: srCurrentVal,
      unit: srTrendData?.unit || null,
      trend: srTrendData?.trend || null,
      isRollup: srIsRollup,
      breakdown: srTrendData?.breakdown?.length > 0 ? srTrendData.breakdown : null,
      formula: null,
      aiDesc: null,
    }
    : null;

  return (
    <div id="draft-page" className="draft-container">
      <header className="draft-header">

        <div className="draft-stepper-row">
          {steps.map((step, index) => (
            <Fragment key={step.id}>
              <div
                className={`step-box ${index === activeIndex ? "active" : ""}`}
                onClick={() => { if (index !== activeIndex) navigate(step.path); }}
              >
                <div className="step-icon-circle">{step.icon}</div>
                <div className="step-title-text">{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line"></div>}
            </Fragment>
          ))}
        </div>
      </header>

      <main className="main-content">
        <div className="draft-wrapper">
          <div className="draft-body">

            {/* 문서 영역 */}
            <div className="draft-doc" id="draftDoc">
              <div className="doc-toolbar">
                <div className="doc-breadcrumb">

                </div>
                <div className="doc-actions">
                  {/* 0. AI 본문 새로고침 */}
                  <button
                    className="doc-btn"
                    onClick={loadAiSections}
                    disabled={aiLoading}
                  >
                    {aiLoading ? "로딩 중..." : " AI 본문 갱신"}
                  </button>



                  {/* 2. 독립된 본문 수정 버튼 (Toggle 형태) */}
                  <button
                    className={`doc-btn ${isEditing ? "editing-active" : ""}`}
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    {isEditing ? " 수정 중" : " 본문 수정"}
                  </button>

                  {/* 2. 분리된 파일 내려받기 드롭다운 버튼 */}
                  <div className="save-dropdown-container" ref={dropdownRef}>
                    <button className="doc-btn export-toggle-btn" onClick={() => setExportMenuOpen(!exportMenuOpen)}>
                       파일 내려받기 <span className="save-dropdown-arrow">▼</span>
                    </button>

                    {exportMenuOpen && (
                      <ul className="save-dropdown-menu">
                        <li className="dropdown-item" onClick={() => handleExport("PDF")}> PDF 다운로드</li>
                        <li className="dropdown-item" onClick={() => handleExport("PPT_NATIVE")}> PPT 다운로드</li>
                      </ul>
                    )}
                  </div>
                </div>
              </div>

              <div className="doc-content">

                {/* ── 편집 바 ( 수정 모드) — 본문·값 모두 아래 페이지에서 직접 수정 ── */}
                {isEditing && (
                  <div className="sr-editor">
                    <div className="sr-editor-bar">
                      <div className="sr-editor-hd">
                         <b>{PAGES[currentPage].subIssueLabel}</b> · {PAGES[currentPage].tabLabel} 수정 중
                      </div>
                      <div className="sr-editor-actions">
                        {savedAt && (
                          <span className="sr-editor-saved">
                            저장됨 {new Date(savedAt).toLocaleString("ko-KR", { hour: "2-digit", minute: "2-digit", month: "numeric", day: "numeric" })}
                          </span>
                        )}
                        {/* 1. 되돌리기 — 저장된 편집값 전체 삭제 */}
                        <button className="doc-btn reset-btn" onClick={handleResetEdits}>
                           되돌리기
                        </button>
                        <button className="sr-editor-save" onClick={handleSaveEdits}> 저장</button>
                        <button
                          className="sr-editor-cancel"
                          onClick={() => {
                            const pk = PAGES[currentPage].key;
                            setEditNarrativeByPage(prev => { const n = { ...prev }; delete n[pk]; return n; });
                            setEditMetricsByPage(prev => { const n = { ...prev }; delete n[pk]; return n; });
                            setIsEditing(false);
                          }}
                        > 취소</button>
                        

                      </div>
                    </div>
                    <div className="sr-editor-hint">
                      아래 페이지에서 <b>본문 문장</b>은 클릭해 바로 타이핑하고, <b>KPI·표·차트의 값</b>은 클릭하면 입력창이 떠서 수정됩니다(같은 지표는 모든 위치에 동시 반영). 이 페이지에만 적용됩니다.
                    </div>
                  </div>
                )}



                {/* ── 보고서 미리보기 영역: SR 운영 템플릿 (현재 페이지) ──
                    데이터는 climateMetrics(adapter) + climateNarrative 로만 구동(더미 없음).
                    subNavItems = 페이지 탭(클릭 시 onSubNavClick → goToPage). */}
                <div
                  ref={previewRef}
                  className={"draft-sr-preview" + (isEditing ? " is-editing" : "")}
                  onClick={openInlineEdit}
                >
                  {(() => {
                    const page = PAGES[currentPage];
                    const PageComponent = page.Component;
                    return (
                      <PageComponent
                        {...page.props}
                        mode={isEditing ? "edit" : "render"}
                        metrics={buildPageMetrics(page)}
                        narrativeText={buildPageNarrative(page.key, page.subIssueId)}
                        aiMetricIds={getAiMetricIds(page.subIssueId)}
                        onNarrativeChange={(text) =>
                          setEditNarrativeByPage((prev) => ({ ...prev, [page.key]: text }))
                        }
                        subNavItems={PAGES.map((p, i) => ({ label: p.tabLabel, active: i === currentPage }))}
                        onSubNavClick={(item, i) => goToPage(i)}
                        onNavClick={(item, i) => { /* 상단 메인 nav: 페이지 매핑 없으면 무시 */ }}
                      />
                    );
                  })()}
                </div>

                {/* 본문 인라인 편집 입력창 (값/토큰 클릭 시 그 자리에 표시) */}
                {inlineEdit && (
                  <input
                    autoFocus
                    className="sr-inline-input"
                    style={{ top: inlineEdit.top, left: inlineEdit.left, width: inlineEdit.width }}
                    defaultValue={inlineEdit.value}
                    placeholder={inlineEdit.id}
                    onBlur={(e) => commitInlineEdit(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") e.currentTarget.blur();
                      else if (e.key === "Escape") setInlineEdit(null);
                    }}
                  />
                )}
              </div>
            </div>


            {/* 우측 데이터 추적 패널 */}
            <div className={`draft-panel ${panelMetricIds.length > 0 && trackId && !isEditing ? "open" : ""}`} id="draftPanel">
              {panelMetricIds.length > 0 ? (
                <div className="panel-inner">
                  <div className="panel-hd">
                    <span className="panel-hd-title">데이터 추적</span>
                    <button className="panel-close-btn" onClick={() => { setTrackId(null); }}>✕</button>
                  </div>

                  {/* 지표 선택 — 이 섹션에서 사용된 모든 metric_id */}
                  <div className={`panel-metric-list-wrap${metricOpen ? " open" : ""}`}>
                    <div className="panel-metric-list-hd" onClick={() => setMetricOpen(v => !v)}>
                      <span className="panel-metric-list-label">
                        {trackId
                          ? ((SR_FIELD_MAP[trackId] && SR_FIELD_MAP[trackId].label) || trackId)
                          : "지표 선택"}
                      </span>
                      <span className="panel-metric-list-right">
                        <span className="panel-select-count">{panelMetricIds.length}개</span>
                        <span className="panel-metric-chevron">{metricOpen ? "▲" : "▼"}</span>
                      </span>
                    </div>
                    {metricOpen && (
                      <div className="panel-metric-list">
                        {panelMetricIds.map((id) => (
                          <div
                            key={id}
                            className={`panel-metric-item${trackId === id ? " active" : ""}`}
                            onClick={() => { setTrackId(id); setMetricOpen(false); }}
                          >
                            <span className="panel-metric-item-name">
                              {(SR_FIELD_MAP[id] && SR_FIELD_MAP[id].label) || id}
                            </span>
                            {/__G\d/.test(id) && (
                              <span className="panel-metric-item-badge">연결</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 선택된 탭 상세 */}
                  {srMetric && (
                    <div className="panel-tab-body">
                      <div className="metric-rows-block">
                        <div className="metric-row">
                          <span className="metric-row-key">metric_id</span>
                          <span className="metric-row-val">{srMetric.metricId}</span>
                        </div>
                        <div className="metric-row">
                          <span className="metric-row-key">공시 코드</span>
                          <span className="metric-row-val">{srMetric.disclosure || "—"}</span>
                        </div>
                        <div className="metric-row">
                          <span className="metric-row-key">지표명</span>
                          <span className="metric-row-val">{srMetric.name}</span>
                        </div>
                        <div className="metric-row">
                          <span className="metric-row-key">데이터 유형</span>
                          <span className="metric-row-val" style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                            <span className={`metric-badge ${/__QL/.test(srMetric.metricId) ? "" : "blue"}`}>
                              {/__QL/.test(srMetric.metricId) ? "정성" : "정량"}
                            </span>
                            {srMetric.breakdown && (
                              <span className="metric-badge blue" style={{ opacity: 0.75 }}>연결</span>
                            )}
                          </span>
                        </div>
                        {srMetric.unit && (
                          <div className="metric-row">
                            <span className="metric-row-key">단위</span>
                            <span className="metric-row-val">{srMetric.unit}</span>
                          </div>
                        )}
                      </div>

                      <div className="metric-latest-box">
                        <span className="metric-latest-label">현재 입력 값</span>
                        <span className="metric-latest-val">{srMetric.value ?? "미입력"}</span>
                      </div>

                      {srMetric.trend && srMetric.trend.length > 0 && (
                        <div className="trend-section">
                          <div className="trend-section-title">추이</div>
                          <div className="trend-chart-wrap">
                            <TrendChart trend={srMetric.trend} />
                          </div>
                        </div>
                      )}

                      {srMetric.breakdown && (
                        <div className="panel-subsection">
                          <div className="trend-section-title">
                            구성 법인별 내역
                            <span className="metric-badge blue" style={{ marginLeft: 6, fontSize: 10 }}>연결</span>
                          </div>
                          <table className="breakdown-table">
                            <thead>
                              <tr>
                                <th>법인</th>
                                <th className="breakdown-val">값</th>
                                <th className="breakdown-val">비중</th>
                              </tr>
                            </thead>
                            <tbody>
                              {srMetric.breakdown.map((b, i) => (
                                <tr key={i}>
                                  <td>{b.l}</td>
                                  <td className="breakdown-val">{b.v}</td>
                                  <td className="breakdown-val">{b.contributionRate != null ? `${b.contributionRate}%` : "—"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {srMetric.formula && (
                        <div className="panel-subsection">
                          <div className="trend-section-title">계산식/산출 방식</div>
                          <div className="formula-box">
                            {srMetric.formula.split("\n").map((line, i, arr) => (
                              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {!srMetric.trend && !srMetric.breakdown && !srMetric.formula && (
                        <div className="ai-desc-box muted">
                          이 지표의 상세(추이·구성·산식)는 데이터 소스 연동 시 표시됩니다.
                        </div>
                      )}

                      <div className="panel-section" style={{ paddingLeft: 0, paddingRight: 0, border: "none" }}>
                        <div className="panel-section-title">AI 근거 생성</div>
                        <div className="ai-desc-box">
                          {srMetric.aiDesc || `’${srMetric.name}’ 지표가 이 섹션의 근거로 사용되었습니다. 상세 근거 문구는 데이터 연동 시 자동 생성됩니다.`}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="panel-empty-text">
                  보고서 본문이나 KPI·표·차트의 값을 클릭하면 해당 지표의 근거가 표시됩니다.
                </div>
              )}
            </div>

          </div>
        </div>

      </main>
      {/* ── 페이지 이동 바 (이전 · 다음) ── */}
      <div className="sr-pager">
        <button className="sr-pager-btn" onClick={prevPage} disabled={currentPage === 0}>‹ 이전</button>
        <span className="sr-pager-info">{currentPage + 1} / {PAGES.length}</span>
        <button className="sr-pager-btn" onClick={nextPage} disabled={currentPage === PAGES.length - 1}>다음 ›</button>
      </div>
      {/* ── PDF/PPT 내보내기용 렌더 영역 (화면 밖) ── */}
      {pdfMode && (
        <div id="pdf-render-root" className="pdf-render-root">
          {/* 단일 통합 목차 */}
          <div id="pdf-toc-combined" className="pdf-toc-wrap">
            <div className="pdf-toc-title">ESG 지속가능경영 보고서 · 목차</div>
            <div className="pdf-toc-rule" />
            {subIssues.map((si) => (
              <div key={si.id} className="pdf-toc-si-group">
                <div className="pdf-toc-si-header">{si.label}</div>
                {si.pages.map((p, i) => (
                  <div key={p.key} id={`pdf-tocitem-${si.id}-${p.key}`} className="pdf-toc-item">
                    <span className="pdf-toc-item-num">{String(i + 1).padStart(2, "0")}</span>
                    <span className="pdf-toc-item-tag">{p.tocTag}</span>
                    <span className="pdf-toc-item-label">{p.tabLabel}</span>
                    <span className="pdf-toc-item-arrow">→</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {/* 서브이슈별 본문 */}
          {subIssues.map((si) => (
            <div key={si.id} data-subissue={si.id}>
              {si.pages.map((page) => {
                const PageComponent = page.Component;
                return (
                  <div key={page.key} id={`pdf-sec-${si.id}-${page.key}`}>
                    <PageComponent
                      {...page.props}
                      metrics={buildMetricsFromEdits(si.adapter, editMetricsByPage[page.key], actualMetricRows)}
                      narrativeText={buildPageNarrative(page.key, si.id)}
                      aiMetricIds={getAiMetricIds(si.id)}
                      subNavItems={si.pages.map((p) => ({ label: p.tabLabel, active: p.key === page.key }))}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Draft;