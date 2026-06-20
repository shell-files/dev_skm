/**
 * ModalWrapper.jsx
 * 레이어: Component (UI)
 * 역할: modal-overlay/modal-window/modal-header/modal-body/modal-footer 구조를 캡슐화한 공통 모달 래퍼.
 *
 * Props:
 *   title    {string}    — 모달 헤더 타이틀
 *   onClose  {Function}  — 닫기 핸들러 (overlay 클릭·X 버튼 공통)
 *   children {ReactNode} — modal-body에 렌더링할 내용
 *   footer   {ReactNode} — modal-footer에 렌더링할 내용 (선택)
 *   maxWidth {string}    — modal-window 최대 너비 (기본 540px)
 */
const ModalWrapper = ({ title, onClose, children, footer, maxWidth = "540px" }) => (
  <div className="modal-overlay" onClick={onClose}>
    <div
      className="modal-window"
      style={{ maxWidth, maxHeight: "90vh", overflow: "auto" }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="modal-header">
        <h3>{title}</h3>
        <button
          type="button"
          className="close-x"
          aria-label="닫기"
          onClick={onClose}
          style={{ border: "none", background: "none", fontSize: "20px", cursor: "pointer" }}
        >
          ×
        </button>
      </div>
      <div className="modal-body">{children}</div>
      {footer && <div className="modal-footer">{footer}</div>}
    </div>
  </div>
);

export default ModalWrapper;
