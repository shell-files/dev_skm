import { useEffect, useRef, useState, Fragment } from "react";
import { useNavigate } from "react-router";
import "@styles/draft.css";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import pptxgen from "pptxgenjs";
import { useSelector, useDispatch } from "react-redux";
import { GET, POST } from "@utils/Network";

// ── SR 템플릿 통합 (서브이슈 레지스트리 소비) ──
// 새 서브이슈는 srTemplates/subIssues/<name>/ 폴더 + registry.js 한 줄로 추가됨.
// (데모용 index.jsx / demo.html / metricsExample.js 는 import 하지 않음)
import { subIssues } from "./srTemplates/registry";
import "@styles/sr-page.css";


// (paragraphData, paragraphTexts, TrendChart 등 상단 데이터 정의는 기존과 동일합니다)

const TrendChart = ({ trend }) => {
  const W = 280, H = 60, pad = 20;
  const vals = trend.map((t) => t.v);
  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const range = maxV - minV || 1;
  const pts = trend.map((t, i) => ({
    x: pad + (i / (trend.length - 1)) * (W - pad * 2),
    y: H - pad - ((t.v - minV) / range) * (H - pad * 2),
    year: t.y,
    val: t.v,
  }));
  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <svg className="trend-svg" viewBox={`0 0 ${W} ${H}`} xmlns="http://www.w3.org/2000/svg">
      <path d={pathD} fill="none" stroke="#03A94D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="4" fill="#03A94D" stroke="#fff" strokeWidth="2" />
          <text x={p.x} y={p.y - 9} textAnchor="middle" fontSize="9" fontWeight="700" fill="#334155">
            {p.val.toLocaleString()}
          </text>
          <text x={p.x} y={H - 4} textAnchor="middle" fontSize="9" fill="#94a3b8">
            {p.year}
          </text>
        </g>
      ))}
    </svg>
  );
};

// ── 보고서 페이지 레지스트리 ───────────────────────────────
// 클릭 이동(목차/이전·다음/subnav 탭)의 단일 소스. 페이지 추가 시 항목만 push.
// metrics/narrativeText 는 렌더 시점에 주입(여기엔 정적 메타만 — 더미 수치 없음).
// ── 레지스트리에서 평탄화한 페이지 목록 (클릭 이동/렌더/PDF의 단일 소스) ──
// 각 페이지에 소속 서브이슈 메타(어댑터·편집필드·내보내기명)를 부착.
const PAGES = subIssues.flatMap((si) =>
  si.pages.map((p) => ({
    ...p,
    tocTitle: si.label,
    subIssueId: si.id,
    subIssueLabel: si.label,
    exportName: si.exportName,
    adapter: si.adapter,
    metricFields: si.metricFields,
  }))
);

// metric_id → 지표명/소속 서브이슈 (근거 추적 패널용). metricFields 에서 자동 구성.
const SR_FIELD_MAP = {};
subIssues.forEach((si) =>
  (si.metricFields || []).forEach((f) => {
    SR_FIELD_MAP[f.id] = { label: f.label, subIssueLabel: si.label };
  })
);

// 지표 상세 메타(단위·최신값·추이·구성·산식·AI근거). 실데이터/API 연결 시 여기에 채우면
// 패널에 추이 차트·구성 표·산식이 자동 표시됨. 비어 있으면 "데이터 연동 예정"으로 표기.
// ⚠ 아래는 패널 데모용 예시 값입니다. 실제 지표 API 연동 시 이 값들을 교체하세요.
//    TrendChart 형식: trend: [{ y: "연도", v: 숫자값 }, ...]
const metricMeta = {
  "E1-05__G0003": {
    unit: "tCO₂eq", latest: "112,500",
    trend: [{ y: "2021", v: 128000 }, { y: "2022", v: 121000 }, { y: "2023", v: 116000 }, { y: "2024", v: 112500 }],
    breakdown: [{ l: "Scope 1 (직접)", v: "41,200" }, { l: "Scope 2 (간접)", v: "71,300" }],
    formula: "Scope 1 + Scope 2\nE1-05__G0001 + E1-05__G0002",
    aiDesc: "기준연도 온실가스 총배출량(연결 기준)으로, 감축 목표·로드맵 산정의 기준점이 되는 핵심 지표입니다.",
  },
  "E1-06__G0003": {
    unit: "tCO₂eq", latest: "104,800",
    trend: [{ y: "2021", v: 128000 }, { y: "2022", v: 121000 }, { y: "2023", v: 112000 }, { y: "2024", v: 104800 }],
    breakdown: [{ l: "Scope 1 (직접)", v: "37,900" }, { l: "Scope 2 (간접)", v: "66,900" }],
    formula: "Scope 1 + Scope 2\nE1-06__G0001 + E1-06__G0002",
    aiDesc: "보고연도 온실가스 총배출량으로, 기준연도 대비 감축 성과를 정량적으로 보여줍니다.",
  },
  "E1-06__G0004": {
    unit: "tCO₂eq", latest: "7,200",
    trend: [{ y: "2022", v: 7000 }, { y: "2023", v: 9000 }, { y: "2024", v: 7200 }],
    breakdown: [{ l: "에너지 효율화", v: "3,100" }, { l: "재생에너지 전환", v: "2,800" }, { l: "공정 개선", v: "1,300" }],
    formula: "전년도 배출량 − 보고연도 배출량",
    aiDesc: "전년 대비 절대 감축량으로, 연간 감축 노력의 실효성을 나타냅니다.",
  },
  "E1-06__G0005": {
    unit: "%", latest: "18.1",
    trend: [{ y: "2021", v: 0 }, { y: "2022", v: 5.5 }, { y: "2023", v: 12.5 }, { y: "2024", v: 18.1 }],
    breakdown: [{ l: "기준연도 대비 누적 감축률", v: "18.1%" }],
    formula: "(기준연도 배출량 − 보고연도 배출량) / 기준연도 배출량 × 100",
    aiDesc: "기준연도 대비 누적 감축률로, 중장기 감축 경로상의 진척도를 보여줍니다.",
  },
  "E1-07__G0003": {
    unit: "%", latest: "31.4",
    trend: [{ y: "2021", v: 12 }, { y: "2022", v: 19 }, { y: "2023", v: 26 }, { y: "2024", v: 31.4 }],
    breakdown: [{ l: "PPA", v: "14.0%" }, { l: "REC 구매", v: "10.4%" }, { l: "자가발전", v: "7.0%" }],
    formula: "재생에너지 사용량 / 총 전력 사용량 × 100",
    aiDesc: "재생에너지 전환율로, RE100 및 Scope 2 감축 경로의 핵심 동인입니다.",
  },
};


// 편집 입력값(displayValue) + 실제 row 를 해당 서브이슈 adapter 로 합쳐 metrics Map 생성.
// 빈 입력은 미포함(템플릿이 토큰/—). 숫자 추출 가능하면 차트 스케일용 value 로.
function buildMetricsFromEdits(adapter, editMetrics, rows) {
  const map = { ...adapter(rows) };
  Object.entries(editMetrics || {}).forEach(([id, raw]) => {
    const t = (raw ?? "").trim();
    if (!t) return;
    const n = parseFloat(t.replace(/[^0-9.\-]/g, ""));
    map[id] = {
      ...(map[id] || {}),
      displayValue: t,
      value: Number.isNaN(n) ? t : n,
      status: "DRAFT",
    };
  });
  return map;
}

const Draft = () => {
  const [currentPid, setCurrentPid] = useState(null);
  const [metricOpen, setMetricOpen] = useState(true);
  const [currentPage, setCurrentPage] = useState(0); // 현재 보고서 페이지 인덱스
  const [pdfMode, setPdfMode] = useState(false); // PDF 내보내기용 전체 페이지 렌더 모드
  const [editMetricsByPage, setEditMetricsByPage] = useState({}); // { pageKey: { metric_id: 표시값 } }
  const [editNarrativeByPage, setEditNarrativeByPage] = useState({}); // { pageKey: 본문 }
  const [inlineEdit, setInlineEdit] = useState(null); // 본문 값 인라인 편집 팝업 {id, top, left, width, value}
  const [trackId, setTrackId] = useState(null); // 근거 추적 패널: 선택된 metric_id
  const [trackCtx, setTrackCtx] = useState(null); // { pageLabel, area, clicked, value }
  const [savedAt, setSavedAt] = useState(null); // 마지막 저장 시각
  const [metricRows, setMetricRows] = useState([]); // DB에서 로드한 지표 rows
  const [aiSections, setAiSections] = useState({}); // { subIssueId → { reportText, metricIds } }

  // ── 상태 정의 ──
  const [isEditing, setIsEditing] = useState(false); // 본문 수정 모드 상태
  const [exportMenuOpen, setExportMenuOpen] = useState(false); // 내보내기 드롭다운 상태

  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // ── SR 템플릿 데이터 연결 (페이지별 웹 편집 → 미리보기/PDF 동일 반영) ──
  const actualMetricRows = metricRows; // API에서 로드한 지표 rows

  // 특정 페이지의 metrics Map / 본문 (페이지 키별 편집값 + 소속 서브이슈 adapter)
  const buildPageMetrics = (pageObj) =>
    buildMetricsFromEdits(pageObj.adapter, editMetricsByPage[pageObj.key], actualMetricRows);
  const buildPageNarrative = (key, subIssueId) => {
    const t = (editNarrativeByPage[key] || "").trim();
    if (t) return t;
    const section = subIssueId && aiSections[subIssueId];
    return section ? section.reportText : null;
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
      // navigate('/result');
      console.log("데이터 없음")
      console.log(selectedCompany.company_id, year)
      return;
    }
  }, [reportData]);
  // 저장된 편집값 불러오기: API 우선, 실패 시 localStorage 폴백
  useEffect(() => {
    const load = async () => {
      if (companyId && year) {
        const json = await GET("/draft/load", { companyId, year });
        // console.log(json)
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
  useEffect(() => {
    if (!companyId || !year) return;
    subIssues.forEach(si => {
      GET("/draft/section", { companyId, year, subIssueId: si.id })
        .then(d => {
          if (d?.success && d.data?.reportText) {
            setAiSections(prev => ({
              ...prev,
              [si.id]: { reportText: d.data.reportText, metricIds: d.data.metricIds || [] },
            }));
          }
        });
    });
  }, [companyId, year]);

  // 저장: API 우선, 실패 시 localStorage 폴백
  const handleSaveEdits = async () => {
    const now = new Date().toISOString();
    const payload = { metrics: editMetricsByPage, narrative: editNarrativeByPage, savedAt: now };
    if (companyId && year) {
      const json = await POST("/draft/save", { companyId, year, ...payload });
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
    const el = e.target.closest("[data-source]");
    if (!el) return; // 본문의 일반 문구(토큰 아님)는 data-source가 없어 contentEditable 편집으로 넘어감
    const src = el.getAttribute("data-source");
    if (!src) return;

    // ── 보기 모드: 근거 추적 패널 열기 ──
    if (!isEditing) {
      const id = src.split(",")[0].trim();
      const m = buildPageMetrics(PAGES[currentPage]);
      const value = (m[id] && m[id].displayValue) || null;
      const area = el.closest(".sr-prose")
        ? "본문"
        : (el.tagName === "TD" || el.closest(".sr-tbl"))
          ? "데이터 표"
          : "지표 시각화(KPI·차트)";
      const clicked = (el.innerText || "").trim().slice(0, 80);
      if (trackId === id) { setTrackId(null); return; } // 같은 항목 재클릭 시 닫기
      setTrackId(id);
      setTrackCtx({ pageLabel: PAGES[currentPage].subIssueLabel + " · " + PAGES[currentPage].tabLabel, area, clicked, value });
      setMetricOpen(true);
      return;
    }

    // ── 수정 모드: 값 인라인 편집 ──
    if (src.includes(",")) return; // 파생/복합값(예: 기준연도 대비 %)은 편집 제외
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

    if (type === "PDF") {
      // 1) 모든 서브이슈의 페이지를 화면 밖에 렌더(캡처용) → React 리렌더/레이아웃 대기
      setPdfMode(true);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      await new Promise((r) => setTimeout(r, 120));

      try {
        const root = document.getElementById("pdf-render-root");
        if (!root) return;

        const renderEl = (el) =>
          html2canvas(el, {
            scale: 2, useCORS: true, allowTaint: true, backgroundColor: "#ffffff",
            width: el.offsetWidth, height: el.offsetHeight, windowWidth: el.offsetWidth,
          });

        // ── 전체 서브이슈를 단일 PDF 파일로 통합 ──
        const pdf = new jsPDF("l", "mm", "a4");
        const pageW = pdf.internal.pageSize.getWidth();
        const pageH = pdf.internal.pageSize.getHeight();
        let pdfFirstPage = true; // jsPDF 기본 1페이지 → 첫 콘텐츠엔 addPage 불필요

        const pendingTocLinks = []; // { tocPdfPage, key, x, y, w, h }
        const pendingSubnavLinks = []; // { onPdfPage, targetKey, x, y, w, h }
        const globalPdfPageOf = {}; // page.key → 절대 페이지 번호

        for (const si of subIssues) {
          // 서브이슈 목차 페이지
          const tocEl = root.querySelector(`#pdf-toc-${si.id}`);
          if (tocEl) {
            if (!pdfFirstPage) pdf.addPage();
            pdfFirstPage = false;
            const tocPdfPage = pdf.getNumberOfPages();

            const tocCanvas = await renderEl(tocEl);
            const tocImgH = Math.min((tocCanvas.height * pageW) / tocCanvas.width, pageH);
            pdf.addImage(tocCanvas.toDataURL("image/png"), "PNG", 0, 0, pageW, tocImgH);

            const tocRect = tocEl.getBoundingClientRect();
            const tocMmPerPx = pageW / tocRect.width;
            si.pages.forEach((p) => {
              const item = root.querySelector(`#pdf-tocitem-${si.id}-${p.key}`);
              if (!item) return;
              const r = item.getBoundingClientRect();
              pendingTocLinks.push({
                tocPdfPage, key: p.key,
                x: (r.left - tocRect.left) * tocMmPerPx,
                y: (r.top - tocRect.top) * tocMmPerPx,
                w: r.width * tocMmPerPx,
                h: r.height * tocMmPerPx,
              });
            });
          }

          // 서브이슈 본문 페이지들
          for (const page of si.pages) {
            const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
            if (!sec) continue;
            const canvas = await renderEl(sec);
            if (!pdfFirstPage) pdf.addPage();
            pdfFirstPage = false;
            const thisPdfPage = pdf.getNumberOfPages();
            globalPdfPageOf[page.key] = thisPdfPage;

            const imgH = (canvas.height * pageW) / canvas.width;
            pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, pageW, imgH);

            const secRect = sec.getBoundingClientRect();
            const mmPerPx = pageW / secRect.width;
            sec.querySelectorAll(".sr-subnav span:not(.dot)").forEach((tab, ti) => {
              if (ti >= si.pages.length) return;
              const r = tab.getBoundingClientRect();
              pendingSubnavLinks.push({
                onPdfPage: thisPdfPage,
                x: (r.left - secRect.left) * mmPerPx,
                y: (r.top - secRect.top) * mmPerPx,
                w: r.width * mmPerPx,
                h: r.height * mmPerPx,
                targetKey: si.pages[ti].key,
              });
            });
          }
        }

        // 모든 페이지 추가 후 링크 일괄 주입
        pendingTocLinks.forEach((l) => {
          const t = globalPdfPageOf[l.key];
          if (!t) return;
          pdf.setPage(l.tocPdfPage);
          pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
        });
        pendingSubnavLinks.forEach((l) => {
          const t = globalPdfPageOf[l.targetKey];
          if (!t) return;
          pdf.setPage(l.onPdfPage);
          pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
        });

        pdf.save("esg-sustainability-report.pdf");
      } finally {
        setPdfMode(false);
      }
      return;
    }
    if (type === "PPT_NATIVE") {
      // 편집형: DOM을 읽어 텍스트=텍스트박스, 표=네이티브 표, 카드=도형+텍스트.
      // 로드맵/게이지처럼 그래픽 블록만 이미지로 삽입.
      setPdfMode(true);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      await new Promise((r) => setTimeout(r, 120));
      try {
        const root = document.getElementById("pdf-render-root");
        if (!root) return;
        const SLIDE_W = 11.69, SLIDE_H = 8.27;
        const FONT = "Malgun Gothic"; // PPT 기본 한글 폰트(없으면 PowerPoint가 대체)

        const renderEl = (el) =>
          html2canvas(el, {
            scale: 2, useCORS: true, allowTaint: true, backgroundColor: null,
            width: el.offsetWidth, height: el.offsetHeight, windowWidth: el.offsetWidth
          });
        const toHex = (rgb) => {
          const m = (rgb || "").match(/\d+(\.\d+)?/g);
          if (!m || m.length < 3) return null;
          const [r, g, b] = m.map(Number);
          return [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase();
        };

        // ── 전체 서브이슈를 단일 PPTX 파일로 통합 ──
        const pptx = new pptxgen();
        pptx.defineLayout({ name: "A4L", width: SLIDE_W, height: SLIDE_H });
        pptx.layout = "A4L";
        let slideNo = 0;

        const makeCtx = (sec) => {
          const pageRect = sec.getBoundingClientRect();
          const k = SLIDE_W / pageRect.width;
          const pos = (el) => { const r = el.getBoundingClientRect(); return { x: (r.left - pageRect.left) * k, y: (r.top - pageRect.top) * k, w: r.width * k, h: r.height * k }; };
          const fpt = (el) => Math.max(6, parseFloat(getComputedStyle(el).fontSize) * k * 72);
          return { k, pos, fpt };
        };
        const addTextEl = (slide, el, ctx, extra = {}) => {
          const txt = (el.innerText || "").trim();
          if (!txt) return;
          const cs = getComputedStyle(el);
          const p = ctx.pos(el);
          slide.addText(txt, {
            x: p.x, y: p.y, w: p.w, h: Math.max(p.h, 0.18),
            fontSize: ctx.fpt(el), fontFace: FONT,
            bold: parseInt(cs.fontWeight, 10) >= 600,
            color: toHex(cs.color) || "16241F",
            align: cs.textAlign === "right" ? "right" : cs.textAlign === "center" ? "center" : "left",
            valign: "top", margin: 1, ...extra,
          });
        };

        const buildSlide = async (sec) => {
          const ctx = makeCtx(sec);
          const slide = pptx.addSlide();

          const topband = sec.querySelector(".sr-topband");
          if (topband) { const p = ctx.pos(topband); slide.addShape(pptx.ShapeType.rect, { x: p.x, y: p.y, w: p.w, h: Math.max(p.h, 0.04), fill: { color: toHex(getComputedStyle(topband).backgroundColor) || "16241F" }, line: { width: 0 } }); }

          const subnav = sec.querySelector(".sr-subnav");
          if (subnav) addTextEl(slide, subnav, ctx, { color: "6b8378" });

          ["sr-eyebrow", "sr-title", "sr-title-en"].forEach((cls) => { const el = sec.querySelector("." + cls); if (el) addTextEl(slide, el, ctx); });

          const prose = sec.querySelector(".sr-prose");
          if (prose) addTextEl(slide, prose, ctx);

          // KPI 카드
          sec.querySelectorAll(".sr-kpi").forEach((card) => {
            const cs = getComputedStyle(card); const p = ctx.pos(card);
            slide.addShape(pptx.ShapeType.roundRect, { x: p.x, y: p.y, w: p.w, h: p.h, rectRadius: 0.05, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { color: toHex(cs.borderTopColor) || "D7E2DC", width: 0.5 } });
            ["kl", "kv", "kd"].forEach((c) => { const el = card.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
          });

          // 표 캡션 + 네이티브 표
          sec.querySelectorAll(".sr-tcap").forEach((cap) => addTextEl(slide, cap, ctx, { bold: true }));
          sec.querySelectorAll("table.sr-tbl").forEach((tbl) => {
            const p = ctx.pos(tbl);
            const rows = [];
            tbl.querySelectorAll("tr").forEach((tr) => {
              const cells = [];
              tr.querySelectorAll("th,td").forEach((td) => {
                const cs = getComputedStyle(td);
                cells.push({
                  text: (td.innerText || "").trim(), options: {
                    bold: td.tagName === "TH" || parseInt(cs.fontWeight, 10) >= 600,
                    color: toHex(cs.color) || "16241F",
                    fill: { color: td.tagName === "TH" ? "EAF3EE" : "FFFFFF" },
                    align: cs.textAlign === "right" ? "right" : cs.textAlign === "center" ? "center" : "left",
                    fontSize: Math.max(7, ctx.fpt(td)), valign: "middle",
                  }
                });
              });
              if (cells.length) rows.push(cells);
            });
            const headCells = tbl.querySelectorAll("tr:first-child th, tr:first-child td");
            const colW = Array.from(headCells).map((c) => c.getBoundingClientRect().width * ctx.k);
            if (rows.length) slide.addTable(rows, { x: p.x, y: p.y, w: p.w, colW: colW.length ? colW : undefined, border: { type: "solid", pt: 0.5, color: "D7E2DC" }, fontFace: FONT, autoPage: false, valign: "middle" });
          });

          // 그래픽 블록은 이미지로(로드맵·게이지)
          for (const sel of [".sr-road", ".sr-gauge"]) {
            const el = sec.querySelector(sel);
            if (el) { const p = ctx.pos(el); const cv = await renderEl(el); slide.addImage({ data: cv.toDataURL("image/png"), x: p.x, y: p.y, w: p.w, h: p.h }); }
          }

          // 노트 카드(편집형)
          sec.querySelectorAll(".sr-note-card").forEach((card) => {
            const cs = getComputedStyle(card); const p = ctx.pos(card);
            slide.addShape(pptx.ShapeType.roundRect, { x: p.x, y: p.y, w: p.w, h: p.h, rectRadius: 0.04, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { color: "D7E2DC", width: 0.5 } });
            ["l", "b", "s"].forEach((c) => { const el = card.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
          });

          // 이행수단
          const measures = sec.querySelector(".sr-measures");
          if (measures) {
            const cs = getComputedStyle(measures); const p = ctx.pos(measures);
            slide.addShape(pptx.ShapeType.rect, { x: p.x, y: p.y, w: p.w, h: p.h, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { width: 0 } });
            ["ml", "mv"].forEach((c) => { const el = measures.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
          }

          const foot = sec.querySelector(".sr-foot");
          if (foot && (foot.innerText || "").trim()) addTextEl(slide, foot, ctx, { color: "8aa399" });

          return slide;
        };

        for (const si of subIssues) {
          // 서브이슈 목차 슬라이드
          const tocSlide = pptx.addSlide(); slideNo++;
          tocSlide.addText(si.label || si.id, { x: 0.6, y: 0.5, w: SLIDE_W - 1.2, h: 0.6, fontSize: 24, bold: true, color: "1B5E44", fontFace: FONT });
          tocSlide.addText("목차", { x: 0.6, y: 1.2, w: 3, h: 0.4, fontSize: 13, color: "6B8378", fontFace: FONT });

          const tocItems = [];
          for (const page of si.pages) {
            const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
            if (!sec) continue;
            await buildSlide(sec);
            slideNo++;
            tocItems.push({ label: page.tabLabel || page.key, slide: slideNo });
          }
          tocItems.forEach((it, i) => {
            tocSlide.addText(`${i + 1}. ${it.label}`, { x: 0.8, y: 1.7 + i * 0.5, w: SLIDE_W - 1.6, h: 0.42, fontSize: 15, color: "16241F", fontFace: FONT, hyperlink: { slide: it.slide } });
          });
        }

        await pptx.writeFile({ fileName: "esg-sustainability-report-편집형.pptx" });
      } finally {
        setPdfMode(false);
      }
      return;
    } 
    if (type === "PPT") {
      // PDF와 동일하게 화면 밖 풀사이즈 렌더 → 각 페이지를 한 슬라이드 이미지로
      setPdfMode(true);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      await new Promise((r) => setTimeout(r, 120));
      try {
        const root = document.getElementById("pdf-render-root");
        if (!root) return;

        const renderEl = (el) =>
          html2canvas(el, {
            scale: 2, useCORS: true, allowTaint: true, backgroundColor: "#ffffff",
            width: el.offsetWidth, height: el.offsetHeight, windowWidth: el.offsetWidth,
          });

        const SLIDE_W = 11.69, SLIDE_H = 8.27; // A4 가로(inch) — 보고서 페이지 비율과 동일

        // ── 전체 서브이슈를 단일 PPTX 파일로 통합 ──
        const pptx = new pptxgen();
        pptx.defineLayout({ name: "A4L", width: SLIDE_W, height: SLIDE_H });
        pptx.layout = "A4L";

        const slideOf = {};       // page.key → 슬라이드 번호(1-based, 전체)
        const createdSlides = {}; // 슬라이드 번호 → 슬라이드 객체
        let slideNo = 0;
        const tocAreas = [];      // { tocSlideNo, key, x, y, w, h }
        const subnavAreas = [];   // { onSlide, targetKey, x, y, w, h }

        for (const si of subIssues) {
          // 서브이슈 목차 슬라이드
          const tocEl = root.querySelector(`#pdf-toc-${si.id}`);
          if (tocEl) {
            const tocCanvas = await renderEl(tocEl);
            const tocSlide = pptx.addSlide(); slideNo++; createdSlides[slideNo] = tocSlide;
            const tocSlideNo = slideNo;
            tocSlide.addImage({ data: tocCanvas.toDataURL("image/png"), x: 0, y: 0, w: SLIDE_W, h: SLIDE_H });

            const tocRect = tocEl.getBoundingClientRect();
            const inPerPx = SLIDE_W / tocRect.width;
            si.pages.forEach((p) => {
              const item = root.querySelector(`#pdf-tocitem-${si.id}-${p.key}`);
              if (!item) return;
              const r = item.getBoundingClientRect();
              tocAreas.push({
                tocSlideNo, key: p.key,
                x: (r.left - tocRect.left) * inPerPx,
                y: (r.top - tocRect.top) * inPerPx,
                w: r.width * inPerPx,
                h: r.height * inPerPx,
              });
            });
          }

          // 서브이슈 본문 슬라이드들
          for (const page of si.pages) {
            const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
            if (!sec) continue;
            const canvas = await renderEl(sec);
            const slide = pptx.addSlide(); slideNo++; createdSlides[slideNo] = slide;
            slideOf[page.key] = slideNo;
            slide.addImage({ data: canvas.toDataURL("image/png"), x: 0, y: 0, w: SLIDE_W, h: SLIDE_H });

            const secRect = sec.getBoundingClientRect();
            const inPerPx = SLIDE_W / secRect.width;
            sec.querySelectorAll(".sr-subnav span:not(.dot)").forEach((tab, ti) => {
              if (ti >= si.pages.length) return;
              const r = tab.getBoundingClientRect();
              subnavAreas.push({
                onSlide: slideNo,
                targetKey: si.pages[ti].key,
                x: (r.left - secRect.left) * inPerPx,
                y: (r.top - secRect.top) * inPerPx,
                w: r.width * inPerPx,
                h: r.height * inPerPx,
              });
            });
          }
        }

        // 모든 슬라이드 추가 후 링크 일괄 주입
        const addLink = (slide, a, t) =>
          slide.addShape(pptx.ShapeType.rect, {
            x: a.x, y: a.y, w: a.w, h: Math.max(a.h, 0.12),
            fill: { color: "FFFFFF", transparency: 100 },
            line: { color: "FFFFFF", transparency: 100, width: 0 },
            hyperlink: { slide: t },
          });
        tocAreas.forEach((a) => {
          const t = slideOf[a.key];
          const s = createdSlides[a.tocSlideNo];
          if (t && s) addLink(s, a, t);
        });
        subnavAreas.forEach((a) => {
          const t = slideOf[a.targetKey];
          const s = createdSlides[a.onSlide];
          if (t && s) addLink(s, a, t);
        });

        await pptx.writeFile({ fileName: "esg-sustainability-report.pptx" });
      } finally {
        setPdfMode(false);
      }
      return;
    }
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

  // ── 근거 추적 패널: 선택된 SR 지표 정보(실데이터 기반, 더미 없음) ──
  const srMeta = trackId ? (metricMeta[trackId] || null) : null;
  const srMetric = trackId
    ? {
      metricId: trackId,
      disclosure: trackId.includes("__") ? trackId.split("__")[0] : "",
      atomicId: trackId.includes("__") ? trackId.split("__").slice(1).join("__") : trackId,
      name: (SR_FIELD_MAP[trackId] && SR_FIELD_MAP[trackId].label) || trackId,
      subIssueLabel: (SR_FIELD_MAP[trackId] && SR_FIELD_MAP[trackId].subIssueLabel) || "",
      dataType: /__QL/.test(trackId) ? "정성 (Qualitative)" : "정량 (Quantitative)",
      value: (trackCtx && trackCtx.value) || null,
      unit: (srMeta && srMeta.unit) || null,
      latest: (srMeta && srMeta.latest) || null,
      trend: (srMeta && srMeta.trend) || null,
      breakdown: (srMeta && srMeta.breakdown) || null,
      formula: (srMeta && srMeta.formula) || null,
      aiDesc: (srMeta && srMeta.aiDesc) || null,
    }
    : null;

  return (
    <div className="draft-container">
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
                  {/* 1. 독립된 본문 수정 버튼 (Toggle 형태) */}
                  <button
                    className={`doc-btn ${isEditing ? "editing-active" : ""}`}
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    {isEditing ? "💾 수정 완료" : "✏️ 본문 수정"}
                  </button>

                  {/* 2. 분리된 파일 내려받기 드롭다운 버튼 */}
                  <div className="save-dropdown-container" ref={dropdownRef}>
                    <button className="doc-btn export-toggle-btn" onClick={() => setExportMenuOpen(!exportMenuOpen)}>
                      📥 파일 내려받기 <span className="save-dropdown-arrow">▼</span>
                    </button>

                    {exportMenuOpen && (
                      <ul className="save-dropdown-menu">
                        <li className="dropdown-item" onClick={() => handleExport("PDF")}>📄 PDF 다운로드</li>
                        <li className="dropdown-item" onClick={() => handleExport("PPT_NATIVE")}>📊 PPT 다운로드</li>
                      </ul>
                    )}
                  </div>
                </div>
              </div>

              <div className="doc-content">
                <h1 className="doc-title">기후목표·전환계획</h1>
                <p className="doc-subtitle">전환 리스크에 선제적으로 대응하는 넷제로 로드맵</p>

                {/* 목차 */}
                <div id="toc-section" className="toc-section">
                  <h2 className="toc-heading">
                    <span>📋</span> 목차
                  </h2>
                  <ol className="toc-list">
                    {PAGES.map((page, idx) => {
                      const active = idx === currentPage;
                      return (
                        <li key={page.key} id={`toc-item-${page.key}`}>
                          <button
                            className={`toc-item-btn${active ? " active" : ""}`}
                            onClick={(e) => { e.stopPropagation(); goToPage(idx); }}
                          >
                            <span className="toc-item-num">
                              {String(idx + 1).padStart(2, "0")}
                            </span>
                            <span className="para-chip blue toc-chip">
                              {page.tocTag}
                            </span>
                            <span className={`toc-item-title${active ? " active" : ""}`}>
                              {page.tocTitle}
                            </span>
                            <span className="toc-item-arrow">→</span>
                          </button>
                        </li>
                      );
                    })}
                  </ol>
                </div>
                {/* 목차 끝부분 */}

                {/* ── 편집 바 (✏️ 수정 모드) — 본문·값 모두 아래 페이지에서 직접 수정 ── */}
                {isEditing && (
                  <div className="sr-editor">
                    <div className="sr-editor-bar">
                      <div className="sr-editor-hd">
                        ✏️ <b>{PAGES[currentPage].subIssueLabel}</b> · {PAGES[currentPage].tabLabel} 수정 중
                      </div>
                      <div className="sr-editor-actions">
                        {savedAt && (
                          <span className="sr-editor-saved">
                            저장됨 {new Date(savedAt).toLocaleString("ko-KR", { hour: "2-digit", minute: "2-digit", month: "numeric", day: "numeric" })}
                          </span>
                        )}
                        <button className="sr-editor-save" onClick={handleSaveEdits}>💾 저장</button>
                      </div>
                    </div>
                    <div className="sr-editor-hint">
                      아래 페이지에서 <b>본문 문장</b>은 클릭해 바로 타이핑하고, <b>KPI·표·차트의 값</b>은 클릭하면 입력창이 떠서 수정됩니다(같은 지표는 모든 위치에 동시 반영). 이 페이지에만 적용됩니다.
                    </div>
                  </div>
                )}

                {/* ── 페이지 이동 바 (이전 · 다음) ── */}
                <div className="sr-pager">
                  <button className="sr-pager-btn" onClick={prevPage} disabled={currentPage === 0}>‹ 이전</button>
                  <span className="sr-pager-info">{currentPage + 1} / {PAGES.length}</span>
                  <button className="sr-pager-btn" onClick={nextPage} disabled={currentPage === PAGES.length - 1}>다음 ›</button>
                </div>

                {/* ── 보고서 미리보기 영역: SR 운영 템플릿 (현재 페이지) ──
                    데이터는 climateMetrics(adapter) + climateNarrative 로만 구동(더미 없음).
                    subNavItems = 페이지 탭(클릭 시 onSubNavClick → goToPage). */}
                <div
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

            {/* 우측 데이터(근거) 추적 패널 — 보고서 본문/값을 클릭하면 해당 지표 근거 표시 */}
            <div className={`draft-panel ${trackId && !isEditing ? "open" : ""}`} id="draftPanel">
              {srMetric ? (
                <div className="panel-inner">
                  <div className="panel-hd">
                    <span className="panel-hd-title">데이터 추적</span>
                    <button className="panel-close-btn" onClick={() => setTrackId(null)}>✕</button>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">선택 위치</div>
                    <span className="para-chip">{trackCtx?.area}</span>
                    <p className="para-preview-text">{trackCtx?.clicked || "—"}</p>
                    <span className="para-id-link">{trackCtx?.pageLabel}</span>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">참조 지표</div>
                    <div className="metric-accordion">
                      <div
                        className={`metric-acc-header ${metricOpen ? "open" : ""}`}
                        onClick={() => setMetricOpen((v) => !v)}
                      >
                        <div className="metric-acc-header-left">
                          <span className="metric-acc-name">{srMetric.name}</span>
                          <span className="metric-badge">{/__QL/.test(srMetric.metricId) ? "정성" : "정량"}</span>
                        </div>
                        <span className="metric-acc-chevron">›</span>
                      </div>

                      {metricOpen && (
                        <div className="metric-acc-body">
                          <div className="metric-row">
                            <span className="metric-row-key">metric_id</span>
                            <span className="metric-row-val">{srMetric.metricId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">공시 코드</span>
                            <span className="metric-row-val">{srMetric.disclosure || "—"}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">atomic_metric_id</span>
                            <span className="metric-row-val">{srMetric.atomicId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">지표명</span>
                            <span className="metric-row-val">{srMetric.name}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">데이터 유형</span>
                            <span className="metric-row-val">{srMetric.dataType}</span>
                          </div>
                          {srMetric.unit && (
                            <div className="metric-row">
                              <span className="metric-row-key">단위</span>
                              <span className="metric-row-val">{srMetric.unit}</span>
                            </div>
                          )}
                          <hr className="metric-divider" />
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

                          {srMetric.breakdown && srMetric.breakdown.length > 0 && (
                            <div className="panel-subsection">
                              <div className="trend-section-title">데이터 구성</div>
                              <table className="breakdown-table">
                                <thead>
                                  <tr>
                                    <th>구분</th>
                                    <th className="breakdown-val">값{srMetric.unit ? ` (${srMetric.unit})` : ""}</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {srMetric.breakdown.map((b, i) => (
                                    <tr key={i}>
                                      <td>{b.l}</td>
                                      <td className="breakdown-val">{b.v}</td>
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
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">AI 근거 생성</div>
                    <div className="ai-desc-box">
                      {srMetric.aiDesc
                        ? srMetric.aiDesc
                        : `‘${srMetric.name}’ 지표가 본 문장(${trackCtx?.area})의 근거로 사용되었습니다. 상세 근거 문구는 데이터 연동 시 자동 생성됩니다.`}
                    </div>
                  </div>
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

      {/* ── PDF 내보내기용: 서브이슈별로 (목차 + 페이지들)을 화면 밖에 풀사이즈로 렌더 ──
          id 에 서브이슈를 prefix 하여 export 시 서브이슈별로 묶어 캡처. 평소엔 렌더 안 함 */}
      {pdfMode && (
        <div id="pdf-render-root" className="pdf-render-root">
          {subIssues.map((si) => (
            <div key={si.id} data-subissue={si.id}>
              <div id={`pdf-toc-${si.id}`} className="pdf-toc-wrap">
                <div className="pdf-toc-sublabel">{si.subLabel}</div>
                <div className="pdf-toc-title">{si.label} · 목차</div>
                <div className="pdf-toc-rule" />
                {si.pages.map((p, i) => (
                  <div
                    key={p.key}
                    id={`pdf-tocitem-${si.id}-${p.key}`}
                    className="pdf-toc-item"
                  >
                    <span className="pdf-toc-item-num">{String(i + 1).padStart(2, "0")}</span>
                    <span className="pdf-toc-item-tag">{p.tocTag}</span>
                    <span className="pdf-toc-item-label">{p.tabLabel}</span>
                    <span className="pdf-toc-item-arrow">p.{p.props.pageNumber} →</span>
                  </div>
                ))}
              </div>
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