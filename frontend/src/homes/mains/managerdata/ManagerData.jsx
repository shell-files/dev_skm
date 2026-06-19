/**
 * ManagerData.jsx
 * 데이터 승인 관리 페이지 — 매니저가 승인 사이클별 메트릭 데이터를 검토·승인.
 * ApprovalProjectSelectModal로 프로젝트 선택 후 DataTab에서 테이블 표시.
 *
 * 주요 상태:
 *   selectedProject   — 현재 선택된 승인 프로젝트 (runId/basisType/cycleType 포함)
 *   selectedCycleType — 승인 사이클 타입 필터
 *
 * 주요 흐름:
 *   1. ApprovalProjectSelectModal에서 프로젝트 선택
 *   2. fetchApprovalItems로 해당 사이클 메트릭 목록 로드
 *   3. DataTab에서 도메인 탭별 검토·승인 액션
 *
 * 의존:
 *   managerDataUtils.js    — 상수, mapApprovalItemToInput 변환 헬퍼
 *   DataTab.jsx            — 도메인별 데이터 테이블 컴포넌트
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams, useLocation } from "react-router";
import "@styles/Manager.css";
import DataTab from "./DataTab.jsx";
import { showConfirmAlert, showDefaultAlert } from "@components/UI/ServiceAlert";
import { useAuth } from "@hooks/AuthContext";
import ApprovalProjectSelectModal from "../modal/ApprovalProjectSelectModal";
import PageHeader from "@components/UI/PageHeader";
import EmptyState from "@components/UI/EmptyState";
import {
  DEFAULT_REPORTING_YEAR,
  clearApprovalProject,
  fetchApprovalItems,
  fetchOnboardingApprovalDetail,
  fetchApprovalProjects,
  fetchRollupRequestDetail,
  approveOnboardingApproval,
  selectApprovalProject,
  rejectOnboardingApproval,
  reviewOnboardingApproval,
} from "@stores/reportSlice";
import {
  PAGE_SIZE, SUPPORTED_APPROVAL_CYCLE_TYPES,
  safeArray, normalizeStatus, mapApprovalItemToInput,
  basisLabel, runStatusLabel, formatStageLabel,
} from "./managerDataUtils";


const ManagerData = () => {
  const dispatch = useDispatch();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const approvalItems = useSelector((state) => state.report?.approval?.items ?? []);
  const approvalLoading = useSelector((state) => state.report?.loading?.approvals ?? false);
  const approvalError = useSelector((state) => state.report?.error?.approvals ?? null);
  const approvalDetail = useSelector(
    (state) => state.report?.approval?.selectedItemDetail ?? null
  );
  const approvalDetailLoading = useSelector(
    (state) => state.report?.loading?.approvalDetail ?? false
  );
  const approvalDetailError = useSelector(
    (state) => state.report?.error?.approvalDetail ?? null
  );
  const reviewLoading = useSelector(
    (state) => state.report?.loading?.onboardingApprovalReview ?? false
  );
  const approveLoading = useSelector(
    (state) => state.report?.loading?.onboardingApprovalApprove ?? false
  );
  const rejectLoading = useSelector(
    (state) => state.report?.loading?.onboardingApprovalReject ?? false
  );
  const approvalProjectsFromStore = useSelector(
    (state) => state.report?.approval?.projects ?? []
  );
  const selectedApprovalProject = useSelector(
    (state) => state.report?.approval?.selectedProject ?? null
  );
  const approvalProjectsLoading = useSelector(
    (state) => state.report?.loading?.approvalProjects ?? false
  );
  const approvalProjectsError = useSelector(
    (state) => state.report?.error?.approvalProjects ?? null
  );

  const [activeTab] = useState("data");
  const [activeService] = useState("disclosure");
  const [isApprovalProjectModalOpen, setIsApprovalProjectModalOpen] = useState(
    false
  );
  const [activeSubCategory, setActiveSubCategory] = useState("all");
  const [selectedIds, setSelectedIds] = useState([]);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectTargetId, setRejectTargetId] = useState(null);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [activeDataCategory, setActiveDataCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dataPage, setDataPage] = useState(1);

  const { user, selectedCompany } = useAuth();

  const companyId =
    selectedCompany?.company_id ?? selectedCompany?.companyId ?? null;
  const reportingYear =
    selectedCompany?.reporting_year ??
    selectedCompany?.reportingYear ??
    DEFAULT_REPORTING_YEAR;
  const cycleTypeQuery = String(searchParams.get("cycleType") || "")
    .trim()
    .toUpperCase();
  const batchIdQuery = searchParams.get("batchId");
  const rollupResponseBatchId = useMemo(() => {
    const parsed = Number(batchIdQuery);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
  }, [batchIdQuery]);
  const [approvalCycleType, setApprovalCycleType] = useState(
    SUPPORTED_APPROVAL_CYCLE_TYPES.includes(cycleTypeQuery)
      ? cycleTypeQuery
      : "PRE_DMA_G0"
  );

  const selectedCompanyName =
    selectedCompany?.name ??
    selectedCompany?.company_name ??
    selectedCompany?.companyName ??
    selectedCompany?.company_code ??
    "SKM";

  const userRole = selectedCompany?.role ?? user?.role ?? "guest";

  const approvalProjects = approvalProjectsFromStore;

  const isRollupResponseApproval = approvalCycleType === "ROLLUP_RESPONSE";
  const approvalBatchId = isRollupResponseApproval
    ? rollupResponseBatchId
    : undefined;
  const selectedProjectBatchId = Number(selectedApprovalProject?.batchId);
  const selectedProjectMatchesRollupBatch =
    !isRollupResponseApproval ||
    (
      rollupResponseBatchId !== undefined &&
      Number.isInteger(selectedProjectBatchId) &&
      selectedProjectBatchId === rollupResponseBatchId
    );
  const effectiveApprovalProject = selectedProjectMatchesRollupBatch
    ? selectedApprovalProject
    : null;

  const approvalReportingYear =
    effectiveApprovalProject?.reportingYear ?? reportingYear;

  const selectedProjectReadOnlyYn = Boolean(effectiveApprovalProject?.readOnlyYn);
  const hasValidRollupApprovalContext =
    !isRollupResponseApproval ||
    (
      Number.isInteger(approvalBatchId) &&
      approvalBatchId > 0 &&
      selectedProjectMatchesRollupBatch &&
      Boolean(effectiveApprovalProject)
    );
  const hasValidApprovalContext = isRollupResponseApproval
    ? hasValidRollupApprovalContext
    : Boolean(effectiveApprovalProject);

  const hasConsultant = false;

  const fallbackApprovalProject = {
    runId: null,
    reportingYear,
    reportBasisType:
      selectedCompany?.report_basis_type ?? selectedCompany?.reportBasisType ?? null,
    runStatus: "ACTIVE",
    workflowStep: "G0_ONBOARDING",
    currentStageLabel: "경영일반 입력",
    readOnlyYn: false,
  };

  const displayApprovalProject =
    effectiveApprovalProject ?? fallbackApprovalProject;

  useEffect(() => {
    if (
      SUPPORTED_APPROVAL_CYCLE_TYPES.includes(cycleTypeQuery) &&
      cycleTypeQuery !== approvalCycleType
    ) {
      queueMicrotask(() => {
        setApprovalCycleType(cycleTypeQuery);
        setSelectedIds([]);
        setDataPage(1);
        setIsRejectModalOpen(false);
      });
    }
  }, [approvalCycleType, cycleTypeQuery]);

  const handleApprovalCycleTypeChange = useCallback(
    (event) => {
      const nextCycleType = String(event.target.value || "").trim().toUpperCase();
      const normalized = SUPPORTED_APPROVAL_CYCLE_TYPES.includes(nextCycleType)
        ? nextCycleType
        : "PRE_DMA_G0";
      setApprovalCycleType(normalized);
      setSelectedIds([]);
      setDataPage(1);
      setIsRejectModalOpen(false);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set("cycleType", normalized);
      setSearchParams(nextParams);
    },
    [searchParams, setSearchParams]
  );

  const handleSelectApprovalProject = useCallback(
    (project) => {
      dispatch(selectApprovalProject(project));
      setSelectedIds([]);
      setDataPage(1);
      setIsApprovalProjectModalOpen(false);
    },
    [dispatch]
  );

  useEffect(() => {
    if (cycleTypeQuery === "ROLLUP_RESPONSE") {
      queueMicrotask(() => {
        setSelectedIds([]);
        setDataPage(1);
        setIsRejectModalOpen(false);
        setIsApprovalProjectModalOpen(false);
      });
      return;
    }

    if (location.state?.skipProjectModal && selectedApprovalProject) {
      // Retain the injected project context, do not open modal
      queueMicrotask(() => {
        setSelectedIds([]);
        setDataPage(1);
      });
      return;
    }

    dispatch(clearApprovalProject());
    queueMicrotask(() => {
      setSelectedIds([]);
      setDataPage(1);
    });

    if (!companyId) return;

    dispatch(fetchApprovalProjects({ companyId }))
      .unwrap()
      .catch((error) => {
        console.error("Approval project list fetch failed:", error);
      })
      .finally(() => {
        setIsApprovalProjectModalOpen(true);
      });
  }, [companyId, cycleTypeQuery, location.state?.skipProjectModal, rollupResponseBatchId]);

  useEffect(() => {
    if (cycleTypeQuery !== "ROLLUP_RESPONSE" || !rollupResponseBatchId) return;

    let cancelled = false;
    const restoreRollupApprovalContext = async () => {
      try {
        const response = await dispatch(
          fetchRollupRequestDetail({ batchId: rollupResponseBatchId })
        ).unwrap();
        if (cancelled) return;

        const detail = response?.data || response;
        const transferStatus = String(
          detail?.transferStatus ||
          detail?.sourceStatus?.transferStatus ||
          ""
        ).trim().toUpperCase();

        dispatch(
          selectApprovalProject({
            runId: null,
            reportingYear: detail?.reportingYear ?? reportingYear,
            cycleType: "ROLLUP_RESPONSE",
            batchId: rollupResponseBatchId,
            readOnlyYn: transferStatus === "SENT" || transferStatus === "RECEIVED",
            currentStageLabel: "자회사 데이터 승인",
          })
        );
        if (!cancelled) {
          await dispatch(
            fetchApprovalItems({
              companyId,
              reportingYear: detail?.reportingYear ?? reportingYear,
              cycleType: "ROLLUP_RESPONSE",
              assignedOnlyYn: true,
              batchId: rollupResponseBatchId,
            })
          ).unwrap();
        }
      } catch (error) {
        console.error("ROLLUP_RESPONSE approval context restore failed:", error);
      }
    };

    restoreRollupApprovalContext();
    return () => {
      cancelled = true;
    };
  }, [companyId, cycleTypeQuery, dispatch, reportingYear, rollupResponseBatchId]);

  const fetchData = useCallback(async () => {
    if (!companyId || !hasValidApprovalContext) {
      return;
    }

    try {
      await dispatch(
        fetchApprovalItems({
          companyId,
          reportingYear: approvalReportingYear,
          cycleType: approvalCycleType,
          assignedOnlyYn: true,
          batchId: approvalBatchId,
        })
      ).unwrap();
    } catch (error) {
      console.error("Approval inbox fetch failed:", error);
    }
  }, [
    approvalCycleType,
    approvalBatchId,
    approvalReportingYear,
    companyId,
    dispatch,
    hasValidApprovalContext,
  ]);

  useEffect(() => {
    queueMicrotask(() => {
      fetchData();
    });
  }, [fetchData]);

  const inputs = useMemo(() => {
    if (!hasValidApprovalContext) return [];
    return safeArray(approvalItems).map(mapApprovalItemToInput);
  }, [approvalItems, hasValidApprovalContext]);

  const kpi = useMemo(
    () =>
      safeArray(inputs).reduce(
        (acc, item) => {
          const status = normalizeStatus(item.approvalStatus || item.status);
          if (status === "APPROVED") acc.approved += 1;
          else if (status === "REJECTED") acc.rejected += 1;
          else acc.waiting += 1;
          return acc;
        },
        { approved: 0, waiting: 0, rejected: 0 }
      ),
    [inputs]
  );

  const totalDataPages = useMemo(
    () => Math.max(1, Math.ceil(safeArray(inputs).length / PAGE_SIZE)),
    [inputs]
  );

  const isLoading = approvalLoading || approvalProjectsLoading;
  const approvalMutationLoading = reviewLoading || approveLoading || rejectLoading;

  const buildApprovalPayload = useCallback(
    (metricId, commentText = "") => ({
      companyId,
      reportingYear: approvalReportingYear,
      cycleType: approvalCycleType,
      metricId,
      ...(approvalCycleType === "ROLLUP_RESPONSE" ? { batchId: approvalBatchId } : {}),
      ...(commentText?.trim() ? { commentText: commentText.trim() } : {}),
    }),
    [approvalBatchId, approvalCycleType, approvalReportingYear, companyId]
  );

  const dispatchApprovalMutation = useCallback(
    async (metricId, status, commentText = "") => {
      if (isRollupResponseApproval && !approvalBatchId) {
        showDefaultAlert(
          "오류",
          "데이터 요청 정보가 없습니다. 받은 요청함에서 다시 진입해 주세요.",
          "error"
        );
        return false;
      }
      const payload = buildApprovalPayload(metricId, commentText);
      if (status === "REVIEWED") {
        return dispatch(reviewOnboardingApproval({ payload, batchId: approvalBatchId })).unwrap();
      }
      if (status === "APPROVED") {
        return dispatch(approveOnboardingApproval({ payload, batchId: approvalBatchId })).unwrap();
      }
      if (status === "REJECTED") {
        return dispatch(rejectOnboardingApproval({ payload, batchId: approvalBatchId })).unwrap();
      }
      throw new Error(`Unsupported approval action: ${status}`);
    },
    [approvalBatchId, buildApprovalPayload, dispatch, isRollupResponseApproval]
  );

  const handleFetchApprovalDetail = useCallback(
    async (metricId) => {
      const response = await dispatch(
        fetchOnboardingApprovalDetail({
          companyId,
          reportingYear: approvalReportingYear,
          metricId,
          cycleType: approvalCycleType,
          batchId: approvalBatchId,
        })
      ).unwrap();
      return response?.data || response;
    },
    [approvalBatchId, approvalCycleType, approvalReportingYear, companyId, dispatch]
  );

  const handleAction = async (id, status, commentText = "") => {
    if (selectedProjectReadOnlyYn) {
      showDefaultAlert("알림", "완료된 프로젝트는 읽기 전용입니다.", "info");
      return false;
    }
    if (isRollupResponseApproval && !approvalBatchId) {
      showDefaultAlert(
        "오류",
        "데이터 요청 정보가 없습니다. 받은 요청함에서 다시 진입해 주세요.",
        "error"
      );
      return false;
    }

    const normalizedStatus = normalizeStatus(status);
    if (normalizedStatus === "REJECTED" && !commentText?.trim()) {
      setRejectTargetId(id);
      setRejectReason("");
      setIsRejectModalOpen(true);
      return false;
    }

    const ok = await showConfirmAlert("확인", "해당 항목을 처리하시겠습니까?", "question");
    if (!ok) return false;

    try {
      const mutationResult = await dispatchApprovalMutation(id, normalizedStatus, commentText);
      if (mutationResult === false) return false;
      await fetchData();
      showDefaultAlert("완료", "승인 작업이 처리되었습니다.", "success");
      return true;
    } catch (error) {
      console.error(error);
      showDefaultAlert(
        "오류",
        error?.message || error?.detail || "승인 작업 처리에 실패했습니다.",
        "error"
      );
      return false;
    }
  };

  const handleBulkAction = async (status, commentText = "") => {
    if (selectedProjectReadOnlyYn) {
      showDefaultAlert("알림", "완료된 프로젝트는 읽기 전용입니다.", "info");
      return false;
    }
    if (isRollupResponseApproval && !approvalBatchId) {
      showDefaultAlert(
        "오류",
        "데이터 요청 정보가 없습니다. 받은 요청함에서 다시 진입해 주세요.",
        "error"
      );
      return false;
    }
    if (!selectedIds.length) return false;

    const ok = await showConfirmAlert("일괄 처리", "계속하시겠습니까?", "question");
    if (!ok) return false;

    const normalizedStatus = normalizeStatus(status);
    if (normalizedStatus === "REJECTED" && !commentText?.trim()) {
      showDefaultAlert("알림", "반려 사유를 입력하세요.", "info");
      return false;
    }

    const succeeded = [];
    const failed = [];
    for (const metricId of selectedIds) {
      try {
        await dispatchApprovalMutation(metricId, normalizedStatus, commentText);
        succeeded.push(metricId);
      } catch (error) {
        failed.push({
          metricId,
          message: error?.message || error?.detail || "처리 실패",
        });
      }
    }
    await fetchData();
    setSelectedIds([]);
    if (failed.length) {
      showDefaultAlert(
        "주의",
        `${succeeded.length}건 처리, ${failed.length}건 실패했습니다.`,
        "warning"
      );
      return false;
    }
    showDefaultAlert("완료", `${succeeded.length}건 처리되었습니다.`, "success");
    return true;
  };

  const handleMainCategoryChange = useCallback((category) => {
    setActiveDataCategory(category);
    setActiveSubCategory("all");
    setDataPage(1);
  }, []);

  return (
    <div id="manager_page">
      <div className="manager-content-container">
        <div className="page-header">
          <div className="page-title-area">
            <PageHeader
              category="ESG 통합 관리"
              title="ESG 통합 관리"
              description="연도별 프로젝트, 승인 현황, 데이터 진행 상태를 관리합니다."
              iconClass="bi-leaf-fill"
            />
          </div>
        </div>

        <section className="approval-project-context-bar">
          <div className="approval-project-context-main">
            <p className="approval-project-context-label">현재 보고서 프로젝트</p>
            <h3 className="approval-project-context-title">
              {displayApprovalProject.reportingYear} 지속가능경영보고서
            </h3>
            <p className="approval-project-context-meta">
              {basisLabel(displayApprovalProject.reportBasisType)}
              {" · "}
              {runStatusLabel(displayApprovalProject.runStatus)}
            </p>
          </div>

          <div className="approval-project-context-stage">
            <p className="approval-project-context-label">현재 단계</p>
            <strong>{formatStageLabel(displayApprovalProject.currentStageLabel)}</strong>
          </div>

          <div className="approval-project-context-actions">
            <label
              className="approval-cycle-type-control"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              <span className="approval-project-context-label">승인 범위</span>
              <select
                value={approvalCycleType}
                onChange={handleApprovalCycleTypeChange}
                disabled={isLoading || approvalMutationLoading || isRollupResponseApproval}
                style={{
                  height: "34px",
                  border: "1px solid #d1d5db",
                  borderRadius: "6px",
                  padding: "0 8px",
                  fontSize: "0.85rem",
                }}
              >
                <option value="PRE_DMA_G0">경영일반 데이터</option>
                <option value="POST_DMA_DISCLOSURE">중대성 이슈 데이터</option>
                <option value="ROLLUP_RESPONSE">자회사 요청 대응 데이터</option>
              </select>
            </label>
            {displayApprovalProject.readOnlyYn && (
              <span className="approval-project-context-readonly-chip">읽기 전용</span>
            )}
            <button
              type="button"
              className="approval-project-change-btn"
              disabled={approvalProjectsLoading || approvalProjects.length === 0 || isRollupResponseApproval}
              aria-disabled={isRollupResponseApproval}
              title={
                isRollupResponseApproval
                  ? "ROLLUP_RESPONSE approval context is fixed by batch."
                  :
                approvalProjects.length === 0
                  ? "No report projects are available."
                  : ""
              }
              onClick={() => {
                if (isRollupResponseApproval) return;
                setIsApprovalProjectModalOpen(true);
              }}
            >
              프로젝트 변경
            </button>
          </div>
        </section>

        {approvalProjectsError && (
          <div className="alert alert-warning" style={{ marginBottom: "12px" }}>
            {approvalProjectsError.message ||
              "보고서 프로젝트 목록을 불러오지 못했습니다."}
          </div>
        )}

        {approvalError && (
          <div className="alert alert-warning" style={{ marginBottom: "12px" }}>
            {approvalError.message || "승인 목록을 불러오지 못했습니다."}
          </div>
        )}

        <div className="kpi-container">
          {[
            { key: "APPROVED", label: "승인됨", count: kpi.approved },
            { key: "PENDING", label: "대기 중", count: kpi.waiting },
            { key: "REJECTED", label: "반려됨", count: kpi.rejected },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() =>
                !isLoading &&
                setStatusFilter(item.key === statusFilter ? "all" : item.key)
              }
              className={`kpi-card ${statusFilter === item.key ? "active" : ""} ${
                isLoading ? "disabled" : ""
              }`}
            >
              <div className="kpi-label">{item.label}</div>
              <div className="kpi-value">{item.count}</div>
            </button>
          ))}
        </div>

        {activeTab === "data" && (
          <div className="manager-data-tab-container">
            {!hasValidRollupApprovalContext ? (
              <EmptyState
                title="데이터 요청 정보가 없습니다."
                desc="받은 요청함에서 다시 진입해 주세요."
              />
            ) : (
              <DataTab
                activeService={activeService}
                isLoading={isLoading}
                activeDataCategory={activeDataCategory}
                activeSubCategory={activeSubCategory}
                selectedIds={selectedIds}
                setSelectedIds={setSelectedIds}
                pagedInputs={inputs}
                totalDataPages={totalDataPages}
                dataPage={dataPage}
                userRole={userRole}
                hasConsultant={hasConsultant}
                statusFilter={statusFilter}
                readOnlyYn={selectedProjectReadOnlyYn}
                handleMainCategoryChange={handleMainCategoryChange}
                setActiveSubCategory={setActiveSubCategory}
                handleBulkAction={handleBulkAction}
                fetchData={fetchData}
                setDataPage={setDataPage}
                handleAction={handleAction}
                actionLoading={approvalMutationLoading}
                approvalDetail={approvalDetail}
                approvalDetailLoading={approvalDetailLoading}
                approvalDetailError={approvalDetailError}
                fetchApprovalDetail={handleFetchApprovalDetail}
              />
            )}
          </div>
        )}

        {isRejectModalOpen && (
          <div className="modal-overlay">
            <div className="modal-window">
              <div className="modal-header">
                <h3>항목 반려</h3>
                <button
                  type="button"
                  className="close-x"
                  onClick={() => setIsRejectModalOpen(false)}
                >
                  x
                </button>
              </div>
              <div className="modal-body">
                <textarea
                  className="reject-textarea"
                  placeholder="반려 사유를 입력하세요."
                  value={rejectReason}
                  onChange={(event) => setRejectReason(event.target.value)}
                  style={{
                    width: "100%",
                    height: "120px",
                    padding: "10px",
                    border: "1px solid #ddd",
                    borderRadius: "6px",
                  }}
                />
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-confirm"
                  onClick={async () => {
                    if (!rejectReason.trim()) {
                      showDefaultAlert("알림", "반려 사유를 입력하세요.", "info");
                      return;
                    }
                    const success = await handleAction(rejectTargetId, "REJECTED", rejectReason);
                    if (success) {
                      setIsRejectModalOpen(false);
                    }
                  }}
                >
                  반려 확인
                </button>
              </div>
            </div>
          </div>
        )}

        <ApprovalProjectSelectModal
          isOpen={isApprovalProjectModalOpen}
          projects={approvalProjects}
          selectedRunId={effectiveApprovalProject?.runId ?? null}
          onSelectProject={handleSelectApprovalProject}
          onClose={() => setIsApprovalProjectModalOpen(false)}
        />
      </div>
    </div>
  );
};

export default ManagerData;
