import { useEffect, useState } from "react";
import "@styles/loginBackground.css";

import gateBg1 from "@assets/images/backgrounds/GateBg1.png";
import gateBg2 from "@assets/images/backgrounds/GateBg2.png";
import gateBg3 from "@assets/images/backgrounds/GateBg3.png";

import blobMain from "@assets/images/backgrounds/login-blob-main.png";
import floatingOrb from "@assets/images/backgrounds/login-floating-orb.png";

/**
 * LoginBackground
 *
 * 역할:
 * - 로그인 페이지 및 다른 페이지에서 재사용 가능한 전체 배경 wrapper
 * - glow, 3D object, node, line 등 장식 요소를 한 컴포넌트로 분리
 * - children을 받아 실제 페이지 콘텐츠를 배경 위에 렌더링
 */
const LoginBackground = ({ children, className = "" }) => {
  const [isReady, setIsReady] = useState(false);

  // 초기 렌더링 시 레이아웃 시프트 방지 및 등장 애니메이션 제어
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setIsReady(true);
      });
    });

    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div
      className={`login-page-shell ${
        isReady ? "is-ready" : "is-initializing"
      } ${className}`}
    >
      {/* 배경 장식 레이어 */}
      <div className="login-page-decor" aria-hidden="true">
        {/* Glow Effects */}
        <div className="login-page-glow login-glow-1" />
        <div className="login-page-glow login-glow-2" />

        {/* 3D Objects */}
        <img
          className="login-page-decor-object decor-object-1"
          src={gateBg1}
          width="100"
          height="100"
          alt=""
        />
        <img
          className="login-page-decor-object decor-object-2"
          src={gateBg2}
          width="160"
          height="160"
          alt=""
        />
        <img
          className="login-page-decor-object decor-object-3"
          src={gateBg3}
          width="70"
          height="70"
          alt=""
        />

        <img
          className="login-page-decor-object generated-bg-1"
          src={blobMain}
          width="600"
          height="600"
          alt=""
        />
        <img
          className="login-page-decor-object generated-bg-3"
          src={floatingOrb}
          width="200"
          height="200"
          alt=""
        />

        {/* Decorative Nodes */}
        <div className="login-page-node node-bg-1" style={{ top: "15%", left: "10%" }} />
        <div className="login-page-node node-bg-2" style={{ top: "45%", right: "15%" }} />
        <div className="login-page-node node-bg-3" style={{ bottom: "25%", left: "20%" }} />
        <div className="login-page-node node-bg-4" style={{ bottom: "15%", right: "10%", opacity: 0.2 }} />
        <div className="login-page-node node-bg-5" style={{ bottom: "30%", right: "5%", opacity: 0.15 }} />

        {/* Decorative Shapes & Lines */}
        <div className="login-page-shape shape-circle-1" />
        <div className="login-page-shape shape-square-1" />

        <img
          className="login-page-decor-object generated-bg-4"
          src={floatingOrb}
          width="200"
          height="200"
          style={{
            bottom: "5%",
            right: "5%",
            opacity: 0.5,
            filter: "blur(40px)",
          }}
          alt=""
        />

        <div
          className="login-page-node node-bg-6"
          style={{
            bottom: "15%",
            right: "12%",
            width: "12px",
            height: "12px",
            background: "rgba(3, 169, 77, 0.4)",
          }}
        />
        <div
          className="login-page-node node-bg-7"
          style={{
            bottom: "25%",
            right: "8%",
            width: "8px",
            height: "8px",
            background: "rgba(3, 169, 77, 0.3)",
          }}
        />

        <div className="login-page-line login-page-line-1" />
        <div className="login-page-line login-page-line-2" />
        <div className="login-page-line login-page-line-3" />
      </div>

      {children}
    </div>
  );
};

export default LoginBackground;