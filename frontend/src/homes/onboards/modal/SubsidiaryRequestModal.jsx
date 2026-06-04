import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  createRollupBatch,
  fetchRollupSubsidiaries,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

/**
 * SubsidiaryRequestModal
 *
 * G0 데이터 요청 자회사 선택 modal.
 * DTO: res.data.items -> { companyId, companyCode, companyName }
 */
const SubsidiaryRequestModal = ({ isOpen, onClose, runId, onRequested }) => {
  const dispatch = useDispatch();
  const subsidiaries = useSelector((state) => state.report.rollup.subsidiaries);
  const loading = useSelector((state) => state.report.loading.subsidiaries);
  const [selectedIds, setSelectedIds] = useState([]);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadSubsidiaries();
    } else {
      setSelectedIds([]);
      setError(null);
    }
  }, [isOpen]);

  const loadSubsidiaries = async () => {
    setError(null);
    try {
      const res = await dispatch(fetchRollupSubsidiaries({ runId })).unwrap();
      const items = Array.isArray(res?.data?.items)
        ? res.data.items
        : Array.isArray(res?.data)
          ? res.data
          : [];
      setSelectedIds(items.map((item) => item.companyId));
    } catch (err) {
      console.error(err);
      setError(err?.message || "자회사 목록 조회에 실패했습니다.");
    }
  };

  const handleToggle = (companyId) => {
    setSelectedIds((prev) =>
      prev.includes(companyId)
        ? prev.filter((id) => id !== companyId)
        : [...prev, companyId]
    );
  };

  const handleRequest = async () => {
    if (selectedIds.length === 0) return;

    setRequesting(true);
    try {
      const res = await dispatch(createRollupBatch({
        runId,
        sourceCompanyIds: selectedIds,
      })).unwrap();

      showDefaultAlert("완료", "자회사 데이터 요청이 완료되었습니다.", "success");
      onRequested?.(res.data || res);
      onClose();
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "요청에 실패했습니다.", "error");
    } finally {
      setRequesting(false);
    }
  };
  if (!isOpen) return null;

  return createPortal(
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 480 }}>
        <div className="ob1-modal-header">
          <h2>G0 데이터 요청 자회사 선택</h2>
          <button className="ob1-btn-close" onClick={onClose}>×</button>
        </div>
        <div className="ob1-modal-body">
          <p style={{ marginBottom: 16, fontSize: "0.9rem", color: "#475569" }}>
            데이터를 수집할 자회사를 선택해 주세요.
          </p>

          {/* loading */}
          {loading && (
            <div className="ob1-table-loading" style={{ padding: "24px" }}>
              <div className="ob1-spinner" />
              <p>자회사 목록을 불러오는 중...</p>
            </div>
          )}

          {/* error */}
          {!loading && error && (
            <div className="ob1-inline-error" style={{ margin: "16px 0" }}>
              <span className="ob1-error-icon">!</span>
              <span>{error}</span>
              <button type="button" className="ob1-btn-retry" onClick={loadSubsidiaries}>
                다시 시도
              </button>
            </div>
          )}

          {/* empty */}
          {!loading && !error && subsidiaries.length === 0 && (
            <div style={{ padding: "24px", textAlign: "center", color: "#64748b" }}>
              등록된 자회사가 없습니다.
            </div>
          )}

          {/* list */}
          {!loading && !error && subsidiaries.length > 0 && (
            <ul
              className="sub-list"
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              {subsidiaries.map((sub) => (
                <li
                  key={sub.companyId}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px",
                    border: "1px solid #e2e8f0",
                    borderRadius: "6px",
                  }}
                >
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      cursor: "pointer",
                      flex: 1,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(sub.companyId)}
                      onChange={() => handleToggle(sub.companyId)}
                    />
                    <span style={{ fontWeight: 500 }}>
                      {sub.companyName}
                    </span>
                    {sub.companyCode && (
                      <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                        ({sub.companyCode})
                      </span>
                    )}
                  </label>
                  <div style={{ textAlign: "right", fontSize: "0.8rem" }}>
                    <span style={{ color: "#2563eb" }}>
                      요청 대상
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div
          className="ob1-modal-footer"
          style={{
            borderTop: "1px solid #e2e8f0",
            padding: "16px",
            display: "flex",
            justifyContent: "flex-end",
            gap: "8px",
          }}
        >
          <button
            style={{
              padding: "8px 16px",
              border: "1px solid #cbd5e1",
              background: "#fff",
              borderRadius: "4px",
              cursor: "pointer",
            }}
            onClick={onClose}
          >
            취소
          </button>
          <button
            style={{
              padding: "8px 16px",
              background: "#1d4ed8",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: selectedIds.length ? "pointer" : "not-allowed",
              opacity: selectedIds.length ? 1 : 0.5,
            }}
            onClick={handleRequest}
            disabled={!selectedIds.length || requesting}
          >
            {requesting ? "요청 중..." : "요청 보내기"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default SubsidiaryRequestModal;


