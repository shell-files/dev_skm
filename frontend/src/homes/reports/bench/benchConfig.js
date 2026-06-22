/**
 * benchConfig.js
 * 벤치마킹 분석 설정 및 결과 매핑 유틸.
 * BenchMarking.jsx에서 import하여 사용.
 *
 * exports:
 *   BENCHMARK_GROUP_CONFIG       — 그룹(leader/peer/sub) UI 메타 설정
 *   mapBenchmarkResultToDashboard — API DTO → 대시보드 표시 데이터 변환
 */

/** 그룹별 API fileType, 표시 레이블, 뱃지 문자, 색상 테마 */
export const BENCHMARK_GROUP_CONFIG = {
  leader: { fileType: "Leader", label: "리더",  letter: "L", color: "green"  },
  peer:   { fileType: "Peer",   label: "피어",  letter: "P", color: "blue"   },
  sub:    { fileType: "Own",    label: "자사",  letter: "S", color: "orange" },
};

/** fetchBenchmarkResult API 응답 DTO → BenchResultDashboard props.displayData 형태로 변환 */
export const mapBenchmarkResultToDashboard = (dto) => ({
  stats: {
    reports: dto.summary?.analyzedReportCount ?? 0,
    leaderCount: dto.summary?.leaderReportCount ?? 0,
    peerCount: dto.summary?.peerReportCount ?? 0,
    ownCount: dto.summary?.ownReportCount ?? 0,
    identifiedIssues: dto.summary?.identifiedIssueCount ?? 0,
    commonIssues: dto.summary?.commonIssueCount ?? 0,
    blindSpots: dto.summary?.blindSpotCount ?? 0,
  },
  topIssues: (dto.topIssues || []).map((item) => ({
    rank: item.rankNo,
    name: item.displaySubIssueName || item.subIssueCode,
    impact: item.benchmarkImpactScore10 ?? item.benchmarkImpactScore05 ?? 0,
    financial: item.benchmarkFinancialScore10 ?? item.benchmarkFinancialScore05 ?? 0,
  })),
  commonIssues: (dto.commonIssues || []).map((item) => ({
    name: item.displaySubIssueName || item.subIssueCode,
    leader: Boolean(item.leaderObserved),
    peer: Boolean(item.peerObserved),
    own: Boolean(item.ownObserved),
  })),
  blindSpots: (dto.blindSpotIssues || []).map((item) => ({
    title: item.displaySubIssueName || item.subIssueCode,
    desc: item.summary || "리더·피어 보고서 대비 자사 보고서에서 관측되지 않은 이슈입니다.",
  })),
});
