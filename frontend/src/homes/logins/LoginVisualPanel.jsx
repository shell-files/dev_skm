import "@styles/loginBackground.css";

import gateBg1 from "@assets/images/backgrounds/GateBg1.png";
import gateBg2 from "@assets/images/backgrounds/GateBg2.png";
import gateBg3 from "@assets/images/backgrounds/GateBg3.png";

/**
 * LoginVisualPanel
 *
 * 역할:
 * - 로그인 카드 왼쪽 ESG 소개 영역
 * - 전체 페이지 배경이 아니라 카드 내부 visual panel
 */
const LoginVisualPanel = () => {
  return (
    <aside className="login-background" aria-hidden="true">
      <div className="login-visual-content">
        <p className="login-visual-kicker">ESG Materiality Platform</p>

        <h2 className="login-visual-title">
          ESG 이중 중대성 평가를
          <br />
          하나의 플랫폼에서.
        </h2>

        <p className="login-visual-description">
          벤치마킹·미디어 분석·이해관계자 설문을 통해
          <br />
          중대성 이슈를 체계적으로 선정하고,
          <br />
          AI가 ESG 보고서 초안을 자동으로 완성합니다.
        </p>

        <div className="login-visual-chip-list">
          <div className="login-visual-chip">벤치마킹 분석</div>
          <div className="login-visual-chip">미디어 분석</div>
          <div className="login-visual-chip">이해관계자 설문</div>
          <div className="login-visual-chip">이중 중대성 매트릭스</div>
          <div className="login-visual-chip">AI 보고서 초안 생성</div>
        </div>
      </div>

      {/* 데이터 흐름 시각화 요소 */}
      <div className="login-visual-assets">
        <div className="data-flow-node node-1" />
        <div className="data-flow-node node-2" />
        <div className="data-flow-node node-3" />
        <div className="data-flow-node node-4" />
        <div className="data-flow-line line-1" />

        <img
          className="login-visual-object login-visual-object-main"
          src={gateBg1}
          alt=""
        />
        <img
          className="login-visual-object login-visual-object-sub-1"
          src={gateBg2}
          alt=""
        />
        <img
          className="login-visual-object login-visual-object-sub-2"
          src={gateBg3}
          alt=""
        />
      </div>
    </aside>
  );
};

export default LoginVisualPanel;