// srTemplates/subIssues/talentDev.jsx
// 교육훈련·역량개발 서브이슈
import React from "react";
import { SRChrome } from "../core/SRChrome";
import { Narrative, mt, num, buildMetricsMap } from "../core/srHelpers";

const TEMPLATE =
  "{S3-01__QL0001} {S3-01__QL0002} 주요 프로그램은 {S3-01__QL0003}, {S3-01__QL0004}로 구성된다. " +
  "연결 임직원 수는 {S1-02__G0001}이며, 1인당 교육시간은 {S3-02__G0002}, " +
  "핵심직무 교육 달성률은 {S3-02__G0003}이다.";

const metricFields = [
  { id: "S3-01__QL0001", label: "교육훈련 전략·방향" },
  { id: "S3-01__QL0002", label: "역량개발 체계 개요" },
  { id: "S3-01__QL0003", label: "주요 교육 프로그램 1" },
  { id: "S3-01__QL0004", label: "주요 교육 프로그램 2" },
  { id: "S1-02__G0001", label: "연결 임직원 수" },
  { id: "S3-02__G0002", label: "1인당 교육시간" },
  { id: "S3-02__G0003", label: "핵심직무 교육 달성률" },
];

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

      {/* KPI strip */}
      <div className="sr-kpis">
        <div className="sr-kpi">
          <div className="kl">연결 임직원 수</div>
          <div className="kv" data-source="S1-02__G0001">{mt(metrics, "S1-02__G0001", mode)}</div>
          <div className="kd flat">연결 기준</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">1인당 교육시간</div>
          <div className="kv" data-source="S3-02__G0002">{mt(metrics, "S3-02__G0002", mode)}</div>
          <div className="kd up">보고연도</div>
        </div>
        <div className="sr-kpi">
          <div className="kl">핵심직무 교육 달성률</div>
          <div className="kv" data-source="S3-02__G0003">{mt(metrics, "S3-02__G0003", mode)}</div>
          <div className="kd up">목표 대비</div>
        </div>
      </div>

      {/* 교육 지표 상세 */}
      <div className="sr-cols" style={{ marginTop: 16 }}>
        <div className="c-main">
          <div className="sr-tcap">
            <span className="num">1</span>교육훈련 핵심 성과 지표
          </div>
          <table className="sr-tbl">
            <thead>
              <tr>
                <th style={{ width: "52%" }}>지표</th>
                <th>보고연도</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>연결 임직원 수</td>
                <td className="strong" data-source="S1-02__G0001">
                  {mt(metrics, "S1-02__G0001", mode)}
                </td>
                <td><span className="unit">명</span></td>
              </tr>
              <tr>
                <td>1인당 교육시간</td>
                <td data-source="S3-02__G0002">
                  {mt(metrics, "S3-02__G0002", mode)}
                </td>
                <td><span className="unit">시간/명</span></td>
              </tr>
              <tr>
                <td>핵심직무 교육 달성률</td>
                <td className="up" data-source="S3-02__G0003">
                  {mt(metrics, "S3-02__G0003", mode)}
                </td>
                <td><span className="unit">목표 대비</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="c-side">
          {/* 달성률 게이지 */}
          <div className="sr-gauge">
            <div className="gl">핵심직무 교육 달성률</div>
            <div className="gv" data-source="S3-02__G0003">
              {mt(metrics, "S3-02__G0003", mode)}
            </div>
            <div className="sr-track">
              <div className="sr-fill" style={{ width: `${fillPct}%` }} />
            </div>
            <div className="sr-gx"><span>0%</span><span>100%</span></div>
          </div>

          {/* 주요 프로그램 */}
          <div className="sr-note-card" data-source="S3-01__QL0003">
            <div className="l">주요 교육 프로그램</div>
            <div className="b" style={{ fontSize: 11 }}>
              {mt(metrics, "S3-01__QL0003", mode)}
            </div>
            <div className="s" data-source="S3-01__QL0004">
              {mt(metrics, "S3-01__QL0004", mode)}
            </div>
          </div>
        </div>
      </div>

      <div className="sr-measures" data-source="S3-01__QL0001">
        <span className="ml">교육훈련 전략</span>
        <span className="mv">{mt(metrics, "S3-01__QL0001", mode)}</span>
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
        pageTitleEn: "Training & Development",
        sourceNote: "SKM SR Template v1.0 · Auto-generated",
      },
    },
  ],
};

export default talentDev;
