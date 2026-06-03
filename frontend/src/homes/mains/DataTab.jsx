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

const normalizeIssueGroup = (item = {}) => {
  const value = item.issueGroup ?? item.issue_group ?? item.groupName;
  return value ? String(value).trim() : "";
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

  const availableIssueGroups = useMemo(() => {
    if (activeDataCategory === "all") return [];
    return [
      ...new Set(
        displayInputs
          .filter((item) => normalizeIssueDomain(item) === activeDataCategory)
          .map((item) => normalizeIssueGroup(item))
          .filter(Boolean)
      ),
    ];
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
      !availableIssueGroups.includes(activeSubCategory)
    ) {
      setActiveSubCategory("all");
    }
  }, [activeSubCategory, availableIssueGroups, setActiveSubCategory]);

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
        normalizeIssueGroup(item) !== activeSubCategory
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
    !isConsultant &&
    selectedSupportedRows.length > 0 &&
    selectedSupportedRows.every(
      (item) => !effectiveHasConsultant || normalizeReviewStatus(item) === "REVIEWED"
    );

  const handleBulkReview = () => {
    if (!selectedSupportedRows.length) return;
    handleBulkAction("REVIEWED");
  };

  const handleBulkApprove = () => {
    if (!canBulkApprove) return;
    handleBulkAction("APPROVED");
  };

  const handleBulkReject = () => {
    if (!selectedSupportedRows.length) return;
    setBulkRejectReason("");
    setIsBulkRejectModalOpen(true);
  };

  const handleOpenApprovalDetail = (item) => {
    setSelectedItemForDetail(item);
    setIsDetailModalOpen(true);
  };

  const handleToggleSelectAll = () => {
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
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]
    );
  };

  const runAction = (item, status, commentText = "") => {
    if (!isActionSupported(item, readOnlyYn)) return;
    handleAction(item.id, status, commentText);
  };

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
                        label: "Mark reviewed",
                        onClick: handleBulkReview,
                        className: "submit",
                        disabled: !selectedSupportedRows.length,
                      },
                    ]
                  : [
                      {
                        label: "Approve selected",
                        onClick: handleBulkApprove,
                        className: "submit",
                        disabled: !canBulkApprove,
                      },
                    ]),
                {
                  label: "Reject selected",
                  onClick: handleBulkReject,
                  className: "reject",
                  disabled: !selectedSupportedRows.length,
                },
              ]}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button className="btn-primary" onClick={fetchData} disabled={isLoading}>
              {isLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>

        <div className="ob-table-main-container" style={{ marginTop: "30px" }}>
          {activeDataCategory !== "all" && availableIssueGroups.length > 0 && (
            <div style={{ marginBottom: "-1px", position: "relative", zIndex: 2 }}>
              <TabButton.Sub
                tabs={[
                  { label: "All groups", value: "all" },
                  ...availableIssueGroups.map((group) => ({
                    label: group,
                    value: group,
                  })),
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
                        onChange={handleToggleSelectAll}
                      />
                    </th>
                    <th style={{ width: "100px" }}>Metric ID</th>
                    <th>Metric</th>
                    <th style={{ width: "110px" }}>Assignee</th>
                    <th style={{ width: "80px" }}>Done</th>
                    <th style={{ width: "80px" }}>Missing</th>
                    <th style={{ width: "100px" }}>Submit</th>
                    <th style={{ width: "100px" }}>Review</th>
                    <th style={{ width: "100px" }}>Approval</th>
                    <th style={{ width: "120px" }}>Submitted</th>
                    <th style={{ width: "190px" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleInputs.length === 0 ? (
                    <tr>
                      <td
                        colSpan="11"
                        style={{
                          padding: "80px 0",
                          color: "#94a3b8",
                          textAlign: "center",
                          background: "#fff",
                        }}
                      >
                        No approval items match the current filters.
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
                              onChange={() => toggleSelect(item.id)}
                            />
                          </td>
                          <td style={{ fontSize: "13px", fontWeight: 600, color: "#475569" }}>
                            {item.metricId || item.id}
                          </td>
                          <td className="st-left">{item.metricName || item.checklistQuestion || "-"}</td>
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
                              >
                                Detail
                              </button>
                              {isConsultant ? (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => runAction(item, "REVIEWED")}
                                    disabled={!supported}
                                    title={unsupportedTitle}
                                  >
                                    Review
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => runAction(item, "REJECTED")}
                                    disabled={!supported}
                                    title={unsupportedTitle}
                                  >
                                    Reject
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => runAction(item, "APPROVED")}
                                    disabled={!canApprove}
                                    title={
                                      !supported
                                        ? unsupportedTitle
                                        : !canApprove
                                          ? "Consultant review must be completed first."
                                          : ""
                                    }
                                    style={!canApprove ? { opacity: 0.5, cursor: "not-allowed" } : {}}
                                  >
                                    Approve
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => runAction(item, "REJECTED")}
                                    disabled={!supported}
                                    title={unsupportedTitle}
                                  >
                                    Reject
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
        onClose={() => setIsDetailModalOpen(false)}
        metricItem={selectedItemForDetail}
        viewerRole={effectiveViewerRole}
        hasConsultant={effectiveHasConsultant}
        onReview={({ commentText }) => {
          if (isActionSupported(selectedItemForDetail, readOnlyYn)) {
            runAction(selectedItemForDetail, "REVIEWED", commentText);
          }
          setIsDetailModalOpen(false);
        }}
        onApprove={({ commentText }) => {
          if (isActionSupported(selectedItemForDetail, readOnlyYn)) {
            runAction(selectedItemForDetail, "APPROVED", commentText);
          }
          setIsDetailModalOpen(false);
        }}
        onReject={({ commentText }) => {
          if (!commentText?.trim()) return;
          if (isActionSupported(selectedItemForDetail, readOnlyYn)) {
            runAction(selectedItemForDetail, "REJECTED", commentText);
          }
          setIsDetailModalOpen(false);
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
                onClick={() => {
                  handleBulkAction("REJECTED", bulkRejectReason.trim());
                  setIsBulkRejectModalOpen(false);
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
