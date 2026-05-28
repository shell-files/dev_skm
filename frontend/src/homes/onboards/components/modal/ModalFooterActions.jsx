import React from 'react';

export default function ModalFooterActions({ onClose, onSaveDraft, onSubmit }) {
  return (
    <div className="ob-modal-footer">
      <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>
        취소
      </button>
      <button type="button" className="ob-btn ob-btn-secondary" onClick={onSaveDraft}>
        임시저장
      </button>
      <button type="button" className="ob-btn ob-btn-primary" onClick={onSubmit}>
        데이터 최종 제출
      </button>
    </div>
  );
}
