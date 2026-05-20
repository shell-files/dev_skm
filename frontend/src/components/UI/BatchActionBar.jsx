import React from 'react';
import "@styles/BatchActionBar.css";

/**
 * BatchActionBar.jsx
 * 
 * 다중 선택 시 나타나는 일괄 처리 툴바 컴포넌트입니다.
 * 
 * Props:
 * - selectedCount: 선택된 항목 수
 * - actions: 실행할 액션들의 배열
 *   [{ label: '저장', onClick: fn, className: 'save' }, ...]
 */
const BatchActionBar = ({ selectedCount, actions = [] }) => {
  if (selectedCount === 0) return null;

  return (
    <div className="ob-batch-toolbar">
      <span className="ob-batch-count">
        <strong>{selectedCount}</strong>건 선택됨
      </span>
      <div className="ob-batch-btns">
        {actions.map((action, idx) => (
          <button
            key={idx}
            type="button"
            className={`ob-batch-btn ${action.className || ""}`}
            onClick={action.onClick}
            disabled={action.disabled}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default BatchActionBar;
