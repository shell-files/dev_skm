/**
 * SRChrome.jsx
 * 레이어: Component (srTemplates/core)
 * 역할: 모든 SR 서브이슈 페이지가 공유하는 공통 프레임 컴포넌트 — 상단 dark band, 상단 nav, subnav, 섹션 헤더, 푸터, MetricBar를 포함하며 본문은 children으로 주입받음
 *
 * Props:
 *   navItems — 상단 nav 탭 목록 (기본값 DEFAULT_NAV)
 *   subNavItems — 서브 nav 탭 목록 (기본값 DEFAULT_SUBNAV)
 *   pageTitle — 섹션 제목 (HTML 허용)
 *   pageTitleEn — 영문 제목 (선택)
 *   footnotes — 하단 각주 배열 (선택)
 *   sourceNote — 하단 출처 표기 (선택)
 *   children — 서브이슈별 본문 영역
 *   tag — 페이지 태그 레이블 (선택)
 *   onNavClick — nav 탭 클릭 핸들러 (선택)
 *   onSubNavClick — subnav 탭 클릭 핸들러 (선택)
 *
 * exports:
 *   SRChrome — SR 페이지 공통 레이아웃 컴포넌트
 *   MetricBar — metric 값으로 높이가 결정되는 bar 차트 요소 (stacked 지원)
 *   DEFAULT_NAV — 기본 상단 nav 항목 배열
 *   DEFAULT_SUBNAV — 기본 subnav 항목 배열
 */
// ============================================================
// SRChrome.jsx — SR 페이지 공통 프레임 (모든 sub-issue 재사용)
// 상단 dark band / nav / sub nav / section header / footer 포함
// 본문은 children으로 주입 → sub-issue별 body만 갈아끼우면 됨
// ============================================================
import React from "react";
import { num } from "./srHelpers";
import "@styles/sr-page.css";



// 상수 사용 OR DB 만들어서 도메인 메핑 후 각 들고 오기
export const DEFAULT_NAV = [
  { key: "letter", label: "Letter to Stakeholders" },
  { key: "overview", label: "Corporate Overview" },
  { key: "env", label: "Environment", active: true },
  { key: "social", label: "Social" },
  { key: "gov", label: "Governance" },
  { key: "appendix", label: "Appendix" },
];
// 상수 사용 OR DB 만들어서 도메인 메핑 후 각 들고 오기
export const DEFAULT_SUBNAV = [
  { label: "환경경영" },
  { label: "기후변화 대응", active: true },
  { label: "용수 관리" },
  { label: "자연자본 관리" },
  { label: "자원 사용 및 순환 경제" },
];



export function SRChrome({
  navItems = DEFAULT_NAV,
  subNavItems = DEFAULT_SUBNAV,
  pageTitle, 
  pageTitleEn,
  footnotes = [],
  sourceNote,
  children,
  tag,
  onNavClick,
  onSubNavClick,
}) {
  return (
    <div className="sr-page">
      {tag && <div className="sr-tag">{tag}</div>}
      <div className="sr-topband" />

      <div className="sr-nav">
        <div className="sr-nav-icons"><span>⌂</span><span>≡</span><span>↻</span></div>
        <div className="sr-nav-items">
          {navItems.map((n, i) => (
            <div
              key={n.key}
              className={"sr-nav-item" + (n.active ? " active" : "")}
              onClick={onNavClick ? () => onNavClick(n, i) : undefined}
              style={onNavClick ? { cursor: "pointer" } : undefined}
            >{n.label}</div>
          ))}
        </div>
      </div>

      <div className="sr-subnav">
        {subNavItems.map((s, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="dot">·</span>}
            <span
              className={s.active ? "sa" : ""}
              onClick={onSubNavClick ? () => onSubNavClick(s, i) : undefined}
              style={onSubNavClick ? { cursor: "pointer" } : undefined}
            >{s.label}</span>
          </React.Fragment>
        ))}
      </div>
      <div className="sr-rule" />

      <div className="sr-body">
        <div className="sr-head">
          <div>
            <div className="sr-title" dangerouslySetInnerHTML={{ __html: pageTitle }} />
            {pageTitleEn && <div className="sr-title-en">{pageTitleEn}</div>}
          </div>
        </div>
        {children}
      </div>

      <div className="sr-foot">
        <div className="sr-fn">
          {footnotes.map((f, i) => (
            <div key={i} dangerouslySetInnerHTML={{ __html: f }} />
          ))}
        </div>
        {sourceNote && <div className="sr-auto" dangerouslySetInnerHTML={{ __html: sourceNote }} />}
      </div>
    </div>
  );
}

/** metric 값으로 스케일되는 막대(없으면 미렌더). breakdown metric 있으면 stacked */
export function MetricBar({ metrics, totalId, s1Id, s2Id, maxVal, maxH }) {
  const total = num(metrics, totalId);
  if (total == null) return <div className="sr-bar solid" style={{ height: 0 }} />;
  const h = Math.round((total / maxVal) * maxH);
  const s1 = s1Id ? num(metrics, s1Id) : null;
  const s2 = s2Id ? num(metrics, s2Id) : null;
  if (s1 != null && s2 != null) {
    return (
      <div className="sr-bar" style={{ height: h }} data-source={totalId}>
        <div className="seg s2" style={{ height: Math.round(h * (s2 / total)) }} data-source={s2Id} />
        <div className="seg s1" style={{ height: Math.round(h * (s1 / total)) }} data-source={s1Id} />
      </div>
    );
  }
  return <div className="sr-bar solid" style={{ height: h }} data-source={totalId} />;
}
