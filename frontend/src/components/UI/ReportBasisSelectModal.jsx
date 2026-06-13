import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { useAuth } from '@hooks/AuthContext.jsx';
import "@styles/reportBasisSelectModal.css";
import {
  DEFAULT_REPORTING_YEAR,
  normalizeReportingYear,
  probeCurrentWorkflow,
  resumeReportWorkflow,
  startReportWorkflow,
  setCurruntYear,
  setMaterialityRunId
} from "@stores/reportSlice";

// Card illustrations
import entityCardImg from "@assets/reportbasis/illustrations/entity-card.png";
import consolidatedCardImg from "@assets/reportbasis/illustrations/consolidated-card.png";

// Side panel icons
import entityReportIcon from "@assets/reportbasis/icons/entity-report.png";
import entityNoSubsidiaryIcon from "@assets/reportbasis/icons/entity-no-subsidiary.png";
import entitySingleCompanyIcon from "@assets/reportbasis/icons/entity-single-company.png";
import consolidatedGroupIcon from "@assets/reportbasis/icons/consolidated-group.png";
import consolidatedDataSyncIcon from "@assets/reportbasis/icons/consolidated-data-sync.png";
import consolidatedReportIcon from "@assets/reportbasis/icons/consolidated-report.png";

// Process steps
import stepBasisImg from "@assets/reportbasis/steps/step-basis.png";
import stepG0Img from "@assets/reportbasis/steps/step-g0.png";
import stepSubsidiaryTransferImg from "@assets/reportbasis/steps/step-subsidiary-transfer.png";
import stepRollupImg from "@assets/reportbasis/steps/step-rollup.png";
import stepDmaImg from "@assets/reportbasis/steps/step-dma.png";
import stepOnboardingImg from "@assets/reportbasis/steps/step-onboarding.png";
import stepReportImg from "@assets/reportbasis/steps/step-report.png";

const ENTITY_STEPS = [
  { img: stepBasisImg, label: "발행 기준 선택" },
  { img: stepG0Img, label: "일반 입력·승인" },
  { img: stepDmaImg, label: "중대성평가 수행" },
  { img: stepOnboardingImg, label: "선정 지표 입력" },
  { img: stepReportImg, label: "AI 공시 보고서 발행" },
];

const CONSOLIDATED_STEPS = [
  { img: stepBasisImg, label: "발행 기준 선택" },
  { img: stepG0Img, label: "일반 입력·승인" },
  { img: stepSubsidiaryTransferImg, label: "연결 데이터 요청" },
  { img: stepRollupImg, label: "연결 데이터 취합" },
  { img: stepDmaImg, label: "중대성평가 수행" },
  { img: stepOnboardingImg, label: "선정 지표 입력" },
  { img: stepReportImg, label: "AI 보고서 발행" },
];

const ReportBasisSelectModal = ({
  // isOpen,
  // onClose,
  companyId,
  reportingYear = DEFAULT_REPORTING_YEAR,
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [selected, setSelected] = useState("ENTITY");
  const [selectedYear, setSelectedYear] = useState(
    normalizeReportingYear(reportingYear)
  );
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentRunId, setCurrentRunId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const statusCacheRef = useRef({});
  const { isBasisModalOpen : isOpen, setIsBasisModalOpen } = useAuth();

  const onClose = () => setIsBasisModalOpen(false);

  useEffect(() => {
    if (!isOpen) {
      statusCacheRef.current = {};
      return;
    }
    setSelectedYear(normalizeReportingYear(reportingYear));
    setSelected("ENTITY");
    setWorkflowStatus(null);
    setCurrentRunId(null);
    setError(null);
  }, [isOpen, companyId, reportingYear]);

  useEffect(() => {
    if (!isOpen || !companyId) return;

    const cacheKey = normalizeReportingYear(selectedYear);
    if (statusCacheRef.current[cacheKey]) {
      setWorkflowStatus(statusCacheRef.current[cacheKey].status);
      setCurrentRunId(statusCacheRef.current[cacheKey].runId);
      return;
    }

    let isMounted = true;
    const fetchCurrent = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await dispatch(
          probeCurrentWorkflow({ companyId, reportingYear: selectedYear })
        ).unwrap();

        if (!isMounted) return;

        if (res?.status === false || res?.success === false || !res?.data) {
          setError(res?.error?.message || "워크플로우 조회에 실패했습니다.");
        } else if (res?.data?.workflowStep === "NO_RUN") {
          statusCacheRef.current[normalizeReportingYear(selectedYear)] = { status: "NO_RUN", runId: null };
          setWorkflowStatus("NO_RUN");
          setCurrentRunId(null);
        } else {
          const runId = res?.data?.runId ?? null;
          statusCacheRef.current[normalizeReportingYear(selectedYear)] = { status: "EXISTS", runId };
          setWorkflowStatus("EXISTS");
          setCurrentRunId(runId);
        }
      } catch (err) {
        console.error("[ReportBasisSelectModal] probeCurrentWorkflow error:", err);
        if (isMounted) setError("워크플로우 조회 중 오류가 발생했습니다.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchCurrent();

    return () => {
      isMounted = false;
    };
  }, [dispatch, isOpen, companyId, selectedYear]);

  if (!isOpen) return null;

  const steps = CONSOLIDATED_STEPS;

  const isStepActive = (idx) => {
    if (selected === "ENTITY") {
      return idx !== 2 && idx !== 3;
    } else if (selected === "CONSOLIDATED") {
      return true;
    }
    return idx === 0;
  };

  const handleConfirm = async () => {
    if (loading) return;

    if (workflowStatus === "EXISTS") {
      if (!currentRunId) {
        setError("현재 선택 연도의 실행 정보를 찾을 수 없습니다.");
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const res = await dispatch(
          resumeReportWorkflow({ runId: currentRunId })
        ).unwrap();
        const isFailed = res?.status === false || res?.success === false || !res?.data;
        if (isFailed) {
          setError(res?.error?.message || res?.detail || "기존 프로젝트 재개에 실패했습니다.");
          setLoading(false);
          return;
        }
      } catch (err) {
        console.error("[ReportBasisSelectModal] resumeWorkflow error:", err);
        setError("기존 프로젝트 재개 중 오류가 발생했습니다.");
        setLoading(false);
        return;
      }

      dispatch(setMaterialityRunId(currentRunId));
      console.log(currentRunId)

      dispatch(setCurruntYear(selectedYear));
      onClose();
      navigate('/onb');
      return;
    }

    if (!selected) return;
    if (!companyId) {
      setError("회사를 먼저 선택해 주세요.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await dispatch(
        startReportWorkflow({
          companyId,
          reportingYear: normalizeReportingYear(selectedYear),
          reportBasisType: selected,
        })
      ).unwrap();

      const isFailed = res?.status === false || res?.success === false || !res?.data;
      if (isFailed) {
        setError(res?.error?.message || "워크플로우 시작에 실패했습니다.");
        setLoading(false);
        return;
      }
      dispatch(setMaterialityRunId(currentRunId));

      dispatch(setCurruntYear(normalizeReportingYear(selectedYear)));

      setIsBasisModalOpen(false);
      onClose();
      navigate('/onb');
    } catch (err) {
      console.error("[ReportBasisSelectModal] startWorkflow error:", err);
      setError("워크플로우 시작 중 오류가 발생했습니다.");
      setLoading(false);
    }
  };

  return createPortal(
    <div className="rbm-overlay" role="dialog" aria-modal="true" aria-labelledby="rbm-title">
      <div className="rbm-layout" style={{ maxWidth: workflowStatus === "NO_RUN" ? "1040px" : "640px", animation: "rbmModalFloatUp 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) forwards" }}>
        <div className="rbm-main">
          <div className="rbm-header">
            <button className="rbm-close" onClick={onClose} aria-label="닫기">×</button>
            <h2 id="rbm-title" className="rbm-title">보고서 프로젝트 선택</h2>
            <p className="rbm-desc">지속가능경영보고서를 작성할 연도와 기준을 선택해 주세요.</p>

            <div className="rbm-year-select-wrapper" style={{ marginTop: "16px", marginBottom: "8px" }}>
              <label htmlFor="reportingYearSelect" style={{ fontWeight: "bold", marginRight: "12px" }}>
                보고연도:
              </label>
              <select
                id="reportingYearSelect"
                value={normalizeReportingYear(selectedYear)}
                onChange={(e) => {
                  const newYear = normalizeReportingYear(e.target.value);
                  setSelectedYear(newYear);
                  setSelected("ENTITY");
                  setError(null);
                  
                  if (statusCacheRef.current[newYear]) {
                    setWorkflowStatus(statusCacheRef.current[newYear].status);
                    setCurrentRunId(statusCacheRef.current[newYear].runId);
                  } else {
                    setWorkflowStatus(null);
                    setCurrentRunId(null);
                  }
                }}
                style={{ padding: "6px 12px", borderRadius: "4px", border: "1px solid #ccc" }}
              >
                <option value={2024}>2024</option>
                <option value={2025}>2025</option>
                <option value={2026}>2026</option>
                <option value={2027}>2027</option>
              </select>
            </div>

            <style>{`
              @keyframes rbmModalFloatUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
              }
              @keyframes rbmFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
              }
              @keyframes rbmSpin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }
            `}</style>
          </div>

          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            {workflowStatus === null ? (
              <div key="status-null" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "20px 0", animation: "rbmFadeIn 0.3s ease-out" }}>
                <div className="rbm-exists-message" style={{ padding: "40px 30px", textAlign: "center", background: "#f8fafc", borderRadius: "12px", margin: "0", border: "1px solid #e2e8f0", width: "100%", minHeight: "140px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <svg width="32" height="32" viewBox="0 0 24 24" style={{ animation: "rbmSpin 1s linear infinite", marginBottom: "12px", color: "#03A94D" }}>
                    <path fill="currentColor" d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z" />
                  </svg>
                  <p style={{ color: "#64748b", fontSize: "0.9rem", margin: 0 }}>프로젝트 정보를 확인하고 있습니다...</p>
                </div>
              </div>
            ) : workflowStatus === "EXISTS" ? (
              <div key="status-exists" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "20px 0", animation: "rbmFadeIn 0.3s ease-out" }}>
                <div className="rbm-exists-message" style={{ padding: "40px 30px", textAlign: "center", background: "#f8fafc", borderRadius: "12px", margin: "0", border: "1px solid #e2e8f0", width: "100%", minHeight: "140px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <h3 style={{ fontSize: "18px", margin: "0 0 12px 0", color: "#1e293b" }}>
                    이미 생성된 {selectedYear}년 보고서 프로젝트가 있습니다.
                  </h3>
                  <p style={{ color: "#64748b", fontSize: "0.9rem", margin: 0 }}>
                    아래 [해당 연도로 이동하기] 버튼을 눌러 프로젝트를 계속 진행하세요.
                  </p>
                </div>
              </div>
            ) : (
              <div key="status-norun" className="rbm-cards" style={{ flex: 1, animation: "rbmFadeIn 0.3s ease-out" }}>
              <button
                type="button"
                className={`rbm-card ${selected === "ENTITY" ? "rbm-card--selected" : ""}`}
                onClick={() => setSelected("ENTITY")}
                aria-pressed={selected === "ENTITY"}
              >
                <div className="rbm-card-badge">단일 회사</div>
                <div className="rbm-card-body">
                  <div className="rbm-card-illust">
                    <img
                      src={entityCardImg}
                      alt="독립기준 ENTITY 일러스트"
                      width={132}
                      height={132}
                      style={{ width: 132, height: 132, objectFit: "contain" }}
                    />
                  </div>
                  <div className="rbm-card-info">
                    <h3 className="rbm-card-title">독립기준 (ENTITY)</h3>
                    <p className="rbm-card-text">
                      본사 단독으로 보고서를 작성합니다.<br />
                      자회사 데이터를 포함하지 않으며<br />
                      해당 회사의 데이터만으로 보고서를 발행합니다.
                    </p>
                    <div className="rbm-card-recommend">
                      <span className="rbm-card-recommend-label">이런 경우 선택하세요</span>
                      <span className="rbm-card-recommend-item">본사만 보고서를 작성하는 경우</span>
                    </div>
                  </div>
                </div>
                <div className="rbm-card-radio">
                  <span className={`rbm-radio-circle ${selected === "ENTITY" ? "rbm-radio-circle--on" : ""}`} />
                </div>
              </button>

              <button
                type="button"
                className={`rbm-card ${selected === "CONSOLIDATED" ? "rbm-card--selected" : ""}`}
                onClick={() => setSelected("CONSOLIDATED")}
                aria-pressed={selected === "CONSOLIDATED"}
              >
                <div className="rbm-card-badge rbm-card-badge--blue">그룹 전체</div>
                <div className="rbm-card-body">
                  <div className="rbm-card-illust">
                    <img
                      src={consolidatedCardImg}
                      alt="연결기준 CONSOLIDATED 일러스트"
                      width={132}
                      height={132}
                      style={{ width: 132, height: 132, objectFit: "contain" }}
                    />
                  </div>
                  <div className="rbm-card-info">
                    <h3 className="rbm-card-title">연결기준 (CONSOLIDATED)</h3>
                    <p className="rbm-card-text">
                      본사와 자회사를 연결하여 보고서를 작성합니다.<br />
                      자회사 데이터를 수집하고, 연결하여<br />
                      그룹 전체 보고서를 발행합니다.
                    </p>
                    <div className="rbm-card-recommend">
                      <span className="rbm-card-recommend-label">이런 경우 선택하세요</span>
                      <span className="rbm-card-recommend-item">본사와 자회사를 포함한 그룹 보고가 필요한 경우</span>
                    </div>
                  </div>
                </div>
                <div className="rbm-card-radio">
                  <span className={`rbm-radio-circle ${selected === "CONSOLIDATED" ? "rbm-radio-circle--on" : ""}`} />
                </div>
              </button>
            </div>
            )}

            {error && <div className="rbm-error">{error}</div>}

            {workflowStatus === "NO_RUN" && (
              <div className="rbm-footer">
                <button type="button" className="rbm-btn-cancel" onClick={onClose}>취소</button>
              </div>
            )}
          </div>
        </div>

        {workflowStatus === "NO_RUN" && (
          <div className="rbm-side">
            <h3 className="rbm-side-heading">발행 기준 안내</h3>
          <p className="rbm-side-desc">
            지속가능경영보고서를 작성할 때<br />
            데이터 수집 범위와 연결 방식을<br />
            선택하는 기준입니다.
          </p>

          <div className="rbm-side-section">
            <h4 className="rbm-side-label rbm-side-label--entity">독립기준 (ENTITY)</h4>
            <ul className="rbm-side-list">
              <li>
                <img src={entityReportIcon} alt="본사 단독 보고" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>본사 단독 보고</span>
              </li>
              <li>
                <img src={entityNoSubsidiaryIcon} alt="자회사 데이터 미포함" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>자회사 데이터 미포함</span>
              </li>
              <li>
                <img src={entitySingleCompanyIcon} alt="단일 회사 기준으로 작성" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>단일 회사 기준으로 작성</span>
              </li>
            </ul>
          </div>

          <div className="rbm-side-section">
            <h4 className="rbm-side-label rbm-side-label--consolidated">연결기준 (CONSOLIDATED)</h4>
            <ul className="rbm-side-list">
              <li>
                <img src={consolidatedGroupIcon} alt="지주사와 선택 자회사 포함" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>지주사와 선택 자회사 포함</span>
              </li>
              <li>
                <img src={consolidatedDataSyncIcon} alt="자회사 데이터 요청 수집 및 연결" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>자회사 데이터 요청·수집 및 연결</span>
              </li>
              <li>
                <img src={consolidatedReportIcon} alt="그룹 전체 기준 작성" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>그룹 전체 기준 작성</span>
              </li>
            </ul>
          </div>

          <div className="rbm-side-tip">
            <strong>선택 전 고려사항</strong>
            <ul>
              <li>자회사 데이터 수집 가능 여부</li>
              <li>내부 보고 체계 및 규제 요구사항</li>
            </ul>
          </div>
        </div>
        )}
      </div>

      <div className="rbm-process-bar" style={{ maxWidth: workflowStatus === "NO_RUN" ? "1040px" : "640px", animation: "rbmModalFloatUp 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) forwards" }}>
        <div className="rbm-process-inner" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {workflowStatus === null ? (
            <div key="process-null" className="rbm-process-actions" style={{ justifyContent: "center", animation: "rbmFadeIn 0.3s ease-out" }}>
              <button
                type="button"
                className="rbm-btn-confirm rbm-btn-confirm--loading"
                disabled={true}
              >
                조회 중...
              </button>
            </div>
          ) : workflowStatus === "EXISTS" ? (
            <div key="process-exists" className="rbm-process-actions" style={{ justifyContent: "center", animation: "rbmFadeIn 0.3s ease-out" }}>
              <button
                type="button"
                className={`rbm-btn-confirm ${loading ? "rbm-btn-confirm--loading" : ""}`}
                onClick={handleConfirm}
                disabled={loading}
              >
                {loading ? "조회 중..." : "해당 연도로 이동하기"}
              </button>
            </div>
          ) : (
            <div key="process-norun" style={{ animation: "rbmFadeIn 0.3s ease-out", width: "100%" }}>
              <h4 className="rbm-process-title">선택 후 진행 과정</h4>
              <div className="rbm-steps">
                {steps.map((step, idx) => (
                  <div key={step.label} className="rbm-step-group">
                    <div className={`rbm-step ${isStepActive(idx) ? "rbm-step--active" : ""}`}>
                      <div className="rbm-step-img-wrap">
                        <img src={step.img} alt={step.label} className="rbm-step-img" />
                      </div>
                      <span className="rbm-step-num">{idx + 1}. {step.label}</span>
                      <span className="rbm-step-sub">{step.sub}</span>
                    </div>
                    {idx < steps.length - 1 && (
                      <span className="rbm-step-arrow">→</span>
                    )}
                  </div>
                ))}
              </div>

              {selected && (
                <div className="rbm-process-actions">
                  <button
                    type="button"
                    className={`rbm-btn-confirm ${loading ? "rbm-btn-confirm--loading" : ""}`}
                    onClick={handleConfirm}
                    disabled={!selected || loading}
                  >
                    {loading
                      ? "시작하는 중..."
                      : selected === "ENTITY"
                        ? "독립기준으로 시작하기"
                        : "연결기준으로 시작하기"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ReportBasisSelectModal;