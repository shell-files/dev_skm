import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import '@styles/onboardingModal.css';

export default function TextEditorModal({ isOpen, onClose, initialValue, title, onSave }) {
  const [value, setValue] = useState(initialValue || '');

  useEffect(() => {
    if (isOpen) {
      setValue(initialValue || '');
    }
  }, [isOpen, initialValue]);

  if (!isOpen) return null;

  return createPortal(
    <div className="ob-modal-overlay" style={{ zIndex: 10000 }}>
      <div className="ob-modal-shell" style={{ maxWidth: '800px', height: '600px', display: 'flex', flexDirection: 'column' }}>
        <div className="ob-modal-header" style={{ borderBottom: '1px solid #e2e8f0', padding: '20px 32px' }}>
          <h2 className="ob-modal-title" style={{ fontSize: '1.2rem', margin: 0 }}>
            {title || '정성 데이터 작성'}
          </h2>
        </div>
        
        <div style={{ flex: 1, padding: '24px 32px', background: '#f8fafc', display: 'flex', flexDirection: 'column' }}>
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="상세 내용을 입력해주세요."
            style={{ 
              flex: 1, 
              width: '100%', 
              padding: '16px', 
              border: '1px solid #cbd5e1', 
              borderRadius: '8px', 
              fontSize: '0.95rem', 
              lineHeight: '1.6', 
              resize: 'none',
              outline: 'none',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
            }}
          />
        </div>

        <div className="ob-modal-footer" style={{ padding: '20px 32px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button type="button" className="ob-btn ob-btn-secondary" onClick={onClose}>
            취소
          </button>
          <button 
            type="button" 
            className="ob-btn ob-btn-primary" 
            onClick={() => {
              onSave(value);
              onClose();
            }}
          >
            저장
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
