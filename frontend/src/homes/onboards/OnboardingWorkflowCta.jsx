/**
 * OnboardingWorkflowCta.jsx
 * 레이어: Component (onboards)
 * 역할: 온보딩 워크플로우 단계(nextAction)에 따라 CTA 버튼 텍스트·활성화 여부를 동적으로 렌더링하는 컴포넌트
 *
 * Props:
 *   variant — "action" (헤더용 버튼) 또는 "noRun" (NO_RUN 상태 안내 카드)
 *   loadingWorkflow — 워크플로우 로딩 여부
 *   workflow — 현재 워크플로우 객체 (nextAction 포함)
 *   isNoRunWorkflow — 워크플로우가 NO_RUN인지 판별하는 함수
 *   onBasisModalOpen — 보고서 발행 기준 선택 모달 열기 핸들러
 *   onCtaClick — CTA 버튼 클릭 핸들러
 */
const OnboardingWorkflowCta = ({
  loadingWorkflow,
  variant = "action",
  workflow,
  isNoRunWorkflow,
  onBasisModalOpen,
  onCtaClick,
}) => {
  const isWaitingRollup = workflow?.nextAction === "WAIT_ROLLUP";

  if (variant === "noRun" || isNoRunWorkflow(workflow)) {
    return (
      <>
        <div className="ob1-empty-state">
          <p className="ob1-empty-title">보고서 발행 기준 선택이 필요합니다.</p>
          <p className="ob1-empty-desc">
            보고서 워크플로우를 생성해 주세요.
          </p>
          <button type="button" className="ob1-btn-cta" onClick={onBasisModalOpen}>
            보고서 발행 기준 선택
          </button>
        </div>
        <div className="ob1-cta-container">
          <button className="ob1-btn-cta" onClick={onCtaClick} disabled={loadingWorkflow}>
            {loadingWorkflow ? "로딩 중..." : "발행 기준 선택"}
          </button>
        </div>
      </>
    );
  }

  return (
    <div className="ob1-cta-container">
      <button
        className="ob1-btn-cta"
        onClick={isWaitingRollup ? undefined : onCtaClick}
        disabled={loadingWorkflow || isWaitingRollup}
      >
        {loadingWorkflow
          ? "로딩 중..."
          : !workflow
            ? "워크플로우 상태 확인 필요"
            : workflow.nextAction === "START_DMA"
              ? "이중중대성평가 진행하기"
              : workflow.nextAction === "REQUEST_ROLLUP"
                ? "자회사 데이터 요청하기"
                : workflow.nextAction === "WAIT_ROLLUP"
                  ? "자회사 데이터 대기"
                  : "입력 상태 확인"}
      </button>
    </div>
  );
};

export default OnboardingWorkflowCta;
