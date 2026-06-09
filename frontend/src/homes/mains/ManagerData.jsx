import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams, useLocation } from "react-router";
import "@styles/Manager.css";
import DataTab from "./DataTab.jsx";
import { showConfirmAlert, showDefaultAlert } from "@components/UI/ServiceAlert";
import { useAuth } from "@hooks/AuthContext";
import ApprovalProjectSelectModal from "./modal/ApprovalProjectSelectModal";
import { APPROVAL_PROJECT_PREVIEW_ROWS } from "@/dev/step12UiPreview/fixtures";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
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

const USE_LEGACY_USER_FIXTURE = STEP12_UI_FIXTURE_ENABLED;
const PAGE_SIZE = 10;
const SUPPORTED_APPROVAL_CYCLE_TYPES = [
  "PRE_DMA_G0",
  "POST_DMA_DISCLOSURE",
  "ROLLUP_RESPONSE",
];

const LEGACY_USER_FIXTURE_CATEGORY_MAP = {
  general: ["General", "Business model", "Report basis", "Management"],
  environmental: ["Climate", "Energy", "Water", "Pollution"],
  social: ["Labor", "Safety", "Human Rights", "Community"],
  governance: ["Governance", "Risk", "Compliance", "Ethics"],
};

const ALL_LEGACY_GROUPS = [
  ...LEGACY_USER_FIXTURE_CATEGORY_MAP.general,
  ...LEGACY_USER_FIXTURE_CATEGORY_MAP.environmental,
  ...LEGACY_USER_FIXTURE_CATEGORY_MAP.social,
  ...LEGACY_USER_FIXTURE_CATEGORY_MAP.governance,
];

const mockUsers = [
  {
    id: 1,
    name: "Consultant",
    email: "consultant@skm.com",
    company: "SKM",
    role: "CONSULTANT",
    deleteYn: "N",
    relations: { consultant: true, employee: false },
    groups: ALL_LEGACY_GROUPS,
  },
  {
    id: 2,
    name: "Assignee",
    email: "assignee@skm.com",
    company: "SKM",
    role: "ASSIGNEE",
    deleteYn: "N",
    relations: { consultant: false, employee: true },
    groups: ["Water", "Pollution"],
  },
  {
    id: 3,
    name: "Manager",
    email: "manager@skm.com",
    company: "SKM",
    role: "ESG_MANAGER",
    deleteYn: "N",
    relations: { consultant: false, employee: true },
    groups: ALL_LEGACY_GROUPS,
  },
];

const safeArray = (value) => (Array.isArray(value) ? value : []);

const normalizeStatus = (value) =>
  String(value || "NOT_STARTED").trim().toUpperCase();

const mapApprovalItemToInput = (item = {}) => {
  const approvalStatus = normalizeStatus(item.approvalStatus);
  const missingAtomicIds = safeArray(item.missingAtomicMetricIds);
  const completedCount = Number(item.completedAtomicCount || 0);
  const requiredCount = Number(item.requiredAtomicCount || 0);
  const missingCount =
    missingAtomicIds.length || Math.max(requiredCount - completedCount, 0);

  return {
    ...item,
    id: item.metricId,
    metricId: item.metricId,
    metricName: item.metricName || item.metricId,
    service: item.service || "disclosure",
    issueDomain: item.issueDomain || "general",
    issueGroup: item.issueGroup || null,
    subIssueId: item.subIssueId ?? null,
    subIssueCode: item.subIssueCode || null,
    subIssueName: item.subIssueName || null,
    status: approvalStatus,
    approvalStatus,
    submitStatus: ["SUBMITTED", "REVIEWED", "APPROVED", "REJECTED"].includes(
      approvalStatus
    )
      ? "SUBMITTED"
      : "DRAFT",
    reviewStatus: [
      "REVIEWED",
      "APPROVED",
      "REJECTED",
    ].includes(approvalStatus)
      ? "REVIEWED"
      : "PENDING",
    inputCompletedCount: completedCount,
    inputMissingCount: missingCount,
    assigneeName:
      item.assigneeName ||
      item.assigneeEmailMasked ||
      (item.assigneeUserId ? `user#${item.assigneeUserId}` : "-"),
    userName:
      item.assigneeName ||
      item.assigneeEmailMasked ||
      (item.assigneeUserId ? `user#${item.assigneeUserId}` : "-"),
    actionSupportedYn: item.actionSupportedYn,
    actionDisabledReason: item.actionDisabledReason,
  };
};

const basisLabel = (basisType) => {
  if (basisType === "CONSOLIDATED") return "연결 기준";
  if (basisType === "ENTITY") return "독립 기준";
  return "기준 미선택";
};

const runStatusLabel = (runStatus) => {
  const status = String(runStatus || "ACTIVE").toUpperCase();
  if (status === "COMPLETED") return "완료";
  if (status === "ARCHIVED") return "보관됨";
  return "진행 중";
};

const formatStageLabel = (label) => {
  if (!label) return "-";
  const lower = String(label).toLowerCase();
  if (lower.includes("g0") || lower.includes("pre_dma")) return "경영일반 입력";
  if (lower.includes("all approvals") || lower.includes("completed")) return "데이터 승인 완료";
  if (lower.includes("disclosure") || lower.includes("post_dma")) return "보고서 연결 공시 승인";
  return label;
};

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
    STEP12_UI_FIXTURE_ENABLED
  );
  const [inputs, setInputs] = useState([]);
  const [users, setUsers] = useState([]);
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

  const approvalProjects = STEP12_UI_FIXTURE_ENABLED
    ? APPROVAL_PROJECT_PREVIEW_ROWS
    : approvalProjectsFromStore;

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

  const hasConsultant = useMemo(
    () =>
      safeArray(users).some((entry) => {
        const roleText = String(entry.role || "").toUpperCase();
        return (
          entry.company === selectedCompanyName &&
          (roleText.includes("CONSULTANT") || entry.relations?.consultant)
        );
      }),
    [users, selectedCompanyName]
  );

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
    if (cycleTypeQuery === "ROLLUP_RESPONSE" && rollupResponseBatchId) {
      queueMicrotask(() => {
        setInputs([]);
        setSelectedIds([]);
        setDataPage(1);
        setIsApprovalProjectModalOpen(false);
      });
      return;
    }

    if (location.state?.skipProjectModal && selectedApprovalProject) {
      // Retain the injected project context, do not open modal
      queueMicrotask(() => {
        setInputs([]);
        setSelectedIds([]);
        setDataPage(1);
      });
      return;
    }

    dispatch(clearApprovalProject());
    queueMicrotask(() => {
      setInputs([]);
      setSelectedIds([]);
      setDataPage(1);
    });

    if (!companyId) return;

    if (STEP12_UI_FIXTURE_ENABLED) {
      queueMicrotask(() => {
        setIsApprovalProjectModalOpen(true);
      });
      return;
    }

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
      } catch (error) {
        console.error("ROLLUP_RESPONSE approval context restore failed:", error);
      }
    };

    restoreRollupApprovalContext();
    return () => {
      cancelled = true;
    };
  }, [cycleTypeQuery, dispatch, reportingYear, rollupResponseBatchId]);

  const fetchData = useCallback(async () => {
    if (USE_LEGACY_USER_FIXTURE) {
      setUsers(mockUsers);
    }

    if (
      !companyId ||
      (
        isRollupResponseApproval
          ? !approvalBatchId || !selectedProjectMatchesRollupBatch
          : !effectiveApprovalProject
      )
    ) {
      setInputs([]);
      return;
    }

    if (STEP12_UI_FIXTURE_ENABLED) {
      setInputs([]);
      return;
    }

    try {
      const response = await dispatch(
        fetchApprovalItems({
          companyId,
          reportingYear: approvalReportingYear,
          cycleType: approvalCycleType,
          assignedOnlyYn: true,
          batchId: approvalBatchId,
        })
      ).unwrap();
      const items = safeArray(response?.data?.items ?? response?.items);
      setInputs(items.map(mapApprovalItemToInput));
    } catch (error) {
      console.error("Approval inbox fetch failed:", error);
      setInputs([]);
    }
  }, [
    approvalCycleType,
    approvalBatchId,
    approvalReportingYear,
    companyId,
    dispatch,
    effectiveApprovalProject,
    isRollupResponseApproval,
    selectedProjectMatchesRollupBatch,
  ]);

  useEffect(() => {
    queueMicrotask(() => {
      fetchData();
    });
  }, [fetchData]);

  useEffect(() => {
    if (STEP12_UI_FIXTURE_ENABLED) return;
    queueMicrotask(() => {
      setInputs(safeArray(approvalItems).map(mapApprovalItemToInput));
    });
  }, [approvalItems]);

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
    [approvalBatchId, buildApprovalPayload, dispatch]
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
      await dispatchApprovalMutation(id, normalizedStatus, commentText);
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
            <h2 className="page-title">ESG 통합 관리</h2>
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
