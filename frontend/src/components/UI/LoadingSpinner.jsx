/**
 * LoadingSpinner.jsx
 * 레이어: Component (UI)
 * 역할: 테이블/목록 영역의 데이터 로딩 상태를 표시하는 스피너.
 * Props: message {string} — 스피너 하단 안내 문구
 */
const LoadingSpinner = ({ message }) => (
  <div className="loading-container">
    <div className="spinner" />
    <p>{message}</p>
  </div>
);

export default LoadingSpinner;
