// ============================================================
// SRChrome.jsx — SR 페이지 공통 프레임 (모든 sub-issue 재사용)
// 상단 dark band / nav / sub nav / section header / footer 포함
// 본문은 children으로 주입 → sub-issue별 body만 갈아끼우면 됨
// ============================================================
import React from "react";
import { num } from "./srHelpers";
import "./sr-page.css";

export const DEFAULT_NAV = [
  { key: "letter", label: "Letter to Stakeholders" },
  { key: "overview", label: "Corporate Overview" },
  { key: "env", label: "Environment", active: true },
  { key: "social", label: "Social" },
  { key: "gov", label: "Governance" },
  { key: "appendix", label: "Appendix" },
];

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
  pageNumber = 42,
  sectionLabel = "전략 · CLIMATE TARGET",
  ghost = "STRATEGY",
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
        <div className="sr-pg">{pageNumber}</div>
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
        <div className="sr-ghost">{ghost}</div>
        <div className="sr-head">
          <div>
            <div className="sr-eyebrow">{sectionLabel}</div>
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
