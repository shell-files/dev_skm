// ============================================================
// ClimateTargetPageB.jsx — B안 (표 중심 버전)
// 모든 셀이 metric_id에 바인딩. breakdown metric이 없으면 해당 행 자동 생략(더미 금지)
// ============================================================
import React from "react";
import { SRChrome } from "../../../core/SRChrome";
import { Narrative, mt, dv, num, fmtInt, reductionFromBase, NARRATIVE_TEMPLATE_CLIMATE } from "../../../core/srHelpers";

/** 일반 셀: render → displayValue, placeholder → {id} */
function Cell({ metrics, id, mode, cls }) {
  return <td className={cls} data-source={id}>{mt(metrics, id, mode)}</td>;
}

/** 숫자 전용 셀: 단위 컬럼이 따로 있는 표에서 값만 표기(줄바꿈 방지) */
function NumCell({ metrics, id, mode, cls }) {
  const txt =
    mode === "placeholder"
      ? `{${id}}`
      : num(metrics, id) != null
      ? fmtInt(num(metrics, id))
      : (dv(metrics, id) ?? "—");
  return <td className={cls} data-source={id}>{txt}</td>;
}

export function ClimateTargetPageB(props) {
  const {
    metrics, narrativeText, mode = "render", highlight = true,
    template = NARRATIVE_TEMPLATE_CLIMATE,
  } = props;

  const cutBase = reductionFromBase(metrics, "E1-05__G0003", "E1-06__G0003");
  const renewPct = num(metrics, "E1-07__G0003") ?? 0;

  // Scope 1/2 분해 행 — 해당 breakdown metric이 있을 때만 렌더
  const splitRows = [
    { label: "　Scope 1 (직접배출)", base: "E1-05__G0001", rep: "E1-06__G0001" },
    { label: "　Scope 2 (간접배출)", base: "E1-05__G0002", rep: "E1-06__G0002" },
  ];

  return (
    <SRChrome {...props}>
      <Narrative narrativeText={narrativeText} template={template} metrics={metrics} mode={mode} highlight={highlight} onNarrativeChange={props.onNarrativeChange} />

      <div className="sr-cols">
        <div className="c-main">
          <div className="sr-tcap"><span className="num">1</span> 온실가스 배출 및 에너지 전환 실적</div>
          <table className="sr-tbl nums">
            <thead>
              <tr><th>구분</th><th>단위</th><th>기준연도</th><th>보고연도</th><th>전년 대비</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>연결 Scope 1·2 배출량</td>
                <td className="unit">{metrics["E1-06__G0003"]?.unit || "tCO2eq"}</td>
                <NumCell metrics={metrics} id="E1-05__G0003" mode={mode} />
                <NumCell metrics={metrics} id="E1-06__G0003" mode={mode} cls="strong" />
                <td className="delta" data-source="E1-06__G0004,E1-06__G0005">
                  {mode === "placeholder"
                    ? "{E1-06__G0004} ({E1-06__G0005})"
                    : `${fmtInt(num(metrics, "E1-06__G0004"))} (${mt(metrics, "E1-06__G0005", mode)})`}
                </td>
              </tr>
              {splitRows.map((r, i) => {
                const b = num(metrics, r.base), rep = num(metrics, r.rep);
                if (b == null || rep == null) return null; // 더미 금지: 미바인딩 시 행 숨김
                return (
                  <tr key={i}>
                    <td>{r.label}</td>
                    <td className="unit">tCO2eq</td>
                    <NumCell metrics={metrics} id={r.base} mode={mode} />
                    <NumCell metrics={metrics} id={r.rep} mode={mode} />
                    <td className="delta" data-source={r.base + "," + r.rep}>{mode === "placeholder" ? "계산" : fmtInt(b - rep)}</td>
                  </tr>
                );
              })}
              <tr>
                <td>재생에너지 전환율</td>
                <td className="unit">{metrics["E1-07__G0003"]?.unit || "%"}</td>
                <td>–</td>
                <Cell metrics={metrics} id="E1-07__G0003" mode={mode} cls="strong" />
                <td className="up">상승</td>
              </tr>
              <tr>
                <td>기준연도 대비 누적 감축률</td>
                <td className="unit">%</td>
                <td>0.00</td>
                <td className="strong" data-source="E1-05__G0003,E1-06__G0003">
                  {mode === "placeholder" ? "계산" : cutBase != null ? cutBase.toFixed(2) : "—"}
                </td>
                <td className="up">개선</td>
              </tr>
            </tbody>
          </table>

          {/* 재생에너지 전환 진척도 게이지 — width는 E1-07__G0003 값으로 */}
          <div className="sr-gauge">
            <div className="gl">재생에너지 전환 진척도 · {mt(metrics, "E1-08__G0002", mode)} 100% 목표</div>
            <div className="gv" data-source="E1-07__G0003">{mt(metrics, "E1-07__G0003", mode)}<small> / 100%</small></div>
            <div className="sr-track"><div className="sr-fill" style={{ width: Math.min(renewPct, 100) + "%" }} /></div>
            <div className="sr-gx"><span>현재 {mt(metrics, "E1-07__G0003", mode)}</span><span>{mt(metrics, "E1-08__G0002", mode)} · 100%</span></div>
          </div>
        </div>

        <div className="c-side">
          <div className="sr-tcap"><span className="num">2</span> 중장기 기후목표</div>
          <table className="sr-tbl">
            <thead><tr><th>목표 항목</th><th>목표연도</th><th>수준</th></tr></thead>
            <tbody>
              <tr>
                <td>재생에너지 전환</td>
                <td className="sr-yr" data-source="E1-08__G0002">{mt(metrics, "E1-08__G0002", mode)}</td>
                <td data-source="E1-08__QL0002">{mt(metrics, "E1-08__QL0002", mode)}</td>
              </tr>
              <tr>
                <td>탄소중립 (Net-Zero)</td>
                <td className="sr-yr" data-source="E1-08__G0001">{mt(metrics, "E1-08__G0001", mode)}</td>
                <td data-source="E1-08__QL0001">{mt(metrics, "E1-08__QL0001", mode)}</td>
              </tr>
              <tr>
                <td>기준연도</td>
                <td className="sr-yr" style={{ color: "var(--ink)" }} data-source="E1-05__QL0002">{mt(metrics, "E1-05__QL0002", mode)}</td>
                <td data-source="E1-05__G0003">{mt(metrics, "E1-05__G0003", mode)}</td>
              </tr>
            </tbody>
          </table>

          {/* 목표 관리 체계 — E1-05__QL0005 (KPI 연계) */}
          <div className="sr-note-card">
            <div className="l">목표 관리 체계</div>
            <div className="b">감축 실적 · 전환율을<br />경영진 KPI에 연계</div>
            <div className="s" data-source="E1-05__QL0005">연 단위 이행 점검 / 자회사별 감축 과제 관리</div>
          </div>
        </div>
      </div>
    </SRChrome>
  );
} 