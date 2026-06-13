// srTemplates/subIssues/talentDev.jsx
// 교육훈련·역량개발 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

// AI 생성 문단이 없을 때 폴백 — 숫자 지표만 참조
const TEMPLATE =
  "연결 임직원 수는 총 {S1-02__G0001}이며, 이들을 대상으로 한 1인당 평균 교육시간은 {S3-02__G0002}이었습니다. " +
  "또한 핵심 직무 교육 달성률은 {S3-02__G0003}를 기록하였습니다.";

const metricFields = [
  { id: "S1-02__G0001",  label: "연결 임직원 수" },
  { id: "S3-02__G0002",  label: "1인당 교육시간" },
  { id: "S3-02__G0003",  label: "핵심직무 교육 달성률" },
  { id: "S3-01__QL0001", label: "인재 전략 방향" },
  { id: "S3-01__QL0002", label: "교육 운영 방식" },
  { id: "S3-01__QL0003", label: "주요 교육 프로그램 1" },
  { id: "S3-01__QL0004", label: "주요 교육 프로그램 2" },
];

// 도넛 게이지 (SVG)
function DonutGauge({ pct = 0, size = 66 }) {
  const R = 23, cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * R;
  const filled = (Math.min(Math.max(pct, 0), 100) / 100) * circ;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} style={{ flexShrink: 0 }}>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(255,255,255,.25)" strokeWidth={8} />
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="#fff" strokeWidth={8}
        strokeDasharray={`${filled} ${circ - filled}`}
        transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="round" />
      <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fontWeight="900" fill="#fff">
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

// 섹션 구분 헤더
function SectionHeader({ title, tag }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-end", justifyContent: "space-between",
      borderBottom: "1.5px solid var(--line)",
      paddingBottom: 6, marginTop: 16, marginBottom: 11,
    }}>
      <span style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <span style={{
          display: "inline-block", width: 4, height: 13,
          background: "var(--brand)", borderRadius: 2, flexShrink: 0,
        }} />
        <span style={{ fontSize: 11.5, fontWeight: 800, color: "var(--ink)" }}>{title}</span>
      </span>
      <span style={{ fontSize: 8.5, fontWeight: 700, color: "var(--muted)", letterSpacing: ".07em" }}>{tag}</span>
    </div>
  );
}

function TalentDevPage(props) {
  const { metrics, narrativeText, mode = "render", aiMetricIds = [] } = props;
  const achieveRate = num(metrics, "S3-02__G0003");
  const fillPct = achieveRate != null ? Math.min(Math.max(achieveRate, 0), 100) : 0;

  return (
    <SRChrome {...props}>
      {/* AI 생성 문단 — report_text 우선, 없으면 template 폴백 */}
      <Narrative
        narrativeText={narrativeText}
        template={TEMPLATE}
        metrics={metrics}
        mode={mode}
        metricIds={aiMetricIds}
        onNarrativeChange={props.onNarrativeChange}
      />

      {/* ── 핵심 성과 지표 ── */}
      <SectionHeader title="핵심 성과 지표" tag="KEY METRICS" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>

        {/* 연결 임직원 수 */}
        <div style={{ border: "1px solid var(--line)", borderRadius: 6, padding: "14px 16px" }}>
          <div style={{ fontSize: 10, color: "var(--muted)", fontWeight: 500 }}>연결 임직원 수</div>
          <div style={{ fontSize: 21, fontWeight: 900, color: "var(--ink)", margin: "5px 0 4px" }}
            data-source="S1-02__G0001">
            {mt(metrics, "S1-02__G0001", mode)}
          </div>
          <div style={{ fontSize: 9, color: "var(--muted)", fontWeight: 500 }}>연결 기준 · 보고연도</div>
        </div>

        {/* 1인당 평균 교육시간 */}
        <div style={{ border: "1px solid var(--line)", borderRadius: 6, padding: "14px 16px" }}>
          <div style={{ fontSize: 10, color: "var(--muted)", fontWeight: 500 }}>1인당 평균 교육시간</div>
          <div style={{ fontSize: 21, fontWeight: 900, color: "var(--ink)", margin: "5px 0 4px" }}
            data-source="S3-02__G0002">
            {mt(metrics, "S3-02__G0002", mode)}
          </div>
          <div style={{ fontSize: 9, color: "var(--muted)", fontWeight: 500 }}>전 임직원 평균</div>
        </div>

        {/* 핵심직무 교육 달성률 + 도넛 게이지 */}
        <div style={{
          background: "var(--brand)", borderRadius: 6, padding: "14px 16px",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
        }}>
          <div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,.75)", fontWeight: 500 }}>핵심직무 교육 달성률</div>
            <div style={{ fontSize: 21, fontWeight: 900, color: "#fff", margin: "5px 0 4px" }}
              data-source="S3-02__G0003">
              {mt(metrics, "S3-02__G0003", mode)}
            </div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,.75)", fontWeight: 500 }}>목표 대비 달성 수준</div>
          </div>
          <DonutGauge pct={fillPct} />
        </div>
      </div>

      {/* ── 주요 교육 프로그램 ── */}
      <SectionHeader title="주요 교육 프로그램" tag="PROGRAMS" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 11 }}>
        {[
          { id: "S3-01__QL0003", badge: "1" },
          { id: "S3-01__QL0004", badge: "2" },
        ].map(({ id, badge }) => (
          <div key={id} style={{ border: "1px solid var(--line)", borderRadius: 6, padding: "12px 14px" }}>
            <div style={{ marginBottom: 7 }}>
              <span style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                width: 20, height: 20, borderRadius: "50%",
                background: "var(--brand)", color: "#fff",
                fontSize: 10, fontWeight: 900,
              }}>{badge}</span>
            </div>
            <div style={{ fontSize: 10.5, color: "var(--ink-soft)", lineHeight: 1.65 }}
              data-source={id}>
              {mt(metrics, id, mode)}
            </div>
          </div>
        ))}
      </div>

      {/* ── 교육 운영 방식 / 인재 전략 방향 ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 11, marginTop: 11 }}>
        <div style={{
          background: "var(--tint)", border: "1px solid var(--line)",
          borderRadius: 6, padding: "12px 14px",
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 800, color: "var(--brand)", marginBottom: 5 }}>교육 운영 방식</div>
          <div style={{ fontSize: 10.5, color: "var(--ink-soft)", lineHeight: 1.6 }}
            data-source="S3-01__QL0002">
            {mt(metrics, "S3-01__QL0002", mode)}
          </div>
        </div>
        <div style={{
          background: "var(--tint)", border: "1px solid var(--line)",
          borderRadius: 6, padding: "12px 14px",
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 800, color: "var(--brand)", marginBottom: 5 }}>인재 전략 방향</div>
          <div style={{ fontSize: 10.5, color: "var(--ink-soft)", lineHeight: 1.6 }}
            data-source="S3-01__QL0001">
            {mt(metrics, "S3-01__QL0001", mode)}
          </div>
        </div>
      </div>
    </SRChrome>
  );
}

const talentDev = {
  id: "S_TALENT__TRAINING_DEVELOPMENT",
  label: "교육훈련·역량개발",
  subLabel: "인적자본 관리",
  exportName: "talent-dev",
  adapter: buildMetricsMap,
  metricFields,
  pages: [
    {
      key: "talent-dev-a",
      tabLabel: "교육훈련",
      tocTag: "S3",
      Component: TalentDevPage,
      props: {
        pageTitle: "교육훈련·역량개발",
        pageTitleEn: "Talent Development & Training",
        sourceNote: "NARRATIVE TEMPLATE V1.0 · AUTO-GENERATED · S3-01 / S3-02 / S1-02 ATOMIC LINKED",
        footnotes: [
          "1) 연결 기준(자회사 포함) 임직원 수 / 보고연도 기준",
          "2) 1인당 교육시간 = 총 교육시간 ÷ 연결 임직원 수 &nbsp;|&nbsp; 3) 핵심직무 교육 달성률 = 핵심직무 교육 이수자 ÷ 대상자",
        ],
        subNavItems: [
          { label: "기후변화 대응" },
          { label: "공급망 감사" },
          { label: "교육훈련", active: true },
          { label: "친환경 제품" },
          { label: "제품안전" },
        ],
      },
    },
  ],
};

export default talentDev;
