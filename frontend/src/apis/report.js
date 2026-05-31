/**
 * Report & Workflow & Rollup API Client
 *
 * Backend endpoints:
 *   GET  /api/v1/report-workflow/current
 *   POST /api/v1/report-workflow/start
 *   GET  /api/v1/report-workflow/{runId}/g0-status
 *   GET  /api/v1/rollups/subsidiaries
 *   POST /api/v1/rollups/batches
 *   GET  /api/v1/rollups/requests
 *   POST /api/v1/rollups/batches/{batchId}/sources/send
 *   GET  /api/v1/rollups/batches/{batchId}/status
 *   POST /api/v1/rollups/batches/{batchId}/calculate
 */
import { GET, POST, PATCH } from "@utils/Network";

export const DEFAULT_REPORTING_YEAR = 2025;

const mapWorkflow = (data) => {
  if (!data) return data;

  return {
    ...data,
    financialBasis: data.reportBasisType || data.financialBasis,
    isParent: data.companyRole === "PARENT",
    isSubsidiary: data.companyRole === "SUBSIDIARY",
    canStartDma: data.nextAction === "START_DMA" && data.dmaReadyYn === true,
    canRequestSubsidiaries: data.nextAction === "REQUEST_ROLLUP" && data.g0InputReadyYn === true,
    shouldWaitRollup: data.nextAction === "WAIT_ROLLUP",
    canCalculateRollup: data.nextAction === "CALCULATE_ROLLUP",
  };
};

/** 현재 workflow 상태 조회 */
export const getCurrent = async (companyId, reportingYear) => {
  const res = await GET(
    `/api/v1/report-workflow/current?companyId=${companyId}&reportingYear=${reportingYear}`
  );

  if (res?.data) {
    res.data = mapWorkflow(res.data);
  }

  return res;
};

/** workflow 시작 (발행 기준 선택 후) */
export const startWorkflow = (payload) =>
  POST("/api/v1/report-workflow/start", payload);

/** 특정 run의 G0 입력·승인 상태 조회 */
export const getG0Status = async (runId) => {
  const res = await GET(`/api/v1/report-workflow/${runId}/g0-status`);

  if (res?.data) {
    res.data = mapWorkflow(res.data);
  }

  return res;
};

/** 자회사 목록 조회 */
export const listSubsidiaries = (runId) =>
  GET("/api/v1/rollups/subsidiaries", { runId });

/** 롤업 배치 생성 (자회사 요청) */
export const saveBatch = (payload) =>
  POST("/api/v1/rollups/batches", payload);

/** 자회사 측 요청 목록 조회 */
export const listRequests = () =>
  GET("/api/v1/rollups/requests");

/** 자회사 → 지주사 데이터 전송 */
export const sendSource = (batchId) =>
  POST(`/api/v1/rollups/batches/${batchId}/sources/send`);

/** 배치 상태 조회 */
export const getStatus = (batchId) =>
  GET(`/api/v1/rollups/batches/${batchId}/status`);

/** 롤업 계산 실행 */
export const calcBatch = (batchId) =>
  POST(`/api/v1/rollups/batches/${batchId}/calculate`);

/** G0 Profile 데이터 조회 */
export const getG0Profile = (companyId, reportingYear) =>
  GET(`/api/v1/company-profile/g0/${companyId}`, { reportingYear });

/** G0 Profile 데이터 저장 */
export const saveG0Profile = (companyId, payload) =>
  PATCH(`/api/v1/company-profile/g0/${companyId}`, payload);

/** G0 Profile 상태 조회 */
export const getG0ProfileStatus = (companyId, reportingYear) =>
  GET(`/api/v1/company-profile/g0/${companyId}/status`, { reportingYear });
