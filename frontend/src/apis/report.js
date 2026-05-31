/**
 * Report / G0 / Rollup API Client
 *
 * Backend endpoints are routed through the existing Network.js helper.
 * Do not place absolute backend URLs in this file.
 */
import { GET, POST, PATCH } from "@utils/Network";

export const DEFAULT_REPORTING_YEAR = 2025;

export const getCurrent = (companyId, reportingYear = DEFAULT_REPORTING_YEAR) => {
  const params = companyId == null ? undefined : { companyId, reportingYear };
  return GET("/api/v1/report-workflow/current", params);
};

export const startWorkflow = (payload) =>
  POST("/api/v1/report-workflow/start", payload);

export const getG0Status = (runId) =>
  GET(`/api/v1/report-workflow/${runId}/g0-status`);

export const getG0Profile = (companyId, reportingYear = DEFAULT_REPORTING_YEAR) =>
  GET(`/api/v1/company-profile/g0/${companyId}`, { reportingYear });

export const saveG0Profile = (companyId, payload) =>
  PATCH(`/api/v1/company-profile/g0/${companyId}`, payload);

export const getG0ProfileStatus = (companyId, reportingYear = DEFAULT_REPORTING_YEAR) =>
  GET(`/api/v1/company-profile/g0/${companyId}/status`, { reportingYear });

export const listSubsidiaries = (runId) =>
  GET("/api/v1/rollups/subsidiaries", { runId });

export const saveBatch = (payload) =>
  POST("/api/v1/rollups/batches", payload);

export const listRequests = () =>
  GET("/api/v1/rollups/requests");

export const sendSource = (batchId) =>
  POST(`/api/v1/rollups/batches/${batchId}/sources/send`);

export const getBatchStatus = (batchId) =>
  GET(`/api/v1/rollups/batches/${batchId}/status`);

export const calcBatch = (batchId) =>
  POST(`/api/v1/rollups/batches/${batchId}/calculate`);
