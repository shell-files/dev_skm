import React, { useEffect, useMemo, useState } from "react";
import TabButton from "@components/UI/TabButton";
import BatchActionBar from "@components/UI/BatchActionBar";
import UiPreviewPanel from "@/dev/step12UiPreview/UiPreviewPanel";
import ApprovalDetailModal from "./modal/ApprovalDetailModal";
import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import {
  mergeApprovalFixtureRows,
  ONBOARDING_SCENARIOS,
  APPROVAL_SCENARIOS,
  ROLLUP_SCENARIOS,
} from "@/dev/step12UiPreview/fixtures";
import "@styles/Manager.css";
import "@styles/TabButton.css";

const PAGE_SIZE = 10;

const DOMAIN_ORDER = ["general", "environmental", "social", "governance"];

const DOMAIN_LABEL = {
  general: "경영일반",
  environmental: "E",
  social: "S",
  governance: "G",
};

const normalizeIssueDomain = (item = {}) => {
  const value =
    item.issueDomain ??
    item.issue_domain ??
    item.domain ??
    "general";
  return String(value || "general").trim();
};

const normalizeIssueGroup = (item = {}) => {
  const value = item.issueGroup ?? item.issue_group ?? item.groupName;
  return value ? String(value).trim() : "";
};

const normalizeApprovalStatus = (item = {}) =>
  String(item.approvalStatus ?? item.status ?? "NOT_STARTED").trim().toUpperCase();

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

const actionSupported = (item = {}) => item.actionSupportedYn !== false;

const actionDisabledTitle = (item = {}) =>
  item.actionDisabledReason || "현재 항목은 이 단계에서 승인 action을 지원하지 않습니다.";

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
  handleMainCategoryChange,
  setActiveSubCategory,
  toggleSelect,
  handleBulkAction,
  fetchData,
  setDataPage,
  handleAction,
}) => {
  const [previewRole, setPreviewRole] = useState("ESG담당자");
  const [previewOnboardingScenario, setPreviewOnboardingScenario] = useState(ONBOARDING_SCENARIOS.UNASSIGNED);
  const [previewApprovalScenario, setPreviewApprovalScenario] = useState(APPROVAL_SCENARIOS.NO_CONSULTANT);
  const [previewRollupScenario, setPreviewRollupScenario] = useState(ROLLUP_SCENARIOS.PARENT_PENDING);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedItemForDetail, setSelectedItemForDetail] = useState(null);
  const [isBulkRejectModalOpen, setIsBulkRejectModalOpen] = useState(false);
  const [bulkRejectReason, setBulkRejectReason] = useState("");

  const sourceInputs = useMemo(
    () => (Array.isArray(pagedInputs) ? pagedInputs : []),
    [pagedInputs]
  );

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
      if (item.service && activeService && activeService !== "all" && itemService !== activeService) {
        return false;
      }
      if (activeDataCategory !== "all" && normalizeIssueDomain(item) !== activeDataCategory) {
        return false;
      }
      if (activeSubCategory !== "all" && normalizeIssueGroup(item) !== activeSubCategory) {
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
  }, [displayInputs, activeService, activeDataCategory, activeSubCategory, statusFilter]);

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

  const effectiveViewerRole = STEP12_UI_FIXTURE_ENABLED ? previewRole : (userRole ?? "guest");
  const isConsultant =
    effectiveViewerRole.includes("CONSULTANT") ||
    effectiveViewerRole.includes("컨설턴트");

  const effectiveHasConsultant =
    STEP12_UI_FIXTURE_ENABLED
      ? previewApprovalScenario !== APPROVAL_SCENARIOS.NO_CONSULTANT
      : hasConsultant;

  const selectedRows = useMemo(
    () => displayInputs.filter((item) => selectedIds.includes(item.id)),
    [displayInputs, selectedIds]
  );
  const selectedSupportedRows = selectedRows.filter(actionSupported);

  const canBulkApprove =
    !isConsultant &&
    selectedSupportedRows.length > 0 &&
    selectedSupportedRows.every((item) => !effectiveHasConsultant || normalizeReviewStatus(item) === "REVIEWED");

  const handleBulkReview = () => {
    if (!selectedSupportedRows.length) return;
    handleBulkAction("reviewed");
  };

  const handleBulkApprove = () => {
    if (!canBulkApprove) return;
    handleBulkAction("approved");
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
    const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));
    setSelectedIds((prev) =>
      allSelected
        ? prev.filter((id) => !visibleIds.includes(id))
        : [...new Set([...prev, ...visibleIds])]
    );
  };

  const runAction = (item, status, commentText = "") => {
    if (!actionSupported(item)) return;
    handleAction(item.id, status, commentText);
  };

  return (
    <section id="datatap_page" className="fade-in">
      <div className="ob-body" style={{ padding: 0 }}>
        <div
          className="data-control-row"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "20px", flex: 1 }}>
            <TabButton.Category
              tabs={[
                { label: "전체", value: "all" },
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
                  ? [{ label: "선택 검토 완료", onClick: handleBulkReview, className: "submit", disabled: !selectedSupportedRows.length }]
                  : [{ label: "선택 최종 승인", onClick: handleBulkApprove, className: "submit", disabled: !canBulkApprove }]),
                { label: "선택 반려", onClick: handleBulkReject, className: "reject", disabled: !selectedSupportedRows.length },
              ]}
            />
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button className="btn-primary" onClick={fetchData} disabled={isLoading}>
              {isLoading ? "로딩 중..." : "데이터 새로고침"}
            </button>
          </div>
        </div>

        <div className="ob-table-main-container" style={{ marginTop: "30px" }}>
          {activeDataCategory !== "all" && availableIssueGroups.length > 0 && (
            <div style={{ marginBottom: "-1px", position: "relative", zIndex: 2 }}>
              <TabButton.Sub
                tabs={[
                  { label: "전체 그룹", value: "all" },
                  ...availableIssueGroups.map((group) => ({ label: group, value: group })),
                ]}
                activeTab={activeSubCategory}
                onTabChange={(value) => setActiveSubCategory(value)}
                categoryTheme={DOMAIN_LABEL[activeDataCategory] || "경영일반"}
                className="data-sub-tabs"
              />
            </div>
          )}

          {isLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <p>데이터를 처리하고 있습니다...</p>
            </div>
          ) : (
            <div className="ob-table-wrap" style={{ borderTopLeftRadius: activeDataCategory === "all" ? "12px" : "0" }}>
              <table className="ob-table">
                <thead>
                  <tr>
                    <th style={{ width: "44px" }}>
                      <input
                        type="checkbox"
                        className="ob-checkbox"
                        aria-label="전체 선택"
                        checked={visibleInputs.length > 0 && visibleInputs.every((item) => selectedIds.includes(item.id))}
                        onChange={handleToggleSelectAll}
                      />
                    </th>
                    <th style={{ width: "100px" }}>Metric ID</th>
                    <th>지표명</th>
                    <th style={{ width: "100px" }}>담당자</th>
                    <th style={{ width: "80px" }}>입력 완료</th>
                    <th style={{ width: "60px" }}>미입력</th>
                    <th style={{ width: "90px" }}>제출 상태</th>
                    <th style={{ width: "90px" }}>검토 상태</th>
                    <th style={{ width: "90px" }}>승인 상태</th>
                    <th style={{ width: "110px" }}>제출일</th>
                    <th style={{ width: "180px" }}>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleInputs.length === 0 ? (
                    <tr>
                      <td colSpan="11" style={{ padding: "80px 0", color: "#94a3b8", textAlign: "center", background: "#fff" }}>
                        <div style={{ marginBottom: "8px", fontSize: "24px" }}>-</div>
                        해당 조건에 맞는 데이터가 없습니다.
                      </td>
                    </tr>
                  ) : (
                    visibleInputs.map((item) => {
                      const reviewStatus = normalizeReviewStatus(item);
                      const approvalStatus = normalizeApprovalStatus(item);
                      const submitStatus = normalizeSubmitStatus(item);
                      const supported = actionSupported(item);
                      const unsupportedTitle = supported ? "" : actionDisabledTitle(item);
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
                              aria-label={`${item.metricId || item.id} 선택`}
                              checked={selectedIds.includes(item.id)}
                              onChange={() => toggleSelect(item.id)}
                            />
                          </td>
                          <td style={{ fontSize: "13px", fontWeight: "600", color: "#475569" }}>
                            {item.metricId || item.id}
                          </td>
                          <td className="st-left">{item.metricName || item.checklistQuestion || "-"}</td>
                          <td>{item.assigneeName || item.userName || "-"}</td>
                          <td className="ob-completion-cell">{item.inputCompletedCount || 0}</td>
                          <td className="ob-completion-cell">{item.inputMissingCount || 0}</td>
                          <td className="cell-status">
                            <span className={`ob-status ${submitStatus === "SUBMITTED" ? "st-submitted" : "st-draft"}`}>
                              {submitStatus === "SUBMITTED" ? "제출완료" : "미제출"}
                            </span>
                          </td>
                          <td className="cell-status">
                            <span className={`ob-status ${reviewStatus === "REVIEWED" ? "st-approved" : "st-draft"}`}>
                              {reviewStatus === "REVIEWED" ? "검토완료" : "검토대기"}
                            </span>
                          </td>
                          <td className="cell-status">
                            <span className={`ob-status ${approvalStatus === "APPROVED" ? "st-approved" : approvalStatus === "REJECTED" ? "st-rejected" : "st-draft"}`}>
                              {approvalStatus === "APPROVED" ? "승인완료" : approvalStatus === "REJECTED" ? "반려" : "미승인"}
                            </span>
                          </td>
                          <td>{item.submittedAt || "-"}</td>
                          <td>
                            <div className="ob-actions">
                              <button className="ob-act-btn ob-act-draft ob-detail-btn" onClick={() => handleOpenApprovalDetail(item)}>
                                상세 보기
                              </button>
                              {isConsultant ? (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => runAction(item, "REVIEWED")}
                                    disabled={!supported}
                                    title={unsupportedTitle}
                                  >
                                    검토 완료
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => handleOpenApprovalDetail(item)}
                                    disabled={!supported}
                                    title={unsupportedTitle}
                                  >
                                    반려
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    className="ob-act-btn ob-act-submit"
                                    onClick={() => runAction(item, "APPROVED")}
                                    disabled={!canApprove}
                                    title={!supported ? unsupportedTitle : !canApprove ? "컨설턴트 검토가 완료되어야 승인할 수 있습니다." : ""}
                                    style={!canApprove ? { opacity: 0.5, cursor: "not-allowed" } : {}}
                                  >
                                    최종 승인
                                  </button>
                                  <button
                                    type="button"
                                    className="ob-act-btn ob-act-reject"
                                    onClick={() => handleOpenApprovalDetail(item)}
                                    disabled={!supported}
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
                style={dataPage === index + 1 ? { backgroundColor: "#03a94d", color: "#fff", border: "none" } : {}}
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
        onReview={({ metricId, commentText }) => {
          if (actionSupported(selectedItemForDetail)) runAction(selectedItemForDetail, "REVIEWED", commentText);
          setIsDetailModalOpen(false);
        }}
        onApprove={({ metricId, commentText }) => {
          if (actionSupported(selectedItemForDetail)) runAction(selectedItemForDetail, "APPROVED", commentText);
          setIsDetailModalOpen(false);
        }}
        onReject={({ metricId, commentText }) => {
          if (!commentText?.trim()) return;
          if (actionSupported(selectedItemForDetail)) runAction(selectedItemForDetail, "REJECTED", commentText);
          setIsDetailModalOpen(false);
        }}
      />

      {isBulkRejectModalOpen && (
        <div className="modal-overlay">
          <div className="modal-window">
            <div className="modal-header">
              <h3>선택 항목 반려</h3>
              <button
                type="button"
                className="close-x"
                aria-label="일괄 반려 모달 닫기"
                onClick={() => setIsBulkRejectModalOpen(false)}
              >
                x
              </button>
            </div>
            <div className="modal-body">
              <p>선택한 {selectedSupportedRows.length}개 지표를 반려합니다.</p>
              <textarea
                className="reject-textarea"
                placeholder="반려 사유를 입력해 주세요"
                value={bulkRejectReason}
                onChange={(event) => setBulkRejectReason(event.target.value)}
                style={{ width: "100%", height: "120px", padding: "10px", border: "1px solid #ddd", borderRadius: "6px", marginTop: "10px" }}
              />
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-confirm"
                disabled={!bulkRejectReason.trim()}
                title={!bulkRejectReason.trim() ? "반려 사유를 입력해 주세요" : ""}
                onClick={() => {
                  handleBulkAction("rejected", bulkRejectReason.trim());
                  setIsBulkRejectModalOpen(false);
                }}
              >
                반려 확정
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
