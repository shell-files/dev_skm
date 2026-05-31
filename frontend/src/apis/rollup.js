/**
 * Rollup API Client
 *
 * Backend endpoints:
 *   GET  /api/v1/rollups/subsidiaries
 *   POST /api/v1/rollups/batches
 *   GET  /api/v1/rollups/requests
 *   POST /api/v1/rollups/batches/{batchId}/sources/send
 *   GET  /api/v1/rollups/batches/{batchId}/status
 *   POST /api/v1/rollups/batches/{batchId}/calculate
 */
import { GET, POST } from "@utils/Network";

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
