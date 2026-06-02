/**
 * Report / G0 / Rollup API Client
 *
 * Backend endpoints are routed through the existing Network.js helper.
 * Do not place absolute backend URLs in this file.
 */
import { GET, POST, PATCH } from "@utils/Network";

export const DEFAULT_REPORTING_YEAR = new Date().getFullYear();

const normalizeDirectDtoResponse = (res) => {
  if (!res || res?.status === false || res?.success === false) {
    return res;
  }
  if (res?.data) {
    return res;
  }
  return {
    success: true,
    data: res,
  };
};

export const getCurrent = (companyId, reportingYear = DEFAULT_REPORTING_YEAR) => {
  const params = companyId == null ? undefined : { companyId, reportingYear };
  return GET("/reportWorkflow/current", params);
};

export const startWorkflow = (payload) =>
  POST("/reportWorkflow/start", payload);

export const resumeWorkflow = (runId) =>
  POST(`/reportWorkflow/${runId}/resume`);

export const getG0Status = (runId) =>
  GET(`/reportWorkflow/${runId}/g0-status`);

export const getOnboardingMetrics = async (
  companyId,
  reportingYear = DEFAULT_REPORTING_YEAR,
  cycleType = "PRE_DMA_G0",
  metricId
) => {
  const params = { companyId, reportingYear, cycleType };
  if (metricId) {
    params.metricId = metricId;
  }
  return normalizeDirectDtoResponse(
    await GET("/onboarding", params)
  );
};

export const saveOnboardingMetricValues = async (metricId, payload) =>
  normalizeDirectDtoResponse(
    await PATCH(`/onboarding/${metricId}`, payload)
  );

export const listSubsidiaries = (runId) =>
  GET("/rollup/subsidiaries", { runId });

export const saveBatch = (payload) =>
  POST("/rollup/batches", payload);

export const listRequests = () =>
  GET("/rollup/requests");

export const sendSource = (batchId) =>
  POST(`/rollup/batches/${batchId}/sources/send`);

export const getBatchStatus = (batchId) =>
  GET(`/rollup/batches/${batchId}/status`);

export const calcBatch = (batchId) =>
  POST(`/rollup/batches/${batchId}/calculate`);
