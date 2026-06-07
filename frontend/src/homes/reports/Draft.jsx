import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import "@styles/draft.css";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from "docx";
import * as XLSX from "xlsx";

// ── SR 템플릿 통합 (서브이슈 레지스트리 소비) ──
// 새 서브이슈는 srTemplates/subIssues/<name>/ 폴더 + registry.js 한 줄로 추가됨.
// (데모용 index.jsx / demo.html / metricsExample.js 는 import 하지 않음)
import { subIssues } from "./srTemplates/registry";
import "./srTemplates/core/sr-page.css";




// (paragraphData, paragraphTexts, TrendChart 등 상단 데이터 정의는 기존과 동일합니다)
const paragraphData = {
  p1: {
    tag: "전략 및 방향", tagType: "blue", id: "P-03-01",
    tooltipTitle: "● 사업 개요 지표",
    tooltipRows: [
      { key: "metric_id", val: "G0-02__G0001" },
      { key: "연결 매출액", val: "17.8조 KRW" },
      { key: "G0-03__G0001", val: "22개 사업장" },
      { key: "보고기간", val: "2024.01.01~12.31" },
    ],
    preview: "SKM은 과학기반 감축목표 이니셔티브(SBTi)의 1.5°C 시나리오에 부합하는 넷제로 목표를 수립하고",
    metricCount: 1,
    metrics: [{
      name: "연결 Scope 1-2 총배출량", badge: "그룹 통합 지표", badgeType: "green",
      metricId: "E1-06", atomicId: "E1-06-G0003", unit: "tCO₂eq", dataType: "정량(Rollup)",
      desc: "지주사와 자회사 설비 데이터를 합산하여 산출한 연결 기준 총배출량",
      latest: "112,500 tCO₂eq",
      trend: [{ y: 2022, v: 130890 }, { y: 2023, v: 117400 }, { y: 2024, v: 112500 }],
      breakdown: [{ l: "A_GROUP", v: "66,000" }, { l: "B_SUB_KR", v: "26,000" }, { l: "C_SUB_EU", v: "18,000" }, { l: "D_SUB_US", v: "2,500" }],
      formula: "Scope 1 + Scope 2\nE1-05__G0001 + E1-05__G0002",
    }],
    aiDesc: "넷제로 전환 방향을 나타내는 핵심 전략 지표로, 과학기반 감축목표 이행 현황을 정량적으로 보여줍니다.",
    related: { id: "P-03-02", label: "핵심 데이터" },
  },
  p2: {
    tag: "주요 성과", tagType: "green", id: "S-03-02",
    tooltipTitle: "● E1-06 Scope 1·2 배출량",
    tooltipRows: [
      { key: "metric_id", val: "E1-06__G0003" },
      { key: "2024 배출량", val: "112,500 tCO₂eq" },
      { key: "감축량", val: "4,402 tCO₂eq" },
      { key: "감축률", val: "3.91%" },
      { key: "재생E 전환율", val: "9.49%" },
    ],
    preview: "2024년 온실가스 배출량(스코프 1·2)은 96.7만 tCO₂e로, 2022년 대비 11.0% 감소하였습니다.",
    metricCount: 1,
    metrics: [{
      name: "온실가스 배출량 (스코프 1·2)", badge: "핵심 지표", badgeType: "blue",
      metricId: "M-ENV-045", atomicId: "AM-ENV-045-01", unit: "만 tCO₂e", dataType: "정량",
      desc: "스코프 1과 스코프 2 배출량을 합산한 온실가스 총배출량",
      latest: "96.7만 tCO₂e",
      trend: [{ y: 2022, v: 101.4 }, { y: 2023, v: 94.2 }, { y: 2024, v: 96.7 }],
      breakdown: [{ l: "스코프 1", v: "33.6" }, { l: "스코프 2", v: "53.1" }],
      formula: "스코프 1 + 스코프 2",
    }],
    aiDesc: "온실가스 배출량 추이를 나타내는 핵심 지표로, 감축 목표 대비 이행 현황을 정량적으로 보여줍니다.",
    related: { id: "P-03-01", label: "전략 및 방향" },
  },
  p3: {
    tag: "전략 및 접근", tagType: "orange", id: "S-03-03",
    tooltipTitle: "● S6-04 공급망 감사",
    tooltipRows: [
      { key: "감사 이행률", val: "71.90%" },
      { key: "고위험 업체 수", val: "64개사" },
      { key: "CAP 완료율", val: "68.09%" },
    ],
    preview: "SKM은 2030년까지 2022년 대비 온실가스 배출량(스코프 1·2) 42% 감축을 목표로 하며...",
    metricCount: 1,
    metrics: [{
      name: "온실가스 감축 목표", badge: "목표 지표", badgeType: "green",
      metricId: "E1-05", atomicId: "E1-05-G0001", unit: "%", dataType: "정량(목표)",
      desc: "2030년까지 2022년 대비 온실가스 배출량 42% 감축 목표치",
      latest: "42% (2030년 목표)",
      trend: [{ y: 2022, v: 0 }, { y: 2023, v: 11 }, { y: 2024, v: 11 }],
      breakdown: [{ l: "에너지 전환", v: "20%p" }, { l: "공정 효율화", v: "12%p" }, { l: "공급망 관리", v: "10%p" }],
      formula: "(기준연도 - 목표연도) / 기준연도 × 100",
    }],
    aiDesc: "온실가스 감축 목표 및 3대 전략 축에 관한 내용으로, 2030 로드맵의 핵심 실행 방향을 제시합니다.",
    related: { id: "S-03-02", label: "주요 성과" },
  },
  p4: {
    tag: "인재 개발", tagType: "blue", id: "S3-02",
    tooltipTitle: "● S3-02 교육 지표",
    tooltipRows: [
      { key: "임직원 수", val: "8,367명" },
      { key: "1인당 교육시간", val: "33.42시간" },
      { key: "핵심직무 달성률", val: "72.01%" },
    ],
    preview: "연결 임직원 8,367명, 1인당 교육시간 33.42시간, 핵심직무 달성률 72.01%...",
    metricCount: 2,
    metrics: [{
      name: "교육 훈련 현황", badge: "인적자본 지표", badgeType: "blue",
      metricId: "S3-02__G0002", atomicId: "S3-02__G0003", unit: "시간/명", dataType: "정량",
      desc: "연결 임직원 교육시간 및 핵심직무 교육 달성률",
      latest: "33.42시간/명",
      trend: [{ y: 2022, v: 28.1 }, { y: 2023, v: 31.5 }, { y: 2024, v: 33.42 }],
      breakdown: [{ l: "임직원 수", v: "8,367명" }, { l: "1인당 교육시간", v: "33.42h" }, { l: "핵심직무 달성률", v: "72.01%" }],
      formula: "총 교육시간 / 전체 임직원 수 (S1-02__G0001)",
    }],
    aiDesc: "미래 모빌리티 전환을 위한 인적 역량 개발 수준을 나타내는 핵심 지표입니다.",
    related: { id: "S3-01", label: "인재 개발 전략" },
  },
  p5: {
    tag: "친환경 제품", tagType: "green", id: "AP-E-06",
    tooltipTitle: "● AP-E-06 친환경제품",
    tooltipRows: [
      { key: "친환경 매출", val: "4.3조 KRW" },
      { key: "매출 비중", val: "24.15%" },
      { key: "회피 배출량", val: "1,245,000 tCO₂eq" },
      { key: "비용 절감", val: "689.7억 KRW" },
    ],
    preview: "친환경 제품 매출 4.3조 KRW (매출 대비 24.15%), 회피배출 1,245,000 tCO₂eq...",
    metricCount: 1,
    metrics: [{
      name: "친환경 제품 매출", badge: "제품 지속가능성", badgeType: "green",
      metricId: "AP-E-06__G0001", atomicId: "AP-E-06__G0003", unit: "KRW", dataType: "정량",
      desc: "연결 기준 친환경 제품 매출액 및 회피 온실가스 배출량",
      latest: "4,298,000,000,000 KRW",
      trend: [{ y: 2022, v: 3100 }, { y: 2023, v: 3750 }, { y: 2024, v: 4298 }],
      breakdown: [{ l: "친환경 매출", v: "4.3조 KRW" }, { l: "매출 비중", v: "24.15%" }, { l: "회피 배출량", v: "1,245,000 tCO₂eq" }, { l: "비용 절감", v: "689.7억 KRW" }],
      formula: "AP-E-06__G0001 / 연결 총매출 × 100 = AP-E-06__G0003",
    }],
    aiDesc: "친환경 제품 포트폴리오의 재무적·환경적 성과를 동시에 보여주는 핵심 지표입니다.",
    related: { id: "AP-E-06", label: "제품 환경성과" },
  },
  p6: {
    tag: "제품 안전", tagType: "orange", id: "AP-S-01",
    tooltipTitle: "● AP-S-01 제품안전",
    tooltipRows: [
      { key: "리콜 건수", val: "3건" },
      { key: "CAP 완료율", val: "70.37%" },
    ],
    preview: "리콜 건수 3건, 제품안전 CAP 완료율 70.37%...",
    metricCount: 1,
    metrics: [{
      name: "제품안전 관리 현황", badge: "품질 지표", badgeType: "blue",
      metricId: "AP-S-01__G0001", atomicId: "AP-S-01__G0005", unit: "건", dataType: "정량",
      desc: "연결 기준 리콜 및 제품안전 시정조치(CAP) 완료 현황",
      latest: "CAP 완료율 70.37%",
      trend: [{ y: 2022, v: 65 }, { y: 2023, v: 68 }, { y: 2024, v: 70.37 }],
      breakdown: [{ l: "리콜 건수", v: "3건" }, { l: "CAP 완료율", v: "70.37%" }, { l: "전체 대상", v: "10건" }],
      formula: "CAP 완료 건수 / AP-S-01__G0002 × 100",
    }],
    aiDesc: "제품 품질과 안전 관리 수준을 정량적으로 보여주는 핵심 리스크 지표입니다.",
    related: { id: "AP-S-01", label: "제품안전 정책" },
  },
  p7: {
    tag: "기후 리스크", tagType: "blue", id: "TCFD-01",
    tooltipTitle: "● TCFD 기후 리스크",
    tooltipRows: [
      { key: "전환 리스크", val: "탄소세·규제 강화" },
      { key: "물리적 리스크", val: "홍수·가뭄" },
      { key: "시나리오", val: "1.5°C / 2°C / 4°C" },
    ],
    preview: "TCFD 프레임워크 기반 기후 리스크 및 기회 요인 식별·평가·관리...",
    metricCount: 1,
    metrics: [{
      name: "기후 전환 비용 추산", badge: "리스크 지표", badgeType: "blue",
      metricId: "TCFD-01__G0001", atomicId: "TCFD-01__G0002", unit: "억 KRW", dataType: "정량(추산)",
      desc: "2°C 시나리오 기준 2030년 탄소 비용 및 규제 대응 추가 비용",
      latest: "연간 약 850억 KRW",
      trend: [{ y: 2022, v: 520 }, { y: 2023, v: 680 }, { y: 2024, v: 850 }],
      breakdown: [{ l: "탄소세 비용", v: "420억" }, { l: "규제 대응 비용", v: "280억" }, { l: "전환 투자", v: "150억" }],
      formula: "시나리오별 탄소 가격 × 배출량 + 규제 준수 비용",
    }],
    aiDesc: "기후변화 시나리오 분석을 통해 도출한 재무적 영향 추산치로, 리스크 관리 투자 우선순위를 제시합니다.",
    related: { id: "P-03-01", label: "전략 및 방향" },
  },
  p8: {
    tag: "이해관계자", tagType: "green", id: "S-IH-01",
    tooltipTitle: "● 이해관계자 소통",
    tooltipRows: [
      { key: "ESG 인식 긍정률", val: "81.2%" },
      { key: "사회공헌 투자", val: "320억 KRW" },
      { key: "IR 미팅", val: "연 4회" },
    ],
    preview: "이중 중요성 평가 기반 이해관계자 소통 및 사회공헌 활동...",
    metricCount: 1,
    metrics: [{
      name: "사회공헌 투자액", badge: "사회 지표", badgeType: "green",
      metricId: "S-IH-01__G0001", atomicId: "S-IH-01__G0003", unit: "억 KRW", dataType: "정량",
      desc: "연결 기준 사회공헌 투자액 및 매출 대비 비율",
      latest: "320억 KRW (매출 0.18%)",
      trend: [{ y: 2022, v: 260 }, { y: 2023, v: 290 }, { y: 2024, v: 320 }],
      breakdown: [{ l: "청소년 교육", v: "120억" }, { l: "이동 지원", v: "90억" }, { l: "환경 복원", v: "110억" }],
      formula: "사회공헌 투자액 / 연결 매출 × 100",
    }],
    aiDesc: "이해관계자 신뢰 구축을 위한 사회적 책임 이행 수준을 정량적으로 보여주는 지표입니다.",
    related: { id: "S3-01", label: "인재 개발 전략" },
  },
  p9: {
    tag: "환경경영", tagType: "blue", id: "E-WM-01",
    tooltipTitle: "● 환경경영 현황",
    tooltipRows: [
      { key: "ISO 14001 인증", val: "21/22개 사업장" },
      { key: "용수 취수량", val: "2,340,000 m³" },
      { key: "재이용수 비율", val: "21.7%" },
      { key: "VOCs 감소율", val: "9.4%" },
    ],
    preview: "ISO 14001 기반 환경경영시스템 운영, 용수·대기오염물질 관리...",
    metricCount: 1,
    metrics: [{
      name: "용수 재이용률", badge: "환경 지표", badgeType: "green",
      metricId: "E-WM-01__G0001", atomicId: "E-WM-01__G0002", unit: "%", dataType: "정량",
      desc: "연결 기준 용수 재이용수 비율",
      latest: "21.7%",
      trend: [{ y: 2022, v: 15.4 }, { y: 2023, v: 18.6 }, { y: 2024, v: 21.7 }],
      breakdown: [{ l: "냉각수 재이용", v: "12.3%" }, { l: "공정수 재이용", v: "6.8%" }, { l: "빗물 활용", v: "2.6%" }],
      formula: "재이용수 사용량 / 총 용수 취수량 × 100",
    }],
    aiDesc: "물 부족 리스크 대응 수준을 보여주는 핵심 환경 지표로, 절수 목표 달성도를 정량화합니다.",
    related: { id: "P-03-02", label: "핵심 데이터" },
  },
  p10: {
    tag: "안전보건", tagType: "orange", id: "S-SH-01",
    tooltipTitle: "● 안전보건 현황",
    tooltipRows: [
      { key: "LTIR", val: "0.38" },
      { key: "사망사고", val: "0건" },
      { key: "협력사 LTIR", val: "0.61" },
      { key: "CAP 완료율", val: "89.4%" },
    ],
    preview: "ISO 45001 기반 안전보건 경영, LTIR 0.38 달성...",
    metricCount: 1,
    metrics: [{
      name: "재해율 (LTIR)", badge: "안전 지표", badgeType: "blue",
      metricId: "S-SH-01__G0001", atomicId: "S-SH-01__G0002", unit: "건/100만 시간", dataType: "정량",
      desc: "연결 기준 임직원 재해율(Lost Time Injury Rate)",
      latest: "0.38",
      trend: [{ y: 2022, v: 0.61 }, { y: 2023, v: 0.45 }, { y: 2024, v: 0.38 }],
      breakdown: [{ l: "임직원 LTIR", v: "0.38" }, { l: "협력사 LTIR", v: "0.61" }, { l: "사망사고", v: "0건" }],
      formula: "재해 건수 / 총 근로시간 × 1,000,000",
    }],
    aiDesc: "안전보건 경영 성과를 정량화하는 핵심 지표로, 중대재해 예방 수준을 보여줍니다.",
    related: { id: "AP-S-01", label: "제품안전 정책" },
  },
  p11: {
    tag: "정보보안", tagType: "blue", id: "G-IS-01",
    tooltipTitle: "● 정보보안 현황",
    tooltipRows: [
      { key: "보안 투자 증가율", val: "21.3%" },
      { key: "침해 신고 사례", val: "0건" },
      { key: "교육 이수율", val: "97.8%" },
      { key: "피싱 클릭률 감소", val: "41%" },
    ],
    preview: "ISO 27001 기반 정보보안 관리, OT 보안 강화 및 AI 기반 이상 탐지...",
    metricCount: 1,
    metrics: [{
      name: "정보보안 교육 이수율", badge: "거버넌스 지표", badgeType: "blue",
      metricId: "G-IS-01__G0001", atomicId: "G-IS-01__G0002", unit: "%", dataType: "정량",
      desc: "전 임직원 대상 정보보안 교육 연간 이수율",
      latest: "97.8%",
      trend: [{ y: 2022, v: 91.3 }, { y: 2023, v: 95.7 }, { y: 2024, v: 97.8 }],
      breakdown: [{ l: "임직원 이수율", v: "97.8%" }, { l: "피싱 클릭률", v: "전년比 -41%" }, { l: "침해 사례", v: "0건" }],
      formula: "교육 이수 인원 / 전체 임직원 수 × 100",
    }],
    aiDesc: "디지털 전환 가속화에 따른 사이버 보안 관리 수준을 정량적으로 보여주는 지표입니다.",
    related: { id: "P-03-01", label: "전략 및 방향" },
  },
  p12: {
    tag: "지배구조", tagType: "green", id: "G-BD-01",
    tooltipTitle: "● 이사회 구성",
    tooltipRows: [
      { key: "사외이사 비율", val: "66.7%" },
      { key: "여성 이사 비율", val: "22.2%" },
      { key: "이사회 출석률", val: "96.4%" },
      { key: "내부신고 건수", val: "47건" },
    ],
    preview: "이사회 독립성·다양성 강화, ESG 연계 보상 체계 및 윤리경영...",
    metricCount: 1,
    metrics: [{
      name: "이사회 사외이사 비율", badge: "거버넌스 지표", badgeType: "green",
      metricId: "G-BD-01__G0001", atomicId: "G-BD-01__G0002", unit: "%", dataType: "정량",
      desc: "전체 이사 중 사외이사 비율",
      latest: "66.7%",
      trend: [{ y: 2022, v: 55.6 }, { y: 2023, v: 62.5 }, { y: 2024, v: 66.7 }],
      breakdown: [{ l: "사내이사", v: "3명" }, { l: "사외이사", v: "6명" }, { l: "여성 이사", v: "2명" }],
      formula: "사외이사 수 / 전체 이사 수 × 100",
    }],
    aiDesc: "이사회 독립성과 다양성 수준을 보여주는 핵심 거버넌스 지표로, 경영 감독 역량을 반영합니다.",
    related: { id: "S3-01", label: "인재 개발 전략" },
  },
};

const paragraphTexts = {
  p1: `A_GROUP의 자동차 부품과 전동화 부품 사업을 총괄하는 지주회사로, 국내외 자회사와 함께 모빌리티 부품 사업을 이룬다. 보고기간은 2024.01.01~2024.12.31이며, 연결 공시 범위는 A_GROUP 본인 사업장과 B_SUB_KR, C_SUB_EU, D_SUB_US를 포함한다. 연결 매출액은 17,800,000,000,000 KRW, 연결 사업장 수는 22개이다.

SKM은 과학기반 감축목표 이니셔티브(SBTi)의 1.5°C 시나리오에 부합하는 넷제로 목표를 수립하고, 이를 달성하기 위한 중·단기 전환 계획을 체계적으로 운영하고 있다. 2030년까지 Scope 1·2 온실가스 배출량을 2022년 대비 42% 감축하고, 2045년까지 Scope 1·2·3 전 범위에 걸쳐 넷제로를 달성한다는 목표를 공식화하였다. 이를 위해 에너지 효율 개선, 재생에너지 전환, 공정 혁신 등 3대 전략 축을 중심으로 사업장별 감축 로드맵을 수립하였으며, 매년 이행 현황을 검증·공시하고 있다.

사업 전략 측면에서 SKM은 전통적인 내연기관 부품 중심의 포트폴리오에서 탈피하여, 전기차(EV) 및 하이브리드 차량용 전동화 부품, 경량화 소재, 첨단 운전자 지원 시스템(ADAS) 관련 부품 등으로 사업 구조를 재편하고 있다. 2024년 기준 전동화 부품 매출 비중은 전체 연결 매출의 약 31%에 달하며, 2027년까지 45% 이상으로 확대할 계획이다. 주요 고객사인 완성차 업체들의 전동화 전환 로드맵과 긴밀히 연계하여 신규 수주 파이프라인을 확충하고 있으며, 유럽·북미·아시아 시장에서의 현지화 생산 체계를 강화하고 있다.

지배구조 측면에서는 이사회 산하에 ESG위원회를 설치하고, ESG 전략 방향 수립과 주요 성과 지표 모니터링을 이사회 차원에서 직접 감독하는 구조를 구축하였다. CEO 및 임원진의 성과 평가 지표에 탄소 감축 목표 달성률, 안전사고 지표, 공급망 ESG 평가 결과 등을 반영함으로써 경영진의 책임성을 강화하였다. 또한 글로벌 ESG 공시 기준인 ISSB(IFRS S1·S2) 및 CSRD에 대응하기 위한 내부 데이터 수집·검증 체계를 정비하고 있으며, 2025년 보고서부터 제3자 검증 범위를 연결 기준 전체로 확대할 예정이다.`,

  p2: `A_GROUP의 2045년 넷제로 달성과 2040년 재생에너지 100% 전환을 목표로 Scope 1·2 배출 감축과 전환계획을 관리한다. 기준연도는 2019이며 기준연도 연결 Scope 1·2 배출량은 130,890 tCO₂eq이다. 보고연도 연결 Scope 1·2 배출량은 112,500 tCO₂eq, 전년 대비 감축량은 4,402 tCO₂eq, 감축률은 3.91%이다. 재생에너지 전환율은 9.49%이다.

2024년 온실가스 배출 감축 성과를 분석하면, Scope 1 직접 배출량은 38,200 tCO₂eq으로 전년 대비 2.1% 감소하였으며, Scope 2 간접 배출량은 74,300 tCO₂eq으로 전년 대비 4.8% 감소하였다. Scope 1 감축은 주로 생산 공정 내 연료 전환(천연가스 → 바이오가스 혼합 연료)과 설비 효율 개선을 통해 달성되었으며, Scope 2 감축은 국내외 사업장의 재생에너지 전력 구매 확대(PPA, REC)를 통해 이루어졌다.

사업장별 감축 현황을 살펴보면, 국내 A_GROUP 본사 사업장은 태양광 발전 설비 추가 설치(5.2MW)와 LED 조명 전면 교체를 통해 연간 2,100 tCO₂eq를 추가 감축하였다. B_SUB_KR은 압축공기 시스템 최적화 및 폐열 회수 장치 도입으로 1,200 tCO₂eq을 감축하였으며, C_SUB_EU는 독일 및 체코 사업장에서 그린 전력 구매 계약 체결을 통해 800 tCO₂eq의 Scope 2 감축을 달성하였다. D_SUB_US는 미국 텍사스 사업장에 ESS(에너지저장시스템)를 도입하여 피크 수요를 관리하고 300 tCO₂eq를 절감하였다.

2025년에는 재생에너지 전환율을 15% 이상으로 확대하고, 주요 사업장 대상 에너지 진단을 실시하여 추가 감축 기회를 발굴할 계획이다. 또한 탄소 감축 실적을 내부 탄소 가격(Internal Carbon Price, ICP)에 연계하여 사업 부문별 감축 인센티브 구조를 정비하고, 장기적으로는 탄소 포집·활용·저장(CCUS) 기술 적용 가능성을 검토하고 있다.`,

  p3: `A_GROUP의 주요 협력사의 환경·인권·윤리 리스크가 조달 안정성과 브랜드 신뢰에 미치는 영향을 고려해 공급망 지속가능성 리스크를 관리한다. 연결 기준 공급업체 감사 이행률은 71.90%, 고위험 공급업체 수는 64개사이다. 공급망 CAP 완료율은 68.09%이다.

SKM의 공급망 지속가능성 관리 체계는 협력사 등록 단계의 ESG 적격성 심사부터 거래 중 정기 감사, 리스크 발견 시 시정조치 계획(CAP) 수립 및 이행 지원, 우수 협력사 인센티브 제공에 이르는 전 주기 관리 프로세스로 구성되어 있다. 2024년에는 1차 협력사 전체(약 890개사)를 대상으로 서면 자기평가(Self-Assessment Questionnaire, SAQ)를 실시하고, 고위험으로 분류된 64개사에 대해 현장 감사를 진행하였다.

감사 결과, 환경 분야에서는 폐수 처리 기준 미달과 화학물질 관리 부적합이 주요 이슈로 식별되었으며, 노동 분야에서는 초과 근무 한도 초과 및 안전 교육 미이수가 빈번하게 지적되었다. 지배구조 분야에서는 부패·뇌물 방지 정책 부재 및 내부 신고 채널 미구축이 주요 개선 과제로 도출되었다. 이에 SKM은 각 협력사와 함께 6개월~12개월 단위의 CAP를 수립하고, 전담 컨설턴트를 통한 이행 지원 프로그램을 운영하고 있다.

공급망 환경 리스크 측면에서는 기후변화로 인한 원자재 수급 불안정, 탄소 국경 조정 메커니즘(CBAM) 도입에 따른 비용 증가 리스크도 별도로 평가하고 있다. 주요 원자재(희토류, 알루미늄, 구리)의 공급 집중 리스크를 완화하기 위해 복수 공급처 확보 및 재활용 소재 사용 비율 확대 전략을 병행하고 있으며, 2024년 기준 재활용 알루미늄 사용 비율은 전체 알루미늄 사용량의 18.3%에 달한다.`,

  p4: `전동화·자율주행·디지털화 전환에 대응하기 위해 미래 모빌리티 기술 인재 확보와 내부 역량 강화가 중요하다. 연결 임직원 수는 8,367명이며, 1인당 교육시간은 33.42시간/명, 핵심직무 교육 달성률은 72.01%이다.

SKM은 2024년 인재 전략의 핵심 방향으로 '미래 모빌리티 전문 인력 육성'과 '다양성·포용성 기반 조직 문화 강화'를 설정하였다. 전동화 및 소프트웨어 역량을 보유한 전문 인력 채용을 위해 국내외 주요 대학 및 연구기관과 산학협력 프로그램을 운영하고, 자체 기술 아카데미를 통해 기존 임직원의 직무 전환 교육을 지원하고 있다. 2024년 한 해 동안 전동화·소프트웨어 관련 신규 채용 인원은 전체 신규 채용의 34%를 차지하였다.

교육 프로그램 측면에서는 직무별 핵심역량 맵(Competency Map)을 기반으로 개인 맞춤형 학습 경로를 제공하는 디지털 학습 플랫폼(e-Learning LMS)을 운영하고 있으며, 연간 이수 기준은 직급별로 차등 적용된다. 2024년 전체 교육 투자액은 전년 대비 12.7% 증가하였으며, 리더십 프로그램 참여율은 관리직 기준 88.3%에 달하였다. 또한 글로벌 사업장 간 순환 근무 프로그램을 통해 임직원의 글로벌 역량 개발을 지원하고 있으며, 2024년 해외 파견 및 순환 근무 인원은 전년 대비 23% 증가하였다.

다양성·포용성 측면에서는 여성 관리직 비율을 2027년까지 20%로 확대하는 목표를 수립하고, 채용·승진·평가 전 과정에서의 다양성 제고 방안을 시행하고 있다. 2024년 기준 여성 관리직 비율은 14.2%로 전년 대비 1.8%p 상승하였다. 장애인 고용률은 3.1%로 법정 의무 고용률(3.1%)을 충족하였으며, 청년·고령자·경력단절 여성 등 취약계층 채용 지원 프로그램도 지속 운영 중이다.`,

  p5: `전동화 부품과 경량화·고효율 부품은 제품 사용 단계의 온실가스 감축과 환경영향 저감에 기여한다. 연결 친환경 제품 매출액은 4,298,000,000,000 KRW이며, 연결 매출 대비 비중은 24.15%이다. 회피 배출량은 1,245,000 tCO₂eq, 재화적 비용 절감 효과는 68,973,000,000 KRW로 추산된다.

SKM의 친환경 제품 포트폴리오는 전기차용 구동 모터·인버터 시스템, 하이브리드 변속기 모듈, 경량 알루미늄 구조 부품, 열 관리 시스템, 수소연료전지 부품 등으로 구성되어 있다. 2024년 전기차 플랫폼 전용 구동 모터 시스템은 신규 수주량이 전년 대비 41% 증가하였으며, 주요 완성차 고객사 5개사로부터 2026~2030년 물량 공급 계약을 체결하였다. 경량 알루미늄 부품은 차량 중량을 평균 8.3% 절감하여 연비 향상 및 주행거리 확대에 기여하고 있다.

제품 전과정 평가(LCA, Life Cycle Assessment)를 통해 친환경 제품의 환경 편익을 정량화하고 있다. 2024년 기준 SKM의 친환경 부품을 탑재한 차량이 동급 내연기관 차량 대비 회피한 온실가스 배출량은 1,245,000 tCO₂eq으로 산출되었으며, 이는 소나무 약 1억 8천만 그루가 1년간 흡수하는 탄소량에 해당하는 규모이다. 이러한 제품 환경 편익 데이터는 고객사의 Scope 3 배출량 산정에 활용될 수 있도록 제품 탄소발자국 인증(PCF) 취득을 순차적으로 진행하고 있으며, 2024년 기준 총 23개 제품 모델에 대한 PCF 인증을 완료하였다.

순환경제 측면에서는 제품 설계 단계부터 재활용 가능성을 고려한 DfE(Design for Environment) 가이드라인을 적용하고 있으며, 폐기 부품의 재제조(Remanufacturing) 및 소재 재활용 비율 확대를 위한 역물류 체계를 구축하고 있다. 2024년 제조 공정 내 발생한 폐기물 재활용률은 87.4%로 전년 대비 3.2%p 상승하였다.`,

  p6: `제품 품질과 안전은 고객 신뢰 확보와 규제 대응, 리콜 리스크 관리와 직접 연결되는 핵심 주제다. 연결 기준 리콜 건수는 10건, 리콜 건수는 3건이며, 제품안전 CAP 완료율은 70.37%이다.

SKM은 제품 개발 초기 단계부터 양산·출하·애프터서비스에 이르는 전 주기에 걸쳐 체계적인 제품 안전 관리 프로세스를 운영하고 있다. 설계 단계에서는 DFMEA(Design Failure Mode and Effects Analysis)와 DRBFM(Design Review Based on Failure Mode)을 의무 적용하고, 양산 단계에서는 PFMEA 및 관리계획서 기반의 공정 모니터링을 실시한다. 고객 인도 후에는 현장 품질 데이터를 실시간으로 수집·분석하는 VOR(Vehicle Off Road) 대응 시스템을 통해 초기 품질 이슈를 신속하게 탐지하고 있다.

2024년 발생한 리콜 3건은 모두 납품 완성차 업체와의 공동 원인 분석(Joint 8D) 과정을 거쳐 설계 변경 및 공정 개선 조치가 완료되었다. 리콜 비용은 제품책임보험을 통해 일부 보전하였으며, 장기적으로는 디지털 트윈 기반 선행 품질 예측 시스템 구축을 통해 리콜 발생 가능성을 사전에 차단하는 역량을 강화할 계획이다. 2025년에는 AI 기반 불량 예측 모델을 주요 3개 사업장에 시범 적용하고, 결과에 따라 전 사업장으로 확대할 예정이다.

고객 만족 측면에서는 연간 고객사 품질 만족도 조사를 실시하고 있으며, 2024년 종합 만족도 점수는 100점 만점에 84.7점으로 전년(82.1점) 대비 2.6점 상승하였다. 불만 처리 평균 응답 시간은 4.2시간으로 목표치(6시간 이내)를 초과 달성하였으며, 품질 클레임 건수는 전년 대비 18.3% 감소하였다.`,

  p7: `SKM은 기후 관련 재무정보공개 협의체(TCFD) 프레임워크에 기반하여 기후 리스크 및 기회 요인을 체계적으로 식별·평가·관리하고 있다. 전환 리스크 측면에서는 탄소세 확대, 내연기관 규제 강화, 저탄소 기술 전환 비용 증가 등을 핵심 리스크로 선정하였으며, 물리적 리스크 측면에서는 홍수·가뭄 등 극단적 기상 현상으로 인한 사업장 및 공급망 피해 가능성을 분석하였다.

2024년 기후 시나리오 분석(1.5°C, 2°C, 4°C)을 통해 도출한 재무 영향 추산 결과, 2°C 시나리오 하에서 2030년까지 탄소 비용 및 규제 대응 비용으로 연간 약 850억 KRW의 추가 비용이 발생할 수 있으며, 4°C 시나리오에서는 주요 사업장의 홍수 피해로 인한 생산 차질 비용이 연간 최대 1,200억 KRW에 달할 수 있는 것으로 분석되었다. 이에 대응하여 주요 사업장의 기후 적응 투자(방재 시설, 냉각 시스템 효율화, 대체 생산 거점 확보)를 2025~2027년 중기 투자 계획에 반영하였다.

기후 기회 요인으로는 전동화 전환 가속에 따른 신규 시장 창출, 재생에너지 직접 구매(PPA)를 통한 전력 비용 안정화, 친환경 제품 프리미엄 가격 실현 가능성 등이 식별되었다. 특히 EU의 배터리 규정(EU Battery Regulation) 및 탄소발자국 공시 의무화는 SKM의 LCA 기반 제품 환경 성능 데이터 경쟁력을 강화하는 기회로 작용할 것으로 전망된다.`,

  p8: `SKM은 임직원, 고객, 지역사회, 공급망, 투자자 등 다양한 이해관계자와의 소통을 통해 지속가능성 우선순위를 주기적으로 점검하고, 이를 전략과 공시에 반영하는 이중 중요성 평가 프로세스를 운영하고 있다. 2024년 이중 중요성 평가에서는 기후변화 대응, 제품 환경성, 인권 및 노동 관행, 공급망 관리, 정보보안·개인정보보호, 지배구조 투명성이 최우선 중요 주제로 선정되었다.

이해관계자별 소통 채널을 살펴보면, 임직원과는 연 2회 전사 타운홀 미팅, 상시 익명 제안 채널, 사업장별 노사 협의회를 통해 소통하고 있으며, 2024년 전임직원 대상 ESG 인식도 조사에서 응답률 78.3%, 전반적 ESG 경영에 대한 긍정 인식률 81.2%를 기록하였다. 투자자와는 연 4회 실적 발표 및 IR 미팅, 전용 ESG 투자자 설명회(2회), 지속가능성 보고서 발간을 통해 정보를 제공하고 있다.

지역사회와의 관계 측면에서는 사업장 인근 지역의 환경·안전 이슈에 대한 주민 설명회를 연 1회 이상 실시하고, 지역 고용 창출 및 중소 협력사 동반성장 프로그램을 운영하고 있다. 2024년 사회공헌 투자액은 연결 매출액 대비 0.18%인 약 320억 KRW이며, 주요 프로그램으로는 미래 모빌리티 청소년 교육, 소외계층 이동 지원, 사업장 인근 환경 복원 활동 등이 있다.`,

  p9: `SKM의 환경경영 체계는 ISO 14001 기반의 환경경영시스템(EMS)을 전 사업장에 적용하고, 연간 내부·외부 감사를 통해 준수 수준을 점검하는 구조로 운영된다. 2024년 기준 연결 기준 전체 22개 사업장 중 21개 사업장이 ISO 14001 인증을 취득하였으며, 신규 해외 사업장 1개소는 2025년 상반기 인증 취득을 목표로 시스템을 구축 중이다.

용수 관리 측면에서는 물 부족 지역(Water-Stressed Area)에 위치한 사업장을 중심으로 용수 절감 목표를 설정하고, 폐수 재이용률 확대 및 냉각수 순환 시스템 개선을 추진하고 있다. 2024년 연결 기준 총 용수 취수량은 2,340,000 m³이며, 이 중 재이용수 비율은 21.7%로 전년 대비 3.1%p 향상되었다. 폐수 방류 기준 초과 사례는 보고기간 중 발생하지 않았다.

대기오염물질 관리 측면에서는 VOCs(휘발성 유기화합물), NOx, 분진 등 주요 오염물질의 배출량을 사업장별로 측정·관리하고, 관련 규제 기준 대비 여유도를 확보하는 선제적 저감 투자를 실시하고 있다. 2024년 VOCs 배출량은 전년 대비 9.4% 감소하였으며, 이는 도장 공정의 수용성 도료 전환 및 배기가스 처리 설비 개선에 기인한다. 화학물질 안전관리 측면에서는 REACH, RoHS, ELV 등 글로벌 화학물질 규제 대응을 위한 물질 데이터베이스를 구축·운영하고 있다.`,

  p10: `SKM의 안전보건 경영 체계는 ISO 45001 기반으로 운영되며, '중대재해 제로' 달성을 최우선 목표로 설정하고 있다. 2024년 연결 기준 LTIR(Lost Time Injury Rate, 재해율)은 0.38로 전년(0.45) 대비 15.6% 개선되었으며, 산업재해 사망사고는 발생하지 않았다. 안전 선행 지표(Leading Indicator)로는 아차사고 보고 건수, 안전 관찰 활동 참여율, 위험성 평가 이행률 등을 관리하고 있으며, 2024년 임직원 1인당 아차사고 보고 건수는 1.82건으로 전년 대비 34% 증가하였다. 이는 안전 문화 성숙도가 향상되어 임직원의 자발적 위험 신고 의식이 높아졌음을 반영한다.

협력사 안전 관리 측면에서는 구내 작업 협력사 전체를 대상으로 안전보건 교육을 연 2회 이상 실시하고, 원청 책임 하에 협력사 안전 점검을 분기별로 수행하고 있다. 2024년 협력사 LTIR은 0.61로 전년(0.79) 대비 22.8% 개선되었다. 또한 중대재해처벌법 대응을 위해 안전보건 관리 체계 적합성 진단을 외부 전문기관에 의뢰하여 실시하였으며, 도출된 개선 과제 142건 중 2024년 말 기준 89.4%인 127건을 완료하였다.

정신건강 및 직원 웰빙 측면에서는 EAP(Employee Assistance Program)를 전 임직원에게 제공하고, 주요 사업장에 심리상담실을 설치·운영하고 있다. 2024년 EAP 이용률은 전체 임직원의 11.3%로 전년 대비 2.8%p 상승하였으며, 심리상담 만족도는 88.2점(100점 기준)을 기록하였다.`,

  p11: `SKM의 정보보안 및 개인정보보호 체계는 ISO 27001 기반의 정보보안 관리 시스템(ISMS)을 그룹 통합 적용하고, 연간 내부 감사와 외부 침투 테스트를 통해 보안 수준을 점검하는 구조로 운영된다. 2024년 정보보안 투자액은 전년 대비 21.3% 증가하였으며, 주요 투자 항목은 제로트러스트(Zero Trust) 아키텍처 전환, OT(Operational Technology) 보안 강화, AI 기반 이상 행위 탐지 시스템 구축 등이다.

제조 현장의 디지털화 가속에 따라 OT 환경과 IT 환경의 통합(IT/OT Convergence)이 진행되면서, 산업 제어 시스템(ICS) 및 스카다(SCADA) 시스템에 대한 사이버 위협이 증가하고 있다. SKM은 OT 전용 보안 아키텍처를 수립하고, 주요 생산 설비에 대한 네트워크 분리 및 접근 통제 강화 조치를 2024년 중 완료하였다. 또한 전 임직원 대상 연간 정보보안 교육을 의무화하고, 피싱 메일 모의 훈련을 분기별로 실시하고 있으며, 2024년 피싱 클릭률은 전년 대비 41% 감소하였다.

개인정보보호 측면에서는 GDPR(유럽 일반개인정보보호법) 및 국내 개인정보보호법 준수를 위한 데이터 처리 활동 기록(ROPA)을 유지하고, 개인정보 영향평가(DPIA)를 신규 서비스 출시 시 의무 실시하고 있다. 2024년 개인정보 침해 신고 사례는 발생하지 않았으며, 개인정보보호 관련 임직원 교육 이수율은 97.8%로 전년 대비 2.1%p 상승하였다.`,

  p12: `SKM은 투명하고 책임있는 지배구조를 구축하기 위해 이사회 구성의 다양성과 독립성 강화, 경영진 보상의 ESG 연계, 윤리경영 및 반부패 체계 고도화를 지속 추진하고 있다. 2024년 기준 이사회는 사내이사 3명, 사외이사 6명으로 구성되어 있으며, 사외이사 비율은 66.7%로 코드(Code) 권고 기준(과반수)을 초과 달성하였다. 이사회 내 여성 이사 비율은 22.2%(사외이사 2명)이며, 평균 재임 기간은 4.3년이다.

이사회 전문성 측면에서는 모빌리티·기술, 재무·회계, 법률·규제, ESG·환경 등 다양한 분야의 전문성을 보유한 이사진을 구성하고, 연간 이사회 역량 평가(Board Effectiveness Review)를 통해 전문성 갭을 분석하고 보완하고 있다. 2024년 이사회 평균 출석률은 96.4%이며, 이사회 결의 안건 126건 중 8건은 소수 의견이 부기된 것으로 나타나 충실한 심의 문화를 반영한다.

윤리경영 및 반부패 측면에서는 '윤리강령' 및 '부패방지 정책'을 전 임직원과 협력사에 적용하고, 내부신고 시스템(Whistleblowing)을 통한 익명 제보 채널을 24시간 운영하고 있다. 2024년 내부신고 접수 건수는 47건이며, 이 중 27건이 실질적 조사 대상으로 분류되어 관련 징계 조치 및 프로세스 개선이 이루어졌다. 협력사를 포함한 이해관계자 대상 반부패 교육 이수율은 94.1%로 전년 대비 3.3%p 상승하였다.`,
};

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
  const [savedAt, setSavedAt] = useState(null); // 마지막 저장 시각
  
  // ── 상태 정의 ──
  const [isEditing, setIsEditing] = useState(false); // 본문 수정 모드 상태
  const [texts, setTexts] = useState(paragraphTexts); // 실시간 수정 가능한 텍스트 데이터 상태
  const [exportMenuOpen, setExportMenuOpen] = useState(false); // 내보내기 드롭다운 상태
  
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // ── SR 템플릿 데이터 연결 (페이지별 웹 편집 → 미리보기/PDF 동일 반영) ──
  // 실제 API/state 가 생기면 actualMetricRows 로 연결. 현재는 빈 배열 + 페이지별 편집값.
  const actualMetricRows = []; // ← 실제 source 연결 시 교체 (더미 금지)

  // 특정 페이지의 metrics Map / 본문 (페이지 키별 편집값 + 소속 서브이슈 adapter)
  const buildPageMetrics = (pageObj) =>
    buildMetricsFromEdits(pageObj.adapter, editMetricsByPage[pageObj.key], actualMetricRows);
  const buildPageNarrative = (key) => {
    const t = (editNarrativeByPage[key] || "").trim();
    return t ? t : null; // 비어 있으면 템플릿이 지표값으로 자동 조합
  };

  const STORAGE_KEY = "draft-sr-edits-v1";

  // 저장된 편집값 불러오기 (최초 마운트 시)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed.metrics) setEditMetricsByPage(parsed.metrics);
      if (parsed.narrative) setEditNarrativeByPage(parsed.narrative);
      if (parsed.savedAt) setSavedAt(parsed.savedAt);
    } catch (e) {
      console.warn("저장된 편집값 로드 실패:", e);
    }
  }, []);

  // 저장: 현재 편집값을 영속화. (백엔드 미연동 → localStorage. 실제 API는 TODO 지점에 연결)
  const handleSaveEdits = () => {
    const now = new Date().toISOString();
    const payload = { metrics: editMetricsByPage, narrative: editNarrativeByPage, savedAt: now };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      setSavedAt(now);
      // TODO(R2): 여기서 실제 저장 API 호출 (예: await api.saveReportDraft(payload))
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
    if (!isEditing) return;
    const el = e.target.closest("[data-source]");
    if (!el) return; // 본문의 일반 문구(토큰 아님)는 data-source가 없어 contentEditable 편집으로 넘어감
    const src = el.getAttribute("data-source");
    if (!src || src.includes(",")) return; // 파생/복합값(예: 기준연도 대비 %)은 편집 제외
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

      // ── 서브이슈별로 각각 독립 PDF 1개 생성 → 개별 파일로 저장 ──
      for (const si of subIssues) {
        const pdf = new jsPDF("l", "mm", "a4"); // SR 템플릿 A4 가로(landscape)
        const pageW = pdf.internal.pageSize.getWidth();   // 297
        const pageH = pdf.internal.pageSize.getHeight();  // 210

        const pdfPageOf = {}; // page.key → 이 PDF 내 페이지 번호
        const tocLinks = [];
        const subnavLinks = [];

        // PDF 1쪽: 이 서브이슈 목차
        const tocEl = root.querySelector(`#pdf-toc-${si.id}`);
        if (tocEl) {
          const tocCanvas = await renderEl(tocEl);
          const tocImgH = Math.min((tocCanvas.height * pageW) / tocCanvas.width, pageH);
          pdf.addImage(tocCanvas.toDataURL("image/png"), "PNG", 0, 0, pageW, tocImgH);
          const tocRect = tocEl.getBoundingClientRect();
          const tocMmPerPx = pageW / tocRect.width;
          si.pages.forEach((p) => {
            const item = root.querySelector(`#pdf-tocitem-${si.id}-${p.key}`);
            if (!item) return;
            const r = item.getBoundingClientRect();
            tocLinks.push({
              key: p.key,
              x: (r.left - tocRect.left) * tocMmPerPx,
              y: (r.top - tocRect.top) * tocMmPerPx,
              w: r.width * tocMmPerPx,
              h: r.height * tocMmPerPx,
            });
          });
        }

        // PDF 2~쪽: 이 서브이슈의 각 페이지
        for (const page of si.pages) {
          const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
          if (!sec) continue;
          const canvas = await renderEl(sec);
          pdf.addPage();
          const thisPdfPage = pdf.getNumberOfPages();
          pdfPageOf[page.key] = thisPdfPage;
          const imgH = (canvas.height * pageW) / canvas.width;
          pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, pageW, imgH);

          // subnav 탭 → 같은 서브이슈 내 해당 페이지로 이동 링크
          const secRect = sec.getBoundingClientRect();
          const mmPerPx = pageW / secRect.width;
          sec.querySelectorAll(".sr-subnav span:not(.dot)").forEach((tab, ti) => {
            if (ti >= si.pages.length) return;
            const r = tab.getBoundingClientRect();
            subnavLinks.push({
              onPdfPage: thisPdfPage,
              x: (r.left - secRect.left) * mmPerPx,
              y: (r.top - secRect.top) * mmPerPx,
              w: r.width * mmPerPx,
              h: r.height * mmPerPx,
              targetKey: si.pages[ti].key,
            });
          });
        }

        // 링크 주입: 목차(1쪽) → 페이지, 각 페이지 subnav 탭 → 페이지
        if (tocLinks.length) {
          pdf.setPage(1);
          tocLinks.forEach((l) => {
            const t = pdfPageOf[l.key];
            if (t) pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
          });
        }
        subnavLinks.forEach((l) => {
          const t = pdfPageOf[l.targetKey];
          if (!t) return;
          pdf.setPage(l.onPdfPage);
          pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
        });

        // 서브이슈별 개별 파일로 저장 (climate-target.pdf 등)
        pdf.save(`${si.exportName || si.id}.pdf`);
        // 브라우저가 다중 다운로드를 막지 않도록 약간의 간격
        await new Promise((r) => setTimeout(r, 300));
      }
    } finally {
      setPdfMode(false);
    }
    return;
  }

  if (type === "Word") {
    const children = [
      new Paragraph({ text: "기후목표·전환계획", heading: HeadingLevel.HEADING_1 }),
      new Paragraph({ text: "전환 리스크에 선제적으로 대응하는 넷제로 로드맵", heading: HeadingLevel.HEADING_2 }),
      new Paragraph({ text: "" }),
    ];

    Object.keys(paragraphData).forEach((pid) => {
      const d = paragraphData[pid];
      children.push(
        new Paragraph({
          children: [new TextRun({ text: d.tag, bold: true, color: "03A94D" })],
          spacing: { before: 200 },
        }),
        new Paragraph({
          children: [new TextRun({ text: texts[pid], size: 22 })],
          spacing: { after: 160 },
        })
      );
    });

    const doc = new Document({ sections: [{ children }] });
    const blob = await Packer.toBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sustainability_draft.docx";
    a.click();
    URL.revokeObjectURL(url);
    return;
  }

  if (type === "Excel") {
    const rows = [["태그", "단락 ID", "본문 내용"]];
    Object.keys(paragraphData).forEach((pid) => {
      rows.push([paragraphData[pid].tag, paragraphData[pid].id, texts[pid]]);
    });
    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws["!cols"] = [{ wch: 14 }, { wch: 12 }, { wch: 80 }];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "본문");
    XLSX.writeFile(wb, "sustainability_draft.xlsx");
    return;
  }

  if (type === "JSON") {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(
      JSON.stringify({ info: paragraphData, contents: texts }, null, 2)
    );
    const a = document.createElement("a");
    a.setAttribute("href", dataStr);
    a.setAttribute("download", "sustainability_draft.json");
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
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

  return (
    <div className="draft-container">
      <header className="draft-header">
     
        <div className="draft-stepper-row">
          {steps.map((step, index) => (
            <div key={step.id} style={{ display: "flex", alignItems: "center" }}>
              <div
                className={`step-box ${index === activeIndex ? "active" : ""}`}
                onClick={() => { if (index !== activeIndex) navigate(step.path); }}
              >
                <div className="step-icon-circle">{step.icon}</div>
                <div style={{ fontSize: "0.8rem", fontWeight: 850 }}>{step.title}</div>
              </div>
              {index < steps.length - 1 && <div className="step-line"></div>}
            </div>
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
                  <span>🏠</span><span className="bc-sep">›</span>
                  <span className="bc-item">환경경영</span><span className="bc-sep">›</span>
                  <span className="bc-item active">기후변화와 대응</span>
                </div>
                <div className="doc-page-info">페이지 1 / 5</div>
                
                <div className="doc-actions">
                  {/* 1. 독립된 본문 수정 버튼 (Toggle 형태) */}
                  <button 
                    className={`doc-btn ${isEditing ? "editing-active" : ""}`} 
                    onClick={() => setIsEditing(!isEditing)}
                    style={{ fontWeight: isEditing ? "bold" : "normal" }}
                  >
                    {isEditing ? "💾 수정 완료" : "✏️ 본문 수정"}
                  </button>

                  {/* 2. 분리된 파일 내려받기 드롭다운 버튼 */}
                  <div className="save-dropdown-container" ref={dropdownRef} style={{ position: "relative", display: "inline-block", flexShrink: 0 }}>
                    <button className="doc-btn export-toggle-btn" onClick={() => setExportMenuOpen(!exportMenuOpen)}>
                      📥 파일 내려받기 <span style={{ fontSize: "0.7rem", marginLeft: "4px" }}>▼</span>
                    </button>
                    
                    {exportMenuOpen && (
                      <ul className="save-dropdown-menu" style={{
                        position: "absolute", top: "100%", right: 0, marginTop: "6px",
                        background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px",
                        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)", padding: "6px 0",
                        listStyle: "none", zIndex: 50, minWidth: "145px"
                      }}>
                        <li onClick={() => handleExport("PDF")} style={dropdownItemStyle}>📄 PDF 다운로드</li>
                        <li onClick={() => handleExport("Word")} style={dropdownItemStyle}>📝 Word (Docx) 저장</li>
                        <li onClick={() => handleExport("Excel")} style={dropdownItemStyle}>📊 Excel 데이터 추출</li>
                        <li onClick={() => handleExport("JSON")} style={dropdownItemStyle}>⚙️ JSON 데이터 추출</li>
                      </ul>
                    )}
                  </div>
                </div>
              </div>

              <div className="doc-content">
                <h1 className="doc-title">기후목표·전환계획</h1>
                <p className="doc-subtitle">전환 리스크에 선제적으로 대응하는 넷제로 로드맵</p>

                {/* 목차 */}
                <div id="toc-section" style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "24px 32px", marginBottom: "32px" }}>
                  <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#1e293b", marginBottom: "16px", paddingBottom: "10px", borderBottom: "2px solid #03A94D", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>📋</span> 목차
                  </h2>
                  <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
                    {PAGES.map((page, idx) => {
                      const active = idx === currentPage;
                      return (
                        <li key={page.key} id={`toc-item-${page.key}`}>
                          <button
                            onClick={(e) => { e.stopPropagation(); goToPage(idx); }}
                            style={{
                              display: "flex", alignItems: "center", gap: "8px",
                              width: "100%", border: "none",
                              background: active ? "#e2e8f0" : "none",
                              cursor: "pointer", padding: "7px 8px", borderRadius: "6px",
                              textAlign: "left", transition: "background 0.15s",
                            }}
                            onMouseEnter={e => { if (!active) e.currentTarget.style.background = "#eef2f7"; }}
                            onMouseLeave={e => { e.currentTarget.style.background = active ? "#e2e8f0" : "none"; }}
                          >
                            <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: 700, minWidth: "20px" }}>
                              {String(idx + 1).padStart(2, "0")}
                            </span>
                            <span className="para-chip blue" style={{ fontSize: "0.68rem", padding: "2px 7px", flexShrink: 0 }}>
                              {page.tocTag}
                            </span>
                            <span style={{ fontSize: "0.8rem", color: active ? "#03A94D" : "#334155", fontWeight: active ? 700 : 400, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {page.tocTitle}
                            </span>
                            <span style={{ fontSize: "0.72rem", color: "#03A94D", fontWeight: 600, flexShrink: 0 }}>→</span>
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
                        narrativeText={buildPageNarrative(page.key)}
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
                    style={{ position: "fixed", top: inlineEdit.top, left: inlineEdit.left, width: inlineEdit.width, zIndex: 1000 }}
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
            <div className={`draft-panel ${currentPid && !isEditing ? "open" : ""}`} id="draftPanel">
              {data && metric ? (
                <div className="panel-inner">
                  <div className="panel-hd">
                    <span className="panel-hd-title">데이터 추적</span>
                    <button className="panel-close-btn" onClick={() => setCurrentPid(null)}>✕</button>
                  </div>

                  {/* <div className="panel-section">
                    <div className="panel-section-title">선택 문단</div>
                    <span className={`para-chip ${data.tagType}`}>{data.tag}</span>
                    <p className="para-preview-text">{texts[currentPid]}</p>
                    <span className="para-id-link">문단 ID: {data.id}</span>
                  </div> */}

                  <div className="panel-section">
                    <div className="panel-section-title">참조 지표 ({data.metricCount})</div>
                    <div className="metric-accordion">
                      <div
                        className={`metric-acc-header ${metricOpen ? "open" : ""}`}
                        onClick={() => setMetricOpen((v) => !v)}
                      >
                        <div className="metric-acc-header-left">
                          <span className="metric-acc-name">{metric.name}</span>
                          <span className={`metric-badge ${metric.badgeType}`}>{metric.badge}</span>
                        </div>
                        <span className="metric-acc-chevron">›</span>
                      </div>

                      {metricOpen && (
                        <div className="metric-acc-body">
                          <div className="metric-row">
                            <span className="metric-row-key">metric_id</span>
                            <span className="metric-row-val">{metric.metricId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">atomic_metric_id</span>
                            <span className="metric-row-val">{metric.atomicId}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">지표명</span>
                            <span className="metric-row-val">{metric.name}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">단위</span>
                            <span className="metric-row-val">{metric.unit}</span>
                          </div>
                          <div className="metric-row">
                            <span className="metric-row-key">데이터 유형</span>
                            <span className="metric-row-val">{metric.dataType}</span>
                          </div>
                          <hr className="metric-divider" />
                          <div className="metric-row">
                            <span className="metric-row-key">설명</span>
                            <span className="metric-row-val metric-row-val--muted">{metric.desc}</span>
                          </div>
                          <div className="metric-latest-box">
                            <span className="metric-latest-label">최신 데이터 (2024)</span>
                            <span className="metric-latest-val">{metric.latest}</span>
                          </div>

                          <div className="trend-section">
                            <div className="trend-section-title">추이</div>
                            <div className="trend-chart-wrap">
                              <TrendChart trend={metric.trend} />
                            </div>
                          </div>

                          {metric.breakdown && (
                            <div className="panel-subsection">
                              <div className="trend-section-title">
                                데이터 구성 ({metric.trend[metric.trend.length - 1].y})
                              </div>
                              <table className="breakdown-table">
                                <thead>
                                  <tr>
                                    <th>구분</th>
                                    <th className="breakdown-val">값 ({metric.unit})</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {metric.breakdown.map((b, i) => (
                                    <tr key={i}>
                                      <td>{b.l}</td>
                                      <td className="breakdown-val">{b.v}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}

                          <div className="panel-subsection">
                            <div className="trend-section-title">계산식/산출 방식</div>
                            <div className="formula-box">
                              {metric.formula.split("\n").map((line, i, arr) => (
                                <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">AI 근거 생성</div>
                    <div className="ai-desc-box">{data.aiDesc}</div>
                  </div>

                  <div className="panel-section">
                    <div className="panel-section-title">관련 문단</div>
                    <div className="related-para-link">
                      <span className="related-para-label">{data.related.id} {data.related.label}</span>
                      <button className="related-para-btn">이동</button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="panel-empty-text" style={{ padding: "40px", color: "#64748b", textAlign: "center" }}>
                  문단을 선택하면 데이터 추적 정보가 표시됩니다.
                </div>
              )}
            </div>

          </div>
        </div>
      </main>

      {/* ── PDF 내보내기용: 서브이슈별로 (목차 + 페이지들)을 화면 밖에 풀사이즈로 렌더 ──
          id 에 서브이슈를 prefix 하여 export 시 서브이슈별로 묶어 캡처. 평소엔 렌더 안 함 */}
      {pdfMode && (
        <div
          id="pdf-render-root"
          style={{ position: "fixed", left: "-99999px", top: 0, width: "297mm", background: "#fff", zIndex: -1 }}
        >
          {subIssues.map((si) => (
            <div key={si.id} data-subissue={si.id}>
              <div
                id={`pdf-toc-${si.id}`}
                style={{ width: "297mm", padding: "20mm 22mm", boxSizing: "border-box", fontFamily: '"Noto Sans KR", sans-serif' }}
              >
                <div style={{ fontSize: "13px", fontWeight: 700, color: "#34805c", marginBottom: "4px" }}>{si.subLabel}</div>
                <div style={{ fontSize: "22px", fontWeight: 800, color: "#16241f", marginBottom: "6px" }}>{si.label} · 목차</div>
                <div style={{ height: "2px", background: "#1b5e44", marginBottom: "18px" }} />
                {si.pages.map((p, i) => (
                  <div
                    key={p.key}
                    id={`pdf-tocitem-${si.id}-${p.key}`}
                    style={{ display: "flex", alignItems: "center", gap: "10px", padding: "11px 6px", borderBottom: "1px solid #e2eae5", fontSize: "13px", color: "#16241f" }}
                  >
                    <span style={{ fontWeight: 800, color: "#8c9893", minWidth: "26px" }}>{String(i + 1).padStart(2, "0")}</span>
                    <span style={{ fontWeight: 700, color: "#1b5e44" }}>{p.tocTag}</span>
                    <span style={{ flex: 1 }}>{p.tabLabel}</span>
                    <span style={{ color: "#34805c", fontWeight: 600 }}>p.{p.props.pageNumber} →</span>
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
                      narrativeText={buildPageNarrative(page.key)}
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



const dropdownItemStyle = {
  padding: "10px 16px",
  fontSize: "0.85rem",
  color: "#334155",
  cursor: "pointer",
  transition: "background 0.2s",
  textAlign: "left"
};
export default Draft;