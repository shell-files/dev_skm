import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  createRollupBatch,
  fetchRollupBatchSources,
  fetchRollupBatchStatus,
  fetchRollupScopePreview,
  fetchRollupSubsidiaries,
  setActiveBatchId,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const purposeLabel = (code) => {
  const value = String(code || "").toUpperCase();
  if (value === "REPORT_DISCLOSURE") return "보고서 연결 공시";
  if (value === "DMA_PRECHECK") return "DMA 사전 계산";
  return value || "-";
};

const asItems = (value) => {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.items)) return value.items;
  if (Array.isArray(value?.metricItems)) return value.metricItems;
  if (Array.isArray(value?.metrics)) return value.metrics;
  return [];
};

const SubsidiaryRequestModal = ({
  isOpen,
  onClose,
  runId,
  reportingYear,
  sourceCycleId,
  rollupPurposeCode = "DMA_PRECHECK",
  metricScopeCode = "G0_02_FINANCIAL_BASIS",
  onRequested,
}) => {
  const dispatch = useDispatch();
  const subsidiaries = useSelector((state) => state.report.rollup.subsidiaries);
  const scopePreview = useSelector((state) => state.report.rollup.scopePreview);
  const loadingSubsidiaries = useSelector((state) => state.report.loading.subsidiaries);
  const loadingPreview = useSelector((state) => state.report.loading.rollupScopePreview);
  const creatingBatch = useSelector((state) => state.report.loading.createBatch);
  const [selectedIds, setSelectedIds] = useState([]);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState(null);

  const requiresSourceCycle = rollupPurposeCode === "REPORT_DISCLOSURE";
  const previewMetricItems = useMemo(() => {
    const items = asItems(scopePreview);
    if (items.length > 0) return items;

    if (Array.isArray(scopePreview?.metricIds)) {
      return scopePreview.metricIds.map((metricId) => ({
        metricId,
      }));
    }

    return [];
  }, [scopePreview]);
  const metricCount =
    scopePreview?.metricCount ??
    scopePreview?.requestedMetricCount ??
    previewMetricItems.length;
  const atomicCount =
    scopePreview?.atomicCount ??
    scopePreview?.requiredAtomicCount ??
    scopePreview?.resolvedExternalEntityAtomicCount ??
    scopePreview?.requiredAtomicMetricIds?.length ??
    previewMetricItems.reduce((sum, metric) => sum + (metric.atomicCount || metric.atomicItems?.length || 0), 0);

  const loadData = useCallback(async () => {
    if (!isOpen) return;
    if (requiresSourceCycle && !sourceCycleId) {
      setError("이중중대성평가 공시 연결기준은 sourceCycleId가 필요합니다.");
      return;
    }

    setError(null);
    try {
      const commonParams = {
        runId,
        sourceCycleId,
        rollupPurposeCode,
        metricScopeCode,
      };

      const [, subsidiaryRes] = await Promise.all([
        dispatch(fetchRollupScopePreview(commonParams)).unwrap(),
        dispatch(fetchRollupSubsidiaries(commonParams)).unwrap(),
      ]);

      const items = Array.isArray(subsidiaryRes?.data?.items)
        ? subsidiaryRes.data.items
        : Array.isArray(subsidiaryRes?.items)
          ? subsidiaryRes.items
          : Array.isArray(subsidiaryRes?.data)
            ? subsidiaryRes.data
            : [];
      setSelectedIds(items.map((item) => item.companyId).filter((id) => id != null));
    } catch (err) {
      console.error(err);
      setError(err?.message || "자회사 요청 정보 조회에 실패했습니다.");
    }
  }, [dispatch, isOpen, metricScopeCode, requiresSourceCycle, rollupPurposeCode, runId, sourceCycleId]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      if (isOpen) {
        loadData();
      } else {
        setSelectedIds([]);
        setError(null);
      }
    });
    return () => {
      active = false;
    };
  }, [isOpen, loadData]);

  const handleToggle = (companyId) => {
    setSelectedIds((prev) =>
      prev.includes(companyId)
        ? prev.filter((id) => id !== companyId)
        : [...prev, companyId]
    );
  };

  const handleRequest = async () => {
    if (selectedIds.length === 0) return;
    if (requiresSourceCycle && !sourceCycleId) {
      showDefaultAlert("요청 불가", "이중중대성평가 공시 연결기준은 sourceCycleId가 필요합니다.", "warning");
      return;
    }

    setRequesting(true);
    try {
      const res = await dispatch(
        createRollupBatch({
          runId,
          sourceCycleId,
          sourceCompanyIds: selectedIds,
          rollupPurposeCode,
          metricScopeCode,
        })
      ).unwrap();

      const data = res?.data || res;
      const batchId = data?.batchId;
      if (batchId) {
        dispatch(setActiveBatchId(batchId));
        await Promise.all([
          dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
          dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
        ]);
      }

      showDefaultAlert("완료", "자회사 데이터 요청이 완료되었습니다.", "success");
      onRequested?.(batchId);
      onClose();
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "요청에 실패했습니다.", "error");
    } finally {
      setRequesting(false);
    }
  };

  if (!isOpen) return null;

  const loading = loadingSubsidiaries || loadingPreview;
  const disabled =
    loading ||
    requesting ||
    creatingBatch ||
    Boolean(error) ||
    selectedIds.length === 0 ||
    (requiresSourceCycle && !sourceCycleId);

  return createPortal(
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 760 }}>
        <div className="ob1-modal-header">
          <h2>자회사 데이터 요청</h2>
          <button className="ob1-btn-close" onClick={onClose}>×</button>
        </div>
        <div className="ob1-modal-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "8px", marginBottom: "16px" }}>
            {[
              ["보고연도", reportingYear || "-"],
              ["롤업 목적", purposeLabel(rollupPurposeCode)],
              ["Metric", metricCount || 0],
              ["Atomic", atomicCount || 0],
            ].map(([label, value]) => (
              <div key={label} style={{ padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#f8fafc" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: "4px" }}>{label}</div>
                <div style={{ fontWeight: 700, color: "#0f172a" }}>{value}</div>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: "16px" }}>
            <div style={{ fontWeight: 700, marginBottom: "8px", color: "#0f172a" }}>요청 Metric 미리보기</div>
            {loadingPreview && !scopePreview ? (
              <div style={{ padding: "14px", color: "#64748b", border: "1px dashed #cbd5e1", borderRadius: "8px" }}>
                롤업 범위를 확인하고 있습니다.
              </div>
            ) : previewMetricItems.length === 0 ? (
              <div style={{ padding: "14px", color: "#64748b", border: "1px dashed #cbd5e1", borderRadius: "8px" }}>
                표시할 Metric 미리보기가 없습니다.
              </div>
            ) : (
              <div style={{ maxHeight: "132px", overflow: "auto", display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "8px" }}>
                {previewMetricItems.map((metric) => (
                  <div key={metric.metricId} style={{ padding: "10px", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
                    <div style={{ fontWeight: 700, color: "#1e293b" }}>{metric.metricId}</div>
                    <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "2px" }}>
                      {metric.metricName || metric.metricNameKr || "-"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {loading && subsidiaries.length === 0 && (
            <div className="ob1-table-loading" style={{ padding: "24px" }}>
              <div className="ob1-spinner" />
              <p>자회사 목록을 불러오고 있습니다.</p>
            </div>
          )}

          {!loading && error && (
            <div className="ob1-inline-error" style={{ margin: "16px 0" }}>
              <span className="ob1-error-icon">!</span>
              <span>{error}</span>
              <button type="button" className="ob1-btn-retry" onClick={loadData}>
                다시 시도
              </button>
            </div>
          )}

          {!loading && !error && subsidiaries.length === 0 && (
            <div style={{ padding: "24px", textAlign: "center", color: "#64748b" }}>
              요청 가능한 자회사가 없습니다.
            </div>
          )}

          {subsidiaries.length > 0 && (
            <ul
              className="sub-list"
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                maxHeight: "260px",
                overflow: "auto",
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
                    <span style={{ fontWeight: 500 }}>{sub.companyName}</span>
                    {sub.companyCode && (
                      <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                        ({sub.companyCode})
                      </span>
                    )}
                  </label>
                  <div style={{ textAlign: "right", fontSize: "0.8rem", color: "#2563eb" }}>
                    요청 대상
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
              cursor: disabled ? "not-allowed" : "pointer",
              opacity: disabled ? 0.5 : 1,
            }}
            onClick={handleRequest}
            disabled={disabled}
          >
            {requesting || creatingBatch ? "요청 중..." : "요청 보내기"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default SubsidiaryRequestModal;
