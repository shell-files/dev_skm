/**
 * RollupSummaryPanel.jsx
 * 레이어: Component (onboards)
 * 역할: 자회사 데이터 취합(롤업) 현황을 단계별 스테퍼·요청 관리 모달과 함께 표시하고, 데이터 취합 실행·전년도 기준값 입력 등을 처리하는 패널
 *
 * Props:
 *   batchId — 활성 롤업 배치 ID
 *   sourceCycleId — POST_DMA_DISCLOSURE 사이클의 소스 cycleId
 *   rollupPurposeCode — 롤업 목적 코드 (DMA_PRECHECK / REPORT_DISCLOSURE)
 *   metricScopeCode — 지표 범위 코드
 *   workflow — 현재 워크플로우 객체 (nextAction 포함)
 *   onCtaClick — 자회사 데이터 요청 버튼 클릭 핸들러
 *   onCalculated — 데이터 취합 완료 후 콜백
 *   onSendSource — 데이터 전송 모달 열기 핸들러
 *
 * 의존 컴포넌트:
 *   RollupSummaryPanel (자기 자신) — 인라인 요청 관리 모달 렌더링 포함
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router";
import { useDispatch, useSelector } from "react-redux";
import {
  calculateRollupBatch,
  fetchRollupBaselineRequirements,
  fetchRollupBatchSources,
  fetchRollupBatchStatus,
  saveRollupBaselineValues,
} from "@stores/reportSlice";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import { purposeLabel, readinessLabel, transferLabel, approvalLabel, numberOrZero } from "./rollupUtils";
import "@styles/onboarding1.css";
import "@styles/onboardingModal.css";

const RollupSummaryPanel = ({
  batchId,
  sourceCycleId,
  onCalculated,
  rollupPurposeCode = "DMA_PRECHECK",
  metricScopeCode = "G0_02_FINANCIAL_BASIS",
  onCalculate,
  workflow,
  onCtaClick,
  onSendSource,
}) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const reduxStatusInfo = useSelector((state) => state.report.rollup.batchStatus);
  const batchSources = useSelector((state) => state.report.rollup.batchSources);
  const loadingStatus = useSelector((state) => state.report.loading.batchStatus);
  const loadingSources = useSelector((state) => state.report.loading.rollupBatchSources);
  const calculatingRedux = useSelector((state) => state.report.loading.calculateBatch);
  const statusError = useSelector((state) => state.report.error.batchStatus);
  const sourceError = useSelector((state) => state.report.error.rollupBatchSources);
  const [showManageModal, setShowManageModal] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);

  // S5-B14: 전년도 연결 기준값(BASELINE_REQUIRED) 수동입력 카드 상태
  const [showBaselineCard, setShowBaselineCard] = useState(false);
  const [baselineItems, setBaselineItems] = useState([]);
  const [baselineInputs, setBaselineInputs] = useState({});
  const [savingBaseline, setSavingBaseline] = useState(false);

  const loadBaselineRequirements = useCallback(async () => {
    if (!batchId) return [];
    try {
      const res = await dispatch(fetchRollupBaselineRequirements({ batchId })).unwrap();
      const data = res?.data || res;
      const items = Array.isArray(data?.items) ? data.items : [];
      const missing = items.filter(
        (it) => String(it.status || "").toUpperCase() === "MISSING"
      );
      setBaselineItems(missing);
      setBaselineInputs((prev) => {
        const next = { ...prev };
        missing.forEach((it) => {
          if (next[it.sourceAtomicMetricId] == null) next[it.sourceAtomicMetricId] = "";
        });
        return next;
      });
      return missing;
    } catch (err) {
      console.error(err);
      return [];
    }
  }, [batchId, dispatch]);

  const statusInfo = useMemo(() => reduxStatusInfo, [reduxStatusInfo]);
  const canCreateRequest =
    workflow?.nextAction === "REQUEST_ROLLUP" ||
    (
      rollupPurposeCode === "REPORT_DISCLOSURE" &&
      metricScopeCode === "SELECTED_DISCLOSURE" &&
      sourceCycleId
    );

  const fetchRollupState = useCallback(async () => {
    if (!batchId) return;
    setError(null);
    try {
      await Promise.all([
        dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
        dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
      ]);
    } catch (err) {
      console.error(err);
      setError(err?.message || "데이터 취합 상태 조회에 실패했습니다.");
    }
  }, [batchId, dispatch]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active) fetchRollupState();
    });
    return () => {
      active = false;
    };
  }, [fetchRollupState]);

  if (!batchId && !canCreateRequest) return null;

  if (batchId && (loadingStatus || loadingSources) && !statusInfo) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-table-loading" style={{ padding: "16px", display: "flex", gap: "8px", alignItems: "center" }}>
          <div className="ob1-spinner" style={{ width: "20px", height: "20px" }} />
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#475569" }}>데이터 취합 상태를 불러오고 있습니다.</p>
        </div>
      </div>
    );
  }

  const activeError = error || statusError?.message || sourceError?.message;
  if (activeError) {
    return (
      <div className="ob1-rollup-panel ob1-rollup-panel-v2">
        <div className="ob1-inline-error">
          <span className="ob1-error-icon">!</span>
          <span>{activeError}</span>
          <button type="button" className="ob1-btn-retry" onClick={fetchRollupState}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (batchId && !statusInfo) return null;

  const requestedCount = numberOrZero(statusInfo?.requestedCount);
  const sentCount = numberOrZero(statusInfo?.sentCount);
  const pendingCount = numberOrZero(statusInfo?.pendingCount);
  const calculateReadyYn = Boolean(statusInfo?.calculateReadyYn);
  const dmaReadyYn = Boolean(statusInfo?.dmaReadyYn);
  const reportReadyYn = Boolean(statusInfo?.reportReadyYn);
  const batchStatus = String(statusInfo?.batchStatus || "").toLowerCase();
  const isCalculated = batchStatus === "completed" || batchStatus === "calculated";
  const isCalculating = calculating || calculatingRedux;

  const handleCalc = async ({ force = false } = {}) => {
    if (onCalculate) {
      onCalculate(batchId);
      return;
    }

    if (isCalculated && !force) return;

    if (!calculateReadyYn) {
      showDefaultAlert(
        "계산 대기",
        "자회사 데이터 전송 완료 후 계산할 수 있습니다.",
        "warning"
      );
      return;
    }

    setCalculating(true);
    try {
      const calcRes = await dispatch(calculateRollupBatch({ batchId })).unwrap();
      const calcData = calcRes?.data || calcRes;
      const warnings = Array.isArray(calcData?.warnings) ? calcData.warnings : [];
      const hasBaselineRequired = warnings.some(
        (w) => String(w?.error || "").toUpperCase() === "BASELINE_REQUIRED"
      );
      await Promise.all([
        dispatch(fetchRollupBatchStatus({ batchId })).unwrap(),
        dispatch(fetchRollupBatchSources({ batchId })).unwrap(),
      ]);
      if (hasBaselineRequired) {
        await loadBaselineRequirements();
        setShowBaselineCard(true);
        showDefaultAlert(
          "전년도 기준값 입력 필요",
          "전년 대비 지표 산정을 위해 전년도 연결 기준값을 입력한 뒤 다시 데이터 취합을 실행하세요.",
          "warning"
        );
      } else {
        setShowBaselineCard(false);
        setBaselineItems([]);
        showDefaultAlert("성공", "데이터 취합이 완료되었습니다.", "success");
        onCalculated?.();
      }
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "데이터 취합에 실패했습니다.", "error");
    } finally {
      setCalculating(false);
    }
  };

  const handleSaveBaseline = async () => {
    const values = baselineItems
      .map((it) => {
        const raw = baselineInputs[it.sourceAtomicMetricId];
        const numeric = raw === "" || raw == null ? null : Number(raw);
        return {
          metricId: it.sourceMetricId || it.metricId,
          atomicMetricId: it.sourceAtomicMetricId,
          reportingYear: it.requiredReportingYear,
          valueNumeric: numeric,
          unit: it.unit,
        };
      })
      .filter((v) => v.valueNumeric != null && !Number.isNaN(v.valueNumeric));

    if (values.length === 0) {
      showDefaultAlert("입력 필요", "전년도 기준값을 입력하세요.", "warning");
      return;
    }

    setSavingBaseline(true);
    try {
      await dispatch(saveRollupBaselineValues({ batchId, values })).unwrap();
      const stillMissing = await loadBaselineRequirements();
      if (stillMissing.length === 0) {
        showDefaultAlert(
          "저장 완료",
          "전년도 기준값이 모두 입력되었습니다. 다시 데이터 취합을 실행하세요.",
          "success"
        );
      } else {
        showDefaultAlert(
          "저장 완료",
          "전년도 기준값이 저장되었습니다. 다시 데이터 취합을 실행하세요.",
          "success"
        );
      }
    } catch (err) {
      console.error(err);
      showDefaultAlert("오류", err?.message || "전년도 기준값 저장에 실패했습니다.", "error");
    } finally {
      setSavingBaseline(false);
    }
  };

  let btnText = "자회사 데이터 대기";
  let btnClass = "";
  let btnDisabled = true;
  let btnAction = () => {};

  const nextAction = workflow?.nextAction;
  if (nextAction === "REQUEST_ROLLUP") {
    btnText = "자회사 데이터 요청하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = onCtaClick;
  } else if (nextAction === "WAIT_ROLLUP") {
    if (isCalculating) {
      btnText = "계산 중...";
      btnDisabled = true;
    } else if (isCalculated) {
      btnText = "데이터 취합 완료";
      btnClass = "calculated";
      btnDisabled = true;
    } else if (calculateReadyYn) {
      btnText = "데이터 취합 실행";
      btnClass = "primary";
      btnDisabled = false;
      btnAction = handleCalc;
    } else {
      btnText = "자회사 데이터 대기";
      btnDisabled = true;
    }
  } else if (nextAction === "START_DMA") {
    btnText = "이중중대성평가 진행하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = () => navigate("/benchmk");
  } else {
    btnText = isCalculating ? "계산 중..." : isCalculated ? "데이터 취합 완료" : calculateReadyYn ? "데이터 취합 실행" : "자회사 데이터 대기";
    btnDisabled = isCalculating || (!calculateReadyYn && !isCalculated);
    if (isCalculated) btnClass = "calculated";
    else if (calculateReadyYn) btnClass = "primary";
    btnAction = handleCalc;
  }

  if (!batchId && canCreateRequest) {
    btnText = "자회사 데이터 요청하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = onCtaClick;
  } else if (batchId && isCalculated && nextAction !== "START_DMA") {
    btnText = "데이터 취합 완료";
    btnClass = "calculated";
    btnDisabled = true;
  } else if (batchId && nextAction === "WAIT_ROLLUP" && calculateReadyYn) {
    btnText = isCalculating ? "계산 중..." : "데이터 취합 실행";
    btnClass = "primary";
    btnDisabled = isCalculating;
    btnAction = handleCalc;
  } else if (batchId && nextAction === "WAIT_ROLLUP") {
    btnText = "자회사 데이터 대기";
    btnClass = "";
    btnDisabled = true;
  }

  // S5-B14: REPORT_DISCLOSURE 데이터 취합 완료 후에는 "보고서 생성하기"로 전환하고
  // /result 의 "점수 해석" 탭으로 이동한다. (DMA_PRECHECK 는 기존 동작 유지)
  const isReportDisclosure =
    String(rollupPurposeCode || "").toUpperCase() === "REPORT_DISCLOSURE";
  if (batchId && isCalculated && isReportDisclosure && !isCalculating && !showBaselineCard && baselineItems.length === 0) {
    btnText = "보고서 생성하기";
    btnClass = "primary";
    btnDisabled = false;
    btnAction = () => navigate("/result", { state: { initialLeftTab: 2 } });
  }

  const finalStepLabel =
    rollupPurposeCode === "REPORT_DISCLOSURE"
      ? "보고서 생성 준비"
      : "이중중대성평가 준비";

  return (
    <div className="ob1-rollup-panel ob1-rollup-panel-v2" style={{ flexDirection: "column", alignItems: "stretch" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "16px", width: "100%" }}>
        <div className="ob1-rollup-info">
          <h3 className="ob1-rollup-title">자회사 데이터 취합</h3>

        </div>

        <div className="ob1-rollup-stepper" style={{ flex: 1, margin: "0 24px", justifyContent: "center" }}>
          <div className={`ob1-rollup-step ${batchId ? "completed" : "active"}`}>요청 생성</div>
          <div className={`ob1-rollup-step ${calculateReadyYn ? "completed" : batchId ? "active" : ""}`}>자회사 전송</div>
          <div className={`ob1-rollup-step ${isCalculated ? "completed" : calculateReadyYn ? "active" : ""}`}>데이터 취합</div>
          <div className={`ob1-rollup-step ${nextAction === "START_DMA" ? "active" : dmaReadyYn || reportReadyYn ? "completed" : ""}`}>
            {finalStepLabel}
          </div>
        </div>

        <div className="ob1-rollup-actions" style={{ display: "flex", alignItems: "center" }}>
          {batchId && (
            <button
              type="button"
              className="ob1-rollup-btn secondary"
              onClick={() => setShowManageModal(true)}
              style={{ marginRight: "8px" }}
            >
              요청 관리
            </button>
          )}
          <button
            type="button"
            className={`ob1-rollup-btn ${btnClass}`}
            onClick={btnAction}
            disabled={btnDisabled}
            title={btnDisabled && !isCalculating && !isCalculated && nextAction === "WAIT_ROLLUP" ? "자회사 데이터 전송 완료 후 진행할 수 있습니다." : ""}
          >
            {btnText}
          </button>
        </div>
      </div>

      {showBaselineCard && (
        <div
          style={{
            marginTop: "16px",
            border: "1px solid #fcd34d",
            background: "#fffbeb",
            borderRadius: "10px",
            padding: "16px 18px",
          }}
        >
          {baselineItems.length > 0 ? (
            <>
              <div style={{ marginBottom: "10px" }}>
                <strong style={{ color: "#b45309", fontSize: "0.95rem" }}>
                  전년도 기준값 입력 필요
                </strong>
                <p style={{ margin: "6px 0 0", fontSize: "0.82rem", color: "#92400e", lineHeight: 1.5 }}>
                  전년 대비 지표 산정을 위해 전년도 연결 기준값을 입력하세요.
                  <br />
                  이 값은 현재 프로젝트에서 입력하지만, 데이터 기준연도는 전년도로 저장됩니다.
                </p>
              </div>

              <div className="ob1-table-container" style={{ overflowX: "auto" }}>
                <table className="ob1-table" style={{ minWidth: "640px" }}>
                  <thead>
                    <tr>
                      <th>지표</th>
                      <th>기준 항목</th>
                      <th>기준연도</th>
                      <th>입력값</th>
                      <th>단위</th>
                    </tr>
                  </thead>
                  <tbody>
                    {baselineItems.map((it) => (
                      <tr key={`${it.ruleCode}-${it.sourceAtomicMetricId}`}>
                        <td>{it.metricId || it.sourceMetricId || "-"}</td>
                        <td>
                          {it.sourceAtomicName || it.sourceAtomicMetricId}
                          <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                            {it.sourceAtomicMetricId}
                          </div>
                        </td>
                        <td>{it.requiredReportingYear}</td>
                        <td>
                          <input
                            type="number"
                            className="ob1-input"
                            value={baselineInputs[it.sourceAtomicMetricId] ?? ""}
                            onChange={(e) =>
                              setBaselineInputs((prev) => ({
                                ...prev,
                                [it.sourceAtomicMetricId]: e.target.value,
                              }))
                            }
                            style={{ width: "140px", padding: "6px 8px" }}
                            placeholder="기준값"
                          />
                        </td>
                        <td>{it.unit || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button
                  type="button"
                  className="ob1-rollup-btn primary"
                  onClick={handleSaveBaseline}
                  disabled={savingBaseline}
                >
                  {savingBaseline ? "저장 중..." : "전년도 기준값 저장"}
                </button>
                <button
                  type="button"
                  className="ob1-rollup-btn"
                  onClick={() => handleCalc({ force: true })}
                  disabled={isCalculating || savingBaseline}
                >
                  {isCalculating ? "취합 중..." : "다시 데이터 취합 실행"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
              <div>
                <strong style={{ color: "#065f46", fontSize: "0.95rem" }}>전년도 기준값 저장 완료</strong>
                <p style={{ margin: "6px 0 0", fontSize: "0.82rem", color: "#064e3b", lineHeight: 1.5 }}>
                  모든 기준값이 저장되었습니다. 데이터 취합을 다시 실행해야 전년 대비 지표가 반영됩니다.
                </p>
              </div>
              <button
                type="button"
                className="ob1-rollup-btn primary"
                onClick={() => handleCalc({ force: true })}
                disabled={isCalculating}
              >
                {isCalculating ? "취합 중..." : "다시 데이터 취합 실행"}
              </button>
            </div>
          )}
        </div>
      )}

      {showManageModal && createPortal(
        <div className="ob-modal-overlay" onClick={() => setShowManageModal(false)}>
          <div className="ob-modal-shell" onClick={e => e.stopPropagation()} style={{ maxWidth: "900px", width: "90%" }}>
            <div className="ob-modal-header" style={{ padding: "20px 24px" }}>
              <h2 className="ob-modal-title" style={{ fontSize: "1.25rem" }}>자회사 데이터 취합 현황</h2>
              <button
                type="button"
                className="ob1-btn-close"
                onClick={() => setShowManageModal(false)}
                style={{ border: "none", background: "none", fontSize: "1.5rem", cursor: "pointer", color: "#64748b" }}
              >
                ×
              </button>
            </div>
            <div className="ob-modal-body" style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: "8px" }}>
                {[
                  ["요청", requestedCount],
                  ["전송", sentCount],
                  ["대기", pendingCount],
                  ["계산 가능", calculateReadyYn ? "Y" : "N"],
                  ["상태", statusInfo.batchStatus || "-"],
                ].map(([label, value]) => (
                  <div key={label} style={{ padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#f8fafc" }}>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginBottom: "4px" }}>{label}</div>
                    <div style={{ fontWeight: 700, color: "#0f172a" }}>{value}</div>
                  </div>
                ))}
              </div>

              {!calculateReadyYn && !isCalculated && (
                <div style={{ marginTop: "10px", fontSize: "0.82rem", color: "#64748b" }}>
                  자회사 데이터 전송 완료 후 계산할 수 있습니다.
                </div>
              )}

              <div style={{ marginTop: "24px", borderTop: "1px solid #e2e8f0", paddingTop: "16px", width: "100%" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <strong style={{ color: "#0f172a" }}>자회사 전송 현황</strong>
                  {(loadingSources || loadingStatus) && <span style={{ fontSize: "0.8rem", color: "#64748b" }}>갱신 중...</span>}
                </div>
                {batchSources.length === 0 ? (
                  <div style={{ padding: "18px", border: "1px dashed #cbd5e1", borderRadius: "8px", color: "#64748b", textAlign: "center" }}>
                    표시할 자회사 전송 현황이 없습니다.
                  </div>
                ) : (
                  <div className="ob1-table-container" style={{ maxHeight: "300px", overflow: "auto" }}>
                    <table className="ob1-table">
                      <thead>
                        <tr>
                          <th>자회사</th>
                          <th>준비 상태</th>
                          <th>승인 상태</th>
                          <th>전송 상태</th>
                          <th>승인 Atomic</th>
                          <th>누락</th>
                        </tr>
                      </thead>
                      <tbody>
                        {batchSources.map((source) => {
                          const required = source.requiredAtomicCount ?? source.requiredCount ?? 0;
                          const approved = source.currentApprovedAtomicCount ?? source.approvedAtomicCount ?? 0;
                          const missing = source.currentMissingAtomicCount ?? source.missingAtomicCount ?? source.missingAtomicMetricIds?.length ?? 0;
                          return (
                            <tr key={source.sourceCompanyId || source.companyId}>
                              <td>{source.sourceCompanyName || source.companyName || source.sourceCompanyId || source.companyId}</td>
                              <td>{readinessLabel(source.readinessStatus)}</td>
                              <td>{approvalLabel(source.approvalStatus)}</td>
                              <td>{transferLabel(source.transferStatus)}</td>
                              <td>{approved} / {required}</td>
                              <td>{missing}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default RollupSummaryPanel;
