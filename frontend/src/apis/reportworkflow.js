/**
 * Report Workflow API Client
 *
 * Backend endpoints:
 *   GET  /api/v1/report-workflow/current
 *   POST /api/v1/report-workflow/start
 *   GET  /api/v1/report-workflow/{runId}/g0-status
 */
import { GET, POST } from "@utils/Network";

/** 현재 workflow 상태 조회 */
export const getCurrent = () =>
  GET("/api/v1/report-workflow/current");

/** workflow 시작 (발행 기준 선택 후) */
export const startWorkflow = (payload) =>
  POST("/api/v1/report-workflow/start", payload);

/** 특정 run의 G0 입력·승인 상태 조회 */
export const getG0Status = (runId) =>
  GET(`/api/v1/report-workflow/${runId}/g0-status`);
