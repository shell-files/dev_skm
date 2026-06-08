import React, { useEffect, useMemo, useState } from "react";
import TabButton from "@components/UI/TabButton";
import BatchActionBar from "@components/UI/BatchActionBar";
import UiPreviewPanel from "@/dev/step12UiPreview/UiPreviewPanel";
import ApprovalDetailModal from "./modal/ApprovalDetailModal";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import {
  APPROVAL_SCENARIOS,
  mergeApprovalFixtureRows,
  ONBOARDING_SCENARIOS,
  ROLLUP_SCENARIOS,
} from "@/dev/step12UiPreview/fixtures";
import "@styles/Manager.css";
import "@styles/TabButton.css";

const PAGE_SIZE = 10;
const DOMAIN_ORDER = ["general", "environmental", "social", "governance"];
const DOMAIN_LABEL = {
  general: "General",
  environmental: "E",
  social: "S",
  governance: "G",
};

const safeArray = (value) => (Array.isArray(value) ? value : []);

const normalizeIssueDomain = (item = {}) =>
  String(item.issueDomain ?? item.issue_domain ?? item.domain ?? "general").trim();

const normalizeSubIssueCode = (item = {}) => {
  const value =
    item.subIssueCode ??
    item.sub_issue_code ??
    item.sourceSubIssueCode ??
    item.source_sub_issue_code;
  return value ? String(value).trim() : "";
};

const normalizeSubIssueName = (item = {}) => {
  const value =
    item.subIssueName ??
    item.sub_issue_name ??
    item.displaySubIssueName;
  return value ? String(value).trim() : normalizeSubIssueCode(item);
};

const normalizeApprovalStatus = (item = {}) =>
  String(item.approvalStatus ?? item.status ?? "NOT_STARTED")
    .trim()
    .toUpperCase();

const normalizeSubmitStatus = (item = {}) => {
  if (item.submitStatus) return String(item.submitStatus).toUpperCase();
  const status = normalizeApprovalStatus(item);
  return ["SUBMITTED", "REVIEWED", "APPROVED", "REJECTED"].includes(status)
    ? "SUBMITTED"
    : "DRAFT";
};

const normalizeReviewStatus = (item = {}) => {
  if (item.reviewStatus) return String(item.reviewStatus).toUpperCase();
  const status = normalizeApprovalStatus(item);
  return ["APPROVED", "REJECTED"].includes(status) ? "REVIEWED" : "PENDING";
};

const isActionSupported = (item = {}, readOnlyYn = false) =>
  !readOnlyYn && (STEP12_UI_FIXTURE_ENABLED || item.actionSupportedYn !== false);

const actionDisabledTitle = (item = {}, readOnlyYn = false) =>
  readOnlyYn
    ? "Completed projects are read-only."
    : item.actionDisabledReason ||
      "This item does not support approval actions in the current step.";

const submitLabel = (status) => (status === "SUBMITTED" ? "Submitted" : "Draft");
const reviewLabel = (status) => (status === "REVIEWED" ? "Reviewed" : "Pending");
const approvalLabel = (status) => {
  if (status === "APPROVED") return "Approved";
  if (status === "REJECTED") return "Rejected";
  return "Pending";
};

const DataTab = ({
  activeService,
  isLoading,
  activeDataCategory,
  activeSubCategory,
  selectedIds,
  setSelectedIds,
  pagedInputs,
  dataPage,
  userRole,
  hasConsultant,
  statusFilter = "all",
  readOnlyYn = false,
  handleMainCategoryChange,
  setActiveSubCategory,
  handleBulkAction,
  fetchData,
  setDataPage,
  handleAction,
  actionLoading = false,
  approvalDetail = null,
  approvalDetailLoading = false,
  approvalDetailError = null,
  fetchApprovalDetail,
}) => {
  const [previewRole, setPreviewRole] = useState("ESG_MANAGER");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(
    ONBOARDING_SCENARIOS.UNASSIGNED
  );
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(
    APPROVAL_SCENARIOS.NO_CONSULTANT
  );
  const [previewRollupScenario, setPreviewRollupScenario] = useState(
    ROLLUP_SCENARIOS.PARENT_PENDING
  );
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedItemForDetail, setSelectedItemForDetail] = useState(null);
  const [isBulkRejectModalOpen, setIsBulkRejectModalOpen] = useState(false);
  const [bulkRejectReason, setBulkRejectReason] = useState("");
  const [modalActionMode, setModalActionMode] = useState(null);

  const sourceInputs = useMemo(() => safeArray(pagedInputs), [pagedInputs]);

  const displayInputs = useMemo(() => {
    if (!STEP12_UI_FIXTURE_ENABLED) return sourceInputs;
    return mergeApprovalFixtureRows(sourceInputs, previewApprovalScenario);
  }, [sourceInputs, previewApprovalScenario]);

  const availableDomains = useMemo(
    () =>
      DOMAIN_ORDER.filter((domain) =>
        displayInputs.some((item) => normalizeIssueDomain(item) === domain)
      ),
    [displayInputs]
  );

  const availableSubIssues = useMemo(() => {
    if (activeDataCategory === "all") return [];
    const subIssueMap = new Map();
    displayInputs
      .filter((item) => normalizeIssueDomain(item) === activeDataCategory)
      .forEach((item) => {
        const code = normalizeSubIssueCode(item);
        if (!code || subIssueMap.has(code)) return;
        subIssueMap.set(code, {
          value: code,
          label: normalizeSubIssueName(item),
        });
      });
    return [...subIssueMap.values()].sort((a, b) =>
      String(a.label || a.value).localeCompare(String(b.label || b.value))
    );
  }, [displayInputs, activeDataCategory]);

  useEffect(() => {
    if (
      activeDataCategory !== "all" &&
      !availableDomains.includes(activeDataCategory)
    ) {
      handleMainCategoryChange("all");
    }
  }, [activeDataCategory, availableDomains, handleMainCategoryChange]);

  useEffect(() => {
    if (
      activeSubCategory !== "all" &&
      !availableSubIssues.some((subIssue) => subIssue.value === activeSubCategory)
    ) {
      setActiveSubCategory("all");
    }
  }, [activeSubCategory, availableSubIssues, setActiveSubCategory]);

  const filteredInputs = useMemo(() => {
    return displayInputs.filter((item) => {
      const itemService = item.service || "disclosure";
      if (
        item.service &&
        activeService &&
        activeService !== "all" &&
        itemService !== activeService
      ) {
        return false;
      }
      if (
        activeDataCategory !== "all" &&
        normalizeIssueDomain(item) !== activeDataCategory
      ) {
        return false;
      }
      if (
        activeSubCategory !== "all" &&
        normalizeSubIssueCode(item) !== activeSubCategory
      ) {
        return false;
      }
      if (statusFilter !== "all") {
        const status = normalizeApprovalStatus(item);
        if (statusFilter === "PENDING") {
          return !["APPROVED", "REJECTED"].includes(status);
        }
        return status === String(statusFilter).toUpperCase();
      }
      return true;
    });
  }, [
    activeDataCategory,
    activeService,
    activeSubCategory,
    displayInputs,
    statusFilter,
  ]);

  const totalDataPages = Math.max(1, Math.ceil(filteredInputs.length / PAGE_SIZE));
  const visibleInputs = useMemo(
    () => filteredInputs.slice((dataPage - 1) * PAGE_SIZE, dataPage * PAGE_SIZE),
    [filteredInputs, dataPage]
  );

  useEffect(() => {
    if (dataPage > totalDataPages) {
      setDataPage(totalDataPages);
    }
  }, [dataPage, totalDataPages, setDataPage]);

  const effectiveViewerRole = STEP12_UI_FIXTURE_ENABLED
    ? previewRole
    : userRole ?? "guest";
  const isConsultant =
    String(effectiveViewerRole).toUpperCase().includes("CONSULTANT") ||
    String(effectiveViewerRole).includes("consultant");

  const effectiveHasConsultant = STEP12_UI_FIXTURE_ENABLED
    ? previewApprovalScenario !== APPROVAL_SCENARIOS.NO_CONSULTANT
    : hasConsultant;

  const selectedRows = useMemo(
    () => displayInputs.filter((item) => selectedIds.includes(item.id)),
    [displayInputs, selectedIds]
  );
  const selectedSupportedRows = selectedRows.filter((item) =>
    isActionSupported(item, readOnlyYn)
  );

  const canBulkApprove =
    !readOnlyYn &&
    !actionLoading &&
    !isConsultant &&
    selectedSupportedRows.length > 0 &&
    selectedSupportedRows.every(
      (item) => !effectiveHasConsultant || normalizeReviewStatus(item) === "REVIEWED"
    );

  const handleBulkReview = () => {
    if (actionLoading || !selectedSupportedRows.length) return;
    handleBulkAction("REVIEWED");
  };

  const handleBulkApprove = () => {
    if (actionLoading || !canBulkApprove) return;
    handleBulkAction("APPROVED");
  };

  const handleBulkReject = () => {
    if (actionLoading || !selectedSupportedRows.length) return;
    setBulkRejectReason("");
    setIsBulkRejectModalOpen(true);
  };

  const handleOpenApprovalDetail = async (item, actionMode = null) => {
    setSelectedItemForDetail(item);
    setModalActionMode(actionMode);
    setIsDetailModalOpen(true);
    try {
      await fetchApprovalDetail?.(item.metricId || item.id);
    } catch (error) {
      console.error(error);
    }
  };

  const handleToggleSelectAll = () => {
    if (readOnlyYn || actionLoading) return;

    const visibleIds = visibleInputs.map((item) => item.id);
    const allSelected =
      visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));
    setSelectedIds((prev) =>
      allSelected
        ? prev.filter((id) => !visibleIds.includes(id))
        : [...new Set([...prev, ...visibleIds])]
    );
  };

  const toggleSelect = (id) => {
    if (readOnlyYn || actionLoading) return;

    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]
    );
  };

  const runAction = async (item, status, commentText = "") => {
    if (!isActionSupported(item, readOnlyYn) || actionLoading) return false;
    return handleAction(item.id, status, commentText);
  };

  const closeDetailModal = () => {
    setIsDetailModalOpen(false);
    setModalActionMode(null);
  };

  const detailMetricItem =
    approvalDetail?.metricId === selectedItemForDetail?.metricId
      ? {
          ...selectedItemForDetail,
          ...approvalDetail,
        }
      : selectedItemForDetail;

  return (
    <section id="datatap_page" className="fade-in">
      <div className="ob-body" style={{ padding: 0 }}>
        <div
          className="data-control-row"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "15px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "20px", flex: 1 }}>
            <TabButton.Category
              tabs={[
                { label: "All", value: "all" },
                ...availableDomains.map((domain) => ({
                  label: DOMAIN_LABEL[domain] || domain,
                  value: domain,
                })),
              ]}
              activeTab={activeDataCategory}
              onTabChange={(value) => handleMainCategoryChange(value)}
              className="data-category-tabs"
            />

            <BatchActionBar
              selectedCount={selectedIds.length}
              actions={[
                ...(isConsultant
                  ? [
                      {
                        label: "검토 완료 상태로 변경",
                        onClick: handleBulkReview,
                        className: "submit",
                        disabled: actionLoading || !selectedSupportedRows.length,
                      },
                    ]
                  : [
                      {
                        label: "선택 항목 최종 승인",
                        onClick: handleBulkApprove,
                        className: "submit",
                        disabled: actionLoading || !canBulkApprove,
                      },
                    ]),
                {
                  label: "선택 항목 반려",
                  onClick: handleBulkReject,
                  className: "reject",
                  disabled: actionLoading || !selectedSupportedRows.length,
                },
              ]}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button className="btn-primary" onClick={fetchData} disabled={isLoading || actionLoading}>
              {isLoading || actionLoading ? "Loading..." : "데이터 새로고침"}
            </button>
          </div>
        </div>

        <div className="ob-table-main-container" style={{ marginTop: "30px" }}>
          {activeDataCategory !== "all" && availableSubIssues.length > 0 && (
            <div style={{ marginBottom: "-1px", position: "relative", zIndex: 2 }}>
              <TabButton.Sub
                tabs={[
                  { label: "All Sub-Issues", value: "all" },
                  ...availableSubIssues,
                ]}
                activeTab={activeSubCategory}
                onTabChange={(value) => setActiveSubCategory(value)}
                categoryTheme={DOMAIN_LABEL[activeDataCategory] || "General"}
                className="data-sub-tabs"
              />
            </div>
          )}

          {isLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p>Loading approval inbox...</p>
            </div>
          ) : (
            <div
              className="ob-table-wrap"
              style={{ borderTopLeftRadius: activeDataCategory === "all" ? "12px" : "0" }}
            >
              <table className="ob-table">
                <thead>
                  <tr>
                    <th style={{ width: "44px" }}>
                      <input
                        type="checkbox"
                        className="ob-checkbox"
                        aria-label="Select all"
                        checked={
                          visibleInputs.length > 0 &&
                          visibleInputs.every((item) => selectedIds.includes(item.id))
                        }
                        disabled={readOnlyYn || actionLoading}
                        onChange={handleToggleSelectAll}
                      />
                    </th>
                    <th style={{ width: "100px" }}>Metric ID</th>
                    <th>지표명</th>
                    <th style={{ width: "120px" }}>Sub-Issue</th>
                    <th style={{ width: "110px" }}>담당자</th>
                    <th style={{ width: "80px" }}>입력 완료</th>
                    <th style={{ width: "80px" }}>미입력</th>
                    <th style={{ width: "100px" }}>제출 상태</th>
                    <th style={{ width: "100px" }}>검토 상태</th>
                    <th style={{ width: "100px" }}>승인 상태</th>
                    <th style={{ width: "120px" }}>제출일</th>
                    <th style={{ width: "190px" }}>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleInputs.length === 0 ? (
                    <tr>
                      <td
                        colSpan="12"
                        style={{
                          padding: "80px 0",
                          color: "#94a3b8",
                          textAlign: "center",
                          background: "#fff",
                        }}
                      >
                        조건에 맞는 데이터가 없습니다.
                      </td>
                    </tr>
                  ) : (
                    visibleInputs.map((item) => {
                      const reviewStatus = normalizeReviewStatus(item);
                      const approvalStatus = normalizeApprovalStatus(item);
                      const submitStatus = normalizeSubmitStatus(item);
                      const supported = isActionSupported(item, readOnlyYn);
                      const unsupportedTitle = supported
                        ? ""
                        : actionDisabledTitle(item, readOnlyYn);
                      const canApprove =
                        supported &&
                        !isConsultant &&
                        (!effectiveHasConsultant || reviewStatus === "REVIEWED");

                      return (
                        <tr key={item.id} className={selectedIds.includes(item.id) ? "selected" : ""}>
                          <td>
                            <input
                              type="checkbox"
                              className="ob-checkbox"
                              aria-label={`Select ${item.metricId || item.id}`}
                              checked={selectedIds.includes(item.id)}
                              disabled={readOnlyYn}
                              onChange={() => toggleSelect(item.id)}
                            />
                          </td>
                          <td style={{ fontSize: "13px", fontWeight: 600, color: "#475569" }}>
                            {item.metricId || item.id}
                          </td>
                          <td className="st-left">{item.metricName || item.checklistQuestion || "-"}</td>
                          <td style={{ fontSize: "12px", color: "#64748b" }}>{normalizeSubIssueName(item) || "-"}</td>
                          <td>{item.assigneeName || item.userName || "-"}</td>
                          <td className="ob-completion-cell">{item.inputCompletedCount || 0}</td>
                          <td className="ob-completion-cell">{item.inputMissingCount || 0}</td>
                          <td className="cell-status">
                            <span className={`ob-status ${submitStatus === "SUBMITTED" ? "st-submitted" : "st-draft"}`}>
                              {submitLabel(submitStatus)}
                            </span>
                          </td>
                          <td className="cell-status">
                            <span className={`ob-status ${reviewStatus === "REVIEWED" ? "st-approved" : "st-draft"}`}>
                              {reviewLabel(reviewStatus)}
                            </span>
                          </td>
                          <td className="cell-status">
                            <span
                              className={`ob-status ${
                                approvalStatus === "APPROVED"
                                  ? "st-approved"
                                  : approvalStatus === "REJECTED"
                                    ? "st-rejected"
                                    : "st-draft"
                              }`}
                            >
                              {approvalLabel(approvalStatus)}
                            </span>
                          </td>
                          <td>{item.submittedAt || "-"}</td>
                          <td>
                            <div className="ob-actions">
                              <button
                                className="ob-act-btn ob-act-draft ob-detail-btn"
                                onClick={() => handleOpenApprovalDetail(item)}
                                disabled={actionLoading}
                              >
                                상세 확인
                              </button>
                              {isConsultant ? (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => runAction(item, "REVIEWED")}
                                    disabled={actionLoading || !supported}
                                    title={unsupportedTitle}
                                  >
                                    검토 완료
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => runAction(item, "REJECTED")}
                                    disabled={actionLoading || !supported}
                                    title={unsupportedTitle}
                                  >
                                    반려
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => handleOpenApprovalDetail(item, "approve")}
                                    disabled={actionLoading || !canApprove}
                                    title={
                                      !supported
                                        ? unsupportedTitle
                                        : !canApprove
                                          ? "Consultant review must be completed first."
                                          : ""
                                    }
                                    style={!canApprove ? { opacity: 0.5, cursor: "not-allowed" } : {}}
                                  >
                                    최종 승인
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => runAction(item, "REJECTED")}
                                    disabled={actionLoading || !supported}
                                    title={unsupportedTitle}
                                  >
                                    반려
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {!isLoading && totalDataPages > 1 && (
          <div className="pagination">
            {Array.from({ length: totalDataPages }).map((_, index) => (
              <button
                key={index}
                onClick={() => setDataPage(index + 1)}
                className={`page-btn ${dataPage === index + 1 ? "active" : ""}`}
                style={
                  dataPage === index + 1
                    ? { backgroundColor: "#03a94d", color: "#fff", border: "none" }
                    : {}
                }
              >
                {index + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      <ApprovalDetailModal
        isOpen={isDetailModalOpen}
        onClose={closeDetailModal}
        metricItem={detailMetricItem}
        viewerRole={effectiveViewerRole}
        hasConsultant={effectiveHasConsultant}
        readOnlyYn={readOnlyYn}
        modalActionMode={modalActionMode}
        loading={approvalDetailLoading}
        error={approvalDetailError}
        actionLoading={actionLoading}
        onReview={async ({ commentText }) => {
          const success = await runAction(selectedItemForDetail, "REVIEWED", commentText);
          if (success) {
            closeDetailModal();
          }
        }}
        onApprove={async ({ commentText }) => {
          const success = await runAction(selectedItemForDetail, "APPROVED", commentText);
          if (success) {
            closeDetailModal();
          }
        }}
        onReject={async ({ commentText }) => {
          if (!commentText?.trim()) return;
          const success = await runAction(selectedItemForDetail, "REJECTED", commentText);
          if (success) {
            closeDetailModal();
          }
        }}
      />

      {isBulkRejectModalOpen && (
        <div className="modal-overlay">
          <div className="modal-window">
            <div className="modal-header">
              <h3>Reject selected items</h3>
              <button
                type="button"
                className="close-x"
                aria-label="Close bulk reject modal"
                onClick={() => setIsBulkRejectModalOpen(false)}
              >
                x
              </button>
            </div>
            <div className="modal-body">
              <p>Reject {selectedSupportedRows.length} selected items.</p>
              <textarea
                className="reject-textarea"
                placeholder="Enter rejection reason."
                value={bulkRejectReason}
                onChange={(event) => setBulkRejectReason(event.target.value)}
                style={{
                  width: "100%",
                  height: "120px",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "6px",
                  marginTop: "10px",
                }}
              />
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-confirm"
                disabled={!bulkRejectReason.trim()}
                title={!bulkRejectReason.trim() ? "Enter rejection reason." : ""}
                onClick={async () => {
                  const success = await handleBulkAction("REJECTED", bulkRejectReason.trim());
                  if (success) {
                    setIsBulkRejectModalOpen(false);
                  }
                }}
              >
                Confirm reject
              </button>
            </div>
          </div>
        </div>
      )}

      <UiPreviewPanel
        role={previewRole}
        onboardingScenario={previewOnboardingScenario}
        approvalScenario={previewApprovalScenario}
        rollupScenario={previewRollupScenario}
        onRoleChange={setPreviewRole}
        onOnboardingScenarioChange={setPreviewOnboardingScenario}
        onApprovalScenarioChange={setPreviewApprovalScenario}
        onRollupScenarioChange={setPreviewRollupScenario}
      />
    </section>
  );
};

export default DataTab;
