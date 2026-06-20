/**
 * DataTab.jsx
 * 레이어: Component (mains) — 구버전 파일
 * 역할: ManagerData 페이지의 승인 항목 테이블 탭 — 도메인·서브이슈 필터, 상태 필터, 행별·일괄 승인·검토·반려 액션, 승인 상세 모달 연동을 담당
 *
 * Props:
 *   activeService — 현재 활성 서비스 유형 (예: "disclosure")
 *   isLoading — 데이터 로딩 여부
 *   activeDataCategory — 현재 도메인 필터 ("all" / "environmental" 등)
 *   activeSubCategory — 현재 서브이슈 필터
 *   selectedIds — 일괄 처리 선택된 항목 ID 배열
 *   setSelectedIds — 선택 항목 상태 업데이트 함수
 *   pagedInputs — 현재 페이지에 표시할 승인 항목 배열
 *   dataPage — 현재 페이지 번호
 *   userRole — 현재 사용자 역할
 *   hasConsultant — 컨설턴트 검토 단계 포함 여부
 *   statusFilter — 승인 상태 필터 ("all" / "APPROVED" / "PENDING" / "REJECTED")
 *   readOnlyYn — 읽기 전용 여부
 *   handleMainCategoryChange — 도메인 카테고리 변경 핸들러
 *   setActiveSubCategory — 서브이슈 필터 업데이트 함수
 *   handleBulkAction — 일괄 승인·반려 핸들러
 *   fetchData — 데이터 새로고침 핸들러
 *   setDataPage — 페이지 번호 업데이트 함수
 *   handleAction — 단건 승인·반려 핸들러
 *   actionLoading — 승인 처리 로딩 여부
 *   approvalDetail — 선택된 항목의 상세 데이터
 *   approvalDetailLoading — 상세 로딩 여부
 *   approvalDetailError — 상세 조회 오류
 *   fetchApprovalDetail — 승인 상세 조회 함수
 *
 * 의존 컴포넌트:
 *   ApprovalDetailModal — 지표 승인 상세 조회·승인·반려 모달
 */
import React, { useEffect, useMemo, useState } from "react";
import TabButton from "@components/UI/TabButton";
import BatchActionBar from "@components/UI/BatchActionBar";
import ApprovalDetailModal from "./modal/ApprovalDetailModal";
import ModalWrapper from "@components/UI/ModalWrapper";
import LoadingSpinner from "@components/UI/LoadingSpinner";
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
  !readOnlyYn && item.actionSupportedYn !== false;

const actionDisabledTitle = (item = {}, readOnlyYn = false) =>
  readOnlyYn
    ? "Completed projects are read-only."
    : item.actionDisabledReason ||
      "This item does not support approval actions in the current step.";

const submitLabel = (status) => (status === "SUBMITTED" ? "제출 완료" : "작성 중");
const reviewLabel = (status) => (status === "REVIEWED" ? "검토 완료" : "대기");
const approvalLabel = (status) => {
  if (status === "APPROVED") return "승인";
  if (status === "REJECTED") return "반려";
  return "대기";
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
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedItemForDetail, setSelectedItemForDetail] = useState(null);
  const [isBulkRejectModalOpen, setIsBulkRejectModalOpen] = useState(false);
  const [bulkRejectReason, setBulkRejectReason] = useState("");
  const [modalActionMode, setModalActionMode] = useState(null);

  const sourceInputs = useMemo(() => safeArray(pagedInputs), [pagedInputs]);

  const displayInputs = sourceInputs;

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

  const effectiveViewerRole = userRole ?? "guest";
  const isConsultant =
    String(effectiveViewerRole).toUpperCase().includes("CONSULTANT") ||
    String(effectiveViewerRole).includes("consultant");

  const effectiveHasConsultant = hasConsultant;

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
            <LoadingSpinner message="Loading approval inbox..." />
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
                    <th style={{ width: "110px" }}>담당자</th>
                    <th style={{ width: "80px" }}>미입력</th>
                    <th style={{ width: "100px" }}>검토 상태</th>
                    <th style={{ width: "100px" }}>승인 상태</th>
                    <th style={{ width: "140px" }}>제출일</th>
                    <th style={{ width: "280px" }}>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleInputs.length === 0 ? (
                    <tr>
                      <td
                        colSpan="9"
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
                              disabled={readOnlyYn || actionLoading}
                              onChange={() => toggleSelect(item.id)}
                            />
                          </td>
                          <td style={{ fontSize: "13px", fontWeight: 600, color: "#475569" }}>
                            {item.metricId || item.id}
                          </td>
                          <td className="st-left">{item.metricName || item.checklistQuestion || "-"}</td>
                          <td>{item.assigneeName || item.userName || "-"}</td>
                          <td className="ob-completion-cell">{item.inputMissingCount || 0}</td>
                          <td className="cell-status">
                            <span className={`ob-status ${reviewStatus === "REVIEWED" ? "st-reviewed" : "st-pending"}`}>
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
                                    : "st-pending"
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
        <ModalWrapper
          title="Reject selected items"
          onClose={() => setIsBulkRejectModalOpen(false)}
          footer={
            <button
              type="button"
              className="btn-confirm"
              disabled={!bulkRejectReason.trim()}
              title={!bulkRejectReason.trim() ? "Enter rejection reason." : ""}
              onClick={async () => {
                const success = await handleBulkAction("REJECTED", bulkRejectReason.trim());
                if (success) setIsBulkRejectModalOpen(false);
              }}
            >
              Confirm reject
            </button>
          }
        >
          <p>Reject {selectedSupportedRows.length} selected items.</p>
          <textarea
            className="reject-textarea"
            placeholder="Enter rejection reason."
            value={bulkRejectReason}
            onChange={(event) => setBulkRejectReason(event.target.value)}
            style={{ width: "100%", height: "120px", padding: "10px", border: "1px solid #ddd", borderRadius: "6px", marginTop: "10px" }}
          />
        </ModalWrapper>
      )}

    </section>
  );
};

export default DataTab;
