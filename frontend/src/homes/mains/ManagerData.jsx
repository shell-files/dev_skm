import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import "@styles/Manager.css";
import DataTab from "./DataTab.jsx";
import { showConfirmAlert, showDefaultAlert } from "@components/UI/ServiceAlert";
import { useAuth } from "@hooks/AuthContext";
import ApprovalProjectSelectModal from "./modal/ApprovalProjectSelectModal";
import { APPROVAL_PROJECT_PREVIEW_ROWS } from "@/dev/step12UiPreview/fixtures";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import {
  DEFAULT_REPORTING_YEAR,
  fetchApprovalItems,
} from "@stores/reportSlice";

const USE_LEGACY_USER_FIXTURE = true;
const PAGE_SIZE = 10;

/**
 * LEGACY USER MANAGEMENT FIXTURE ONLY.
 * 승인 작업함 production scope/filter source로 사용하지 않는다.
 * 후속 인원 관리 API 연결 시 제거 대상이다.
 */
const LEGACY_USER_FIXTURE_CATEGORY_MAP = {
  general: ["회사개요", "사업구조", "보고정보", "경영일반"],
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
    name: "이채훈",
    email: "chaehoon@skm.com",
    company: "SKM",
    role: "컨설턴트",
    deleteYn: "N",
    relations: { consultant: true, employee: false },
    groups: ALL_LEGACY_GROUPS,
  },
  {
    id: 2,
    name: "김하영",
    email: "hayoung@skm.com",
    company: "SKM",
    role: "부서담당자",
    deleteYn: "N",
    relations: { consultant: false, employee: true },
    groups: ["Water", "Pollution"],
  },
  {
    id: 3,
    name: "이정빈",
    email: "jungbin@skm.com",
    company: "SKM",
    role: "관리자",
    deleteYn: "N",
    relations: { consultant: false, employee: true },
    groups: ALL_LEGACY_GROUPS,
  },
  {
    id: 4,
    name: "최수아",
    email: "sua@skm.com",
    company: "SKM",
    role: "ESG담당자",
    deleteYn: "N",
    relations: { consultant: false, employee: true },
    groups: ["Governance", "Compliance"],
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
  const missingCount = missingAtomicIds.length || Math.max(requiredCount - completedCount, 0);

  return {
    ...item,
    id: item.metricId,
    metricId: item.metricId,
    metricName: item.metricName || item.metricId,
    service: item.service || "disclosure",
    issueDomain: item.issueDomain || "general",
    issueGroup: item.issueGroup || "경영일반",
    status: approvalStatus,
    approvalStatus,
    submitStatus: ["SUBMITTED", "REVIEWED", "APPROVED", "REJECTED"].includes(approvalStatus)
      ? "SUBMITTED"
      : "DRAFT",
    reviewStatus: ["APPROVED", "REJECTED"].includes(approvalStatus) ? "REVIEWED" : "PENDING",
    inputCompletedCount: completedCount,
    inputMissingCount: missingCount,
    assigneeName: item.assigneeUserId ? `user#${item.assigneeUserId}` : "-",
    userName: item.assigneeUserId ? `user#${item.assigneeUserId}` : "-",
    actionSupportedYn: item.actionSupportedYn,
    actionDisabledReason: item.actionDisabledReason,
  };
};

const ManagerData = () => {
  const dispatch = useDispatch();
  const approvalItems = useSelector((state) => state.report?.approval?.items ?? []);
  const approvalLoading = useSelector((state) => state.report?.loading?.approvals ?? false);
  const approvalError = useSelector((state) => state.report?.error?.approvals ?? null);

  const [activeTab, setActiveTab] = useState('data');
  const [activeService] = useState("disclosure");

  const [selectedApprovalProject, setSelectedApprovalProject] = useState(null);
  const [isApprovalProjectModalOpen, setIsApprovalProjectModalOpen] = useState(STEP12_UI_FIXTURE_ENABLED);

  const approvalProjects = STEP12_UI_FIXTURE_ENABLED ? APPROVAL_PROJECT_PREVIEW_ROWS : [];

  const handleSelectApprovalProject = (project) => {
    setSelectedApprovalProject(project);
    setIsApprovalProjectModalOpen(false);
  };

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
    selectedCompany?.company_id ??
    selectedCompany?.companyId ??
    null;
  const reportingYear =
    selectedCompany?.reporting_year ??
    selectedCompany?.reportingYear ??
    DEFAULT_REPORTING_YEAR;
  const cycleType = "PRE_DMA_G0";

  const selectedCompanyName =
    selectedCompany?.name ??
    selectedCompany?.company_name ??
    selectedCompany?.companyName ??
    selectedCompany?.company_code ??
    "SKM";

  const userRole = selectedCompany?.role ?? user?.role ?? "guest";

  const hasConsultant = useMemo(() => {
    return safeArray(users).some((entry) => {
      const roleText = String(entry.role || "").toUpperCase();
      return (
        entry.company === selectedCompanyName &&
        (roleText.includes("CONSULTANT") || String(entry.role || "").includes("컨설턴트"))
      );
    });
  }, [users, selectedCompanyName]);

  const fallbackApprovalProject = {
    runId: null,
    reportingYear: 2026,
    reportBasisType: selectedCompany?.report_basis_type ?? selectedCompany?.reportBasisType ?? null,
    runStatus: "ACTIVE",
    workflowStep: "G0_ONBOARDING",
    currentStageLabel: "경영일반 승인",
    readOnlyYn: false,
  };

  const displayApprovalProject = selectedApprovalProject ?? fallbackApprovalProject;

  const fetchData = useCallback(async () => {
    if (USE_LEGACY_USER_FIXTURE) {
      setUsers(mockUsers);
    }
    if (!companyId) {
      setInputs([]);
      return;
    }
    try {
      const response = await dispatch(
        fetchApprovalItems({
          companyId,
          reportingYear,
          cycleType,
          assignedOnlyYn: true,
        })
      ).unwrap();
      const items = safeArray(response?.data?.items ?? response?.items);
      setInputs(items.map(mapApprovalItemToInput));
    } catch (error) {
      console.error("Approval inbox fetch failed:", error);
      setInputs([]);
    }
  }, [companyId, cycleType, dispatch, reportingYear]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    setInputs(safeArray(approvalItems).map(mapApprovalItemToInput));
  }, [approvalItems]);

  const kpi = useMemo(() => {
    return safeArray(inputs).reduce(
      (acc, item) => {
        const status = normalizeStatus(item.approvalStatus || item.status);
        if (status === "APPROVED") acc.approved += 1;
        else if (status === "REJECTED") acc.rejected += 1;
        else acc.waiting += 1;
        return acc;
      },
      { approved: 0, waiting: 0, rejected: 0 }
    );
  }, [inputs]);

  const totalDataPages = useMemo(
    () => Math.max(1, Math.ceil(safeArray(inputs).length / PAGE_SIZE)),
    [inputs]
  );

  const toggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    const ids = safeArray(inputs).map((item) => item.id);
    const allSelected = ids.length > 0 && ids.every((id) => selectedIds.includes(id));
    setSelectedIds(
      allSelected
        ? selectedIds.filter((id) => !ids.includes(id))
        : [...new Set([...selectedIds, ...ids])]
    );
  };

  const handleAction = async (id, status, commentText = "") => {
    const normalizedStatus = normalizeStatus(status);
    if (normalizedStatus === "REJECTED" && !commentText?.trim()) {
      setRejectTargetId(id);
      setRejectReason("");
      setIsRejectModalOpen(true);
      return;
    }

    const ok = await showConfirmAlert("확인", "처리하시겠습니까?", "question");
    if (!ok) return;

    setInputs((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: normalizedStatus,
              approvalStatus: normalizedStatus,
              ...(normalizedStatus === "REJECTED" ? { reason: commentText.trim() } : {}),
            }
          : item
      )
    );
  };

  const handleBulkAction = async (status, commentText = "") => {
    if (!selectedIds.length) return;
    const ok = await showConfirmAlert("일괄 처리", "진행하시겠습니까?", "question");
    if (!ok) return;

    const normalizedStatus = normalizeStatus(status);
    setInputs((prev) =>
      prev.map((item) =>
        selectedIds.includes(item.id)
          ? {
              ...item,
              status: normalizedStatus,
              approvalStatus: normalizedStatus,
              ...(normalizedStatus === "REJECTED" ? { reason: commentText.trim() } : {}),
            }
          : item
      )
    );
    setSelectedIds([]);
  };

  const handleMainCategoryChange = useCallback((category) => {
    setActiveDataCategory(category);
    setActiveSubCategory("all");
    setDataPage(1);
  }, []);

  const isLoading = approvalLoading;

  return (
    <div id="manager_page">
      <div className="manager-content-container">
        <div className="page-header">
          <div className="page-title-area">
            <h2 className="page-title">ESG 통합 관리 시스템</h2>
          </div>

          <section className="approval-project-context-bar">
            <div className="approval-project-context-main">
              <p className="approval-project-context-label">현재 보고서 프로젝트</p>
              <h3 className="approval-project-context-title">
                {displayApprovalProject.reportingYear} 지속가능경영보고서
              </h3>
              <p className="approval-project-context-meta">
                {displayApprovalProject.reportBasisType === "CONSOLIDATED" ? "연결 기준" : "개별 기준"}
                {" · "}
                {displayApprovalProject.runStatus === "COMPLETED" ? "완료" : "진행 중"}
              </p>
            </div>

            <div className="approval-project-context-stage">
              <p className="approval-project-context-label">현재 단계</p>
              <strong>{displayApprovalProject.currentStageLabel}</strong>
            </div>

            <div className="approval-project-context-actions">
              {displayApprovalProject.readOnlyYn && (
                <span className="approval-project-readonly-chip">읽기 전용</span>
              )}
              <button
                type="button"
                className="approval-project-change-btn"
                onClick={() => setIsApprovalProjectModalOpen(true)}
              >
                프로젝트 변경
              </button>
            </div>
          </section>
        </div>

        {approvalError && (
          <div className="alert alert-warning" style={{ marginBottom: "12px" }}>
            {approvalError.message || "승인 작업함 조회에 실패했습니다."}
          </div>
        )}

        <div className="kpi-container">
          {[
            { key: "APPROVED", label: "승인 완료", count: kpi.approved },
            { key: "PENDING", label: "승인 대기", count: kpi.waiting },
            { key: "REJECTED", label: "반려", count: kpi.rejected },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => !isLoading && setStatusFilter(item.key === statusFilter ? "all" : item.key)}
              className={`kpi-card ${statusFilter === item.key ? "active" : ""} ${isLoading ? "disabled" : ""}`}
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
              handleMainCategoryChange={handleMainCategoryChange}
              setActiveSubCategory={setActiveSubCategory}
              handleBulkAction={handleBulkAction}
              fetchData={fetchData}
              setDataPage={setDataPage}
              handleAction={handleAction}
              toggleSelect={toggleSelect}
              toggleSelectAll={toggleSelectAll}
            />
          </div>
        )}

        {isRejectModalOpen && (
          <div className="modal-overlay">
            <div className="modal-window">
              <div className="modal-header">
                <h3>반려 사유 입력</h3>
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
                  placeholder="반려 사유를 입력해 주세요"
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
                      showDefaultAlert("알림", "반려 사유를 입력해 주세요.", "info");
                      return;
                    }
                    await handleAction(rejectTargetId, "REJECTED", rejectReason);
                    setIsRejectModalOpen(false);
                  }}
                >
                  반려 확정
                </button>
              </div>
            </div>
          </div>
        )}

        <ApprovalProjectSelectModal
          isOpen={isApprovalProjectModalOpen}
          projects={approvalProjects}
          selectedRunId={selectedApprovalProject?.runId ?? null}
          onSelectProject={handleSelectApprovalProject}
          onClose={() => setIsApprovalProjectModalOpen(false)}
        />
      </div>
    </div>
  );
};

export default ManagerData;
