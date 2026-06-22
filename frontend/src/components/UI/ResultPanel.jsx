/**
 * ResultPanel.jsx
 * 레이어: Component (UI)
 * 역할: 분석 결과 대시보드의 패널 레이아웃 — 색상 점·제목·카운트 배지 헤더와 body 슬롯을 제공한다.
 *
 * Props:
 *   title    {string}    — 패널 제목
 *   accent   {string}    — 색상 테마 ("green" | "blue" | "orange" | "purple")
 *   count    {number}    — 헤더 우측 카운트 배지 (생략 시 미표시)
 *   children {ReactNode} — panel-body 내용
 */
const ResultPanel = ({ title, accent, count, children }) => (
  <div className={`result-panel panel-accent-${accent}`}>
    <div className="panel-header-row">
      <span className="panel-title">
        <span className={`panel-dot dot-${accent}`} />
        {title}
      </span>
      {count != null && <span className="panel-badge-count">{count}건</span>}
    </div>
    <div className="panel-body">{children}</div>
  </div>
);

export default ResultPanel;
