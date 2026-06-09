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
        <p className="login-visual-kicker">Unified ESG Platform</p>

        <h2 className="login-visual-title">
          지속가능경영 데이터를
          <br />
          하나의 플랫폼에서.
        </h2>

        <p className="login-visual-description">
          지표 입력부터 증빙 수집, 승인 워크플로우까지
          <br />
          ESG 보고 과정을 체계적으로 관리하세요.
        </p>

        <div className="login-visual-chip-list">
          <div className="login-visual-chip">보고서 AI 자동 발간</div>
          <div className="login-visual-chip">탄소관리 자동화 AI</div>
          <div className="login-visual-chip">공급망 데이터 AI 통합 관리</div>
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