import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router";
import "@styles/reportBasisSelectModal.css";
import { DEFAULT_REPORTING_YEAR, startWorkflow, getCurrent, resumeWorkflow } from "@/apis/report";

// ── Illustrations (카드 대표 일러스트 132×132)
import entityCardImg from "@assets/reportbasis/illustrations/entity-card.png";
import consolidatedCardImg from "@assets/reportbasis/illustrations/consolidated-card.png";

// ── Icons (우측 설명 패널 34×34)
import entityReportIcon from "@assets/reportbasis/icons/entity-report.png";
import entityNoSubsidiaryIcon from "@assets/reportbasis/icons/entity-no-subsidiary.png";
import entitySingleCompanyIcon from "@assets/reportbasis/icons/entity-single-company.png";
import consolidatedGroupIcon from "@assets/reportbasis/icons/consolidated-group.png";
import consolidatedDataSyncIcon from "@assets/reportbasis/icons/consolidated-data-sync.png";
import consolidatedReportIcon from "@assets/reportbasis/icons/consolidated-report.png";

// ── Steps (하단 프로세스)
import stepBasisImg from "@assets/reportbasis/steps/step-basis.png";
import stepG0Img from "@assets/reportbasis/steps/step-g0.png";
import stepSubsidiaryTransferImg from "@assets/reportbasis/steps/step-subsidiary-transfer.png";
import stepRollupImg from "@assets/reportbasis/steps/step-rollup.png";
import stepDmaImg from "@assets/reportbasis/steps/step-dma.png";
import stepOnboardingImg from "@assets/reportbasis/steps/step-onboarding.png";
import stepReportImg from "@assets/reportbasis/steps/step-report.png";

// ── Entity 선택 시 프로세스 (5단계)
const ENTITY_STEPS = [
  { img: stepBasisImg,    label: "기준 선택",       sub: "보고서 발행 기준 결정" },
  { img: stepG0Img,       label: "G0 입력·승인",    sub: "G0 지표 입력 및 승인" },
  { img: stepDmaImg,      label: "이중중대성평가",   sub: "DMA 평가 수행" },
  { img: stepOnboardingImg, label: "선정 지표 입력·승인", sub: "확정 지표 입력 및 승인" },
  { img: stepReportImg,   label: "보고서 생성",      sub: "최종 보고서 작성 및 발행" },
];

// ── Consolidated 선택 시 프로세스 (7단계)
const CONSOLIDATED_STEPS = [
  { img: stepBasisImg,              label: "기준 선택",           sub: "보고서 발행 기준 결정" },
  { img: stepG0Img,                 label: "본사 G0 입력·승인",   sub: "G0 지표 입력 및 승인" },
  { img: stepSubsidiaryTransferImg, label: "자회사 G0 요청·전송", sub: "자회사 데이터 요청 및 수집" },
  { img: stepRollupImg,             label: "G0 연결 롤업",        sub: "데이터 연결 및 결과 확인" },
  { img: stepDmaImg,                label: "이중중대성평가",       sub: "DMA 평가 수행" },
  { img: stepOnboardingImg,         label: "선정 지표 수집·롤업", sub: "확정 지표 수집 및 롤업" },
  { img: stepReportImg,             label: "보고서 생성",          sub: "최종 보고서 작성 및 발행" },
];

const ReportBasisSelectModal = ({
  isOpen,
  onClose,
  companyId,
  reportingYear = DEFAULT_REPORTING_YEAR
}) => {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null); // null | 'ENTITY' | 'CONSOLIDATED'
  const [selectedYear, setSelectedYear] = useState(reportingYear);
  const [workflowStatus, setWorkflowStatus] = useState(null); // 'NO_RUN' | 'EXISTS'
  const [currentRunId, setCurrentRunId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setSelectedYear(reportingYear);
    setSelected(null);
    setWorkflowStatus(null);
    setCurrentRunId(null);
    setError(null);
  }, [isOpen, companyId, reportingYear]);

  useEffect(() => {
    if (!isOpen || !companyId) return;

    let isMounted = true;
    const fetchCurrent = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getCurrent(companyId, selectedYear);
        if (isMounted) {
          if (res?.status === false || res?.success === false || !res?.data) {
             setError(res?.error?.message || "워크플로우 조회 실패");
          } else if (res?.data?.workflowStep === 'NO_RUN') {
             setWorkflowStatus('NO_RUN');
             setCurrentRunId(null);
          } else {
             setWorkflowStatus('EXISTS');
             setCurrentRunId(res?.data?.runId ?? null);
          }
        }
      } catch (err) {
        if (isMounted) setError("워크플로우 조회 중 오류 발생");
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchCurrent();
    
    return () => { isMounted = false; };
  }, [isOpen, companyId, selectedYear]);

  if (!isOpen) return null;

  const steps = selected === "ENTITY"
    ? ENTITY_STEPS
    : selected === "CONSOLIDATED"
    ? CONSOLIDATED_STEPS
    : [];

  const handleConfirm = async () => {
    if (loading) return;
    
    if (workflowStatus === 'EXISTS') {
      if (!currentRunId) {
        setError("현재 선택 연도의 실행 정보를 찾을 수 없습니다.");
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const res = await resumeWorkflow(currentRunId);
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

      onClose?.();
      navigate(`/onb?reportingYear=${selectedYear}`, {
        replace: true,
        state: {
          workflowStartedAt: Date.now(),
        },
      });
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
      const res = await startWorkflow({
        companyId,
        reportingYear: selectedYear,
        reportBasisType: selected
      });

      const isFailed = res?.status === false || res?.success === false || !res?.data;
      if (isFailed) {
        setError(res?.error?.message || "워크플로우 시작에 실패했습니다.");
        setLoading(false);
        return;
      }

      // 성공 → /onb 이동
      onClose?.();
      navigate(`/onb?reportingYear=${selectedYear}`, {
        replace: true,
        state: {
          workflowStartedAt: Date.now(),
        },
      });
    } catch (err) {
      console.error("[ReportBasisSelectModal] startWorkflow error:", err);
      setError("워크플로우 시작 중 오류가 발생했습니다.");
      setLoading(false);
    }
  };

  return createPortal(
    <div className="rbm-overlay" role="dialog" aria-modal="true" aria-labelledby="rbm-title">
      <div className="rbm-layout">
        {/* ── 좌측: 메인 모달 ── */}
        <div className="rbm-main">
          {/* 헤더 */}
          <div className="rbm-header">
            <button className="rbm-close" onClick={onClose} aria-label="닫기">✕</button>
            <h2 id="rbm-title" className="rbm-title">보고서 프로젝트 선택</h2>
            <p className="rbm-desc">지속가능경영보고서를 작성할 연도와 기준을 선택해 주세요.</p>
            
            <div className="rbm-year-select-wrapper" style={{ marginTop: '16px', marginBottom: '8px' }}>
              <label htmlFor="reportingYearSelect" style={{ fontWeight: 'bold', marginRight: '12px' }}>보고연도:</label>
              <select 
                id="reportingYearSelect"
                value={selectedYear} 
                onChange={(e) => {
                  setSelectedYear(Number(e.target.value));
                  setSelected(null);
                  setWorkflowStatus(null);
                  setCurrentRunId(null);
                  setError(null);
                }}
                style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                <option value={2024}>2024</option>
                <option value={2025}>2025</option>
                <option value={2026}>2026</option>
                <option value={2027}>2027</option>
              </select>
            </div>

            {workflowStatus !== 'EXISTS' && (
              <div className="rbm-banner">
                <span className="rbm-banner-icon">💡</span>
                발행 기준에 따라 보고 범위, 데이터 수집 방식, 보고 절차가 달라집니다.
              </div>
            )}
          </div>

          {/* 카드 선택 영역 */}
          {workflowStatus === 'EXISTS' ? (
            <div className="rbm-exists-message" style={{ padding: '40px 20px', textAlign: 'center', background: '#f8fafc', borderRadius: '8px', margin: '20px 0' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#1e293b' }}>이미 생성된 {selectedYear}년 보고서 프로젝트가 있습니다.</h3>
              <p style={{ color: '#64748b' }}>아래 [해당 연도로 이동하기] 버튼을 눌러 프로젝트를 계속 진행하세요.</p>
            </div>
          ) : (
            <div className="rbm-cards">
              {/* ENTITY 카드 */}
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
                      자회사 데이터를 포함하지 않으며,<br />
                      해당 회사의 데이터만으로 보고서를 발행합니다.
                    </p>
                    <div className="rbm-card-recommend">
                      <span className="rbm-card-recommend-label">이런 경우 선택하세요</span>
                      <span className="rbm-card-recommend-item">✓ 본사만 보고서를 작성하는 경우</span>
                    </div>
                  </div>
                </div>
                <div className="rbm-card-radio">
                  <span className={`rbm-radio-circle ${selected === "ENTITY" ? "rbm-radio-circle--on" : ""}`} />
                </div>
              </button>

              {/* CONSOLIDATED 카드 */}
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
                      자회사 데이터를 수집하고, 연결(롤업)하여<br />
                      그룹 전체의 보고서를 발행합니다.
                    </p>
                    <div className="rbm-card-recommend">
                      <span className="rbm-card-recommend-label">이런 경우 선택하세요</span>
                      <span className="rbm-card-recommend-item">✓ 본사만 자회사를 포함한 그룹 보고가 필요한 경우</span>
                    </div>
                  </div>
                </div>
                <div className="rbm-card-radio">
                  <span className={`rbm-radio-circle ${selected === "CONSOLIDATED" ? "rbm-radio-circle--on" : ""}`} />
                </div>
              </button>
            </div>
          )}

          {/* 에러 표시 */}
          {error && (
            <div className="rbm-error">{error}</div>
          )}

          {/* 하단 액션 */}
          {workflowStatus !== 'EXISTS' && (
            <div className="rbm-footer">
              <button type="button" className="rbm-btn-cancel" onClick={onClose}>취소</button>
              <div className="rbm-footer-info">
                <span className="rbm-info-icon">ⓘ</span>
                발행 기준 설정은 보고서 작성 시작 전 언제든 변경할 수 있습니다.
                <button type="button" className="rbm-link">자세히 알아보기 &rsaquo;</button>
              </div>
            </div>
          )}
        </div>

        {/* ── 우측: 발행 기준 설명 패널 ── */}
        <div className="rbm-side">
          <h3 className="rbm-side-heading">발행 기준이란?</h3>
          <p className="rbm-side-desc">
            지속가능경영보고서를 작성할 때,<br />
            데이터 수집 범위와 연결 방식에 대해<br />
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
                <img src={consolidatedGroupIcon} alt="지주사 + 선택 자회사 포함" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>지주사 + 선택 자회사 포함</span>
              </li>
              <li>
                <img src={consolidatedDataSyncIcon} alt="자회사 데이터 요청·수집 및 연결" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>자회사 데이터 요청·수집 및 연결</span>
              </li>
              <li>
                <img src={consolidatedReportIcon} alt="그룹 전체 기준 작성" width={34} height={34} style={{ width: 34, height: 34, objectFit: "contain" }} />
                <span>그룹 전체 기준 작성</span>
              </li>
            </ul>
          </div>

          <div className="rbm-side-tip">
            <span className="rbm-side-tip-icon">💡</span>
            <strong>선택 시 고려사항</strong>
            <ul>
              <li>보고 범위 (단일 회사 vs 그룹 전체)</li>
              <li>자회사 데이터 수집 가능 여부</li>
              <li>내부 보고 체계 및 외부 규제 요구사항</li>
              <li>향후 변경 가능 (보고서 작성 전까지)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* ── 하단: 선택 후 진행 과정 ── */}
      <div className="rbm-process-bar">
        <div className="rbm-process-inner">
          {workflowStatus === 'EXISTS' ? (
            <div className="rbm-process-actions" style={{ justifyContent: 'center' }}>
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
            <>
              <h4 className="rbm-process-title">선택 후 진행 과정</h4>
              {selected ? (
            <div className="rbm-steps">
              {steps.map((step, idx) => (
                <div key={step.label} className="rbm-step-group">
                  <div className={`rbm-step ${idx === 0 ? "rbm-step--active" : ""}`}>
                    <div className="rbm-step-img-wrap">
                      <img
                        src={step.img}
                        alt={step.label}
                        className="rbm-step-img"
                      />
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
          ) : (
            <p className="rbm-process-placeholder">발행 기준을 선택하면 진행 과정이 표시됩니다.</p>
          )}

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
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ReportBasisSelectModal;
