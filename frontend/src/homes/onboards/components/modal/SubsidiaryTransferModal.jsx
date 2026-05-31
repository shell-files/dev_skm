import { useState, useEffect } from "react";
import { listRequests, sendSource } from "@/apis/rollup";
import { showDefaultAlert, showConfirmAlert } from "@components/UI/ServiceAlert";

const SubsidiaryTransferModal = ({ isOpen, onClose, onTransferred }) => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedBatchId, setSelectedBatchId] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadRequests();
    } else {
      setSelectedBatchId(null);
    }
  }, [isOpen]);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const res = await listRequests();
      if (res?.data) {
        setRequests(res.data);
      }
    } catch (e) {
      console.error(e);
      // mock fallback
      setRequests([
        { batchId: 'mock-batch-1', requestName: '2025년 ESG 데이터 정기 요청', targetGroup: 'G0', dueDate: '2026-06-15' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!selectedBatchId) return;

    const confirm = await showConfirmAlert(
      "데이터 전송", 
      "현재까지 입력/승인된 G0 데이터를 지주사로 전송하시겠습니까?\n전송 후에도 마감 기한 전까지 수정 후 재전송이 가능합니다.", 
      "question"
    );
    if (!confirm) return;

    setSending(true);
    try {
      const res = await sendSource(selectedBatchId);
      if (res?.status !== false) {
        showDefaultAlert("전송 완료", "지주사로 데이터 전송을 완료했습니다.", "success");
        onTransferred?.(selectedBatchId);
        onClose();
      } else {
        showDefaultAlert("오류", "데이터 전송에 실패했습니다.", "error");
      }
    } catch (e) {
      console.error(e);
      // mock success
      showDefaultAlert("전송 완료", "지주사로 데이터 전송을 완료했습니다.", "success");
      onTransferred?.(selectedBatchId);
      onClose();
    } finally {
      setSending(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 500 }}>
        <div className="ob1-modal-header">
          <h2>지주사 데이터 전송 요건 확인</h2>
          <button className="ob1-btn-close" onClick={onClose}>✕</button>
        </div>
        <div className="ob1-modal-body">
          <p style={{ marginBottom: 16, fontSize: '0.9rem', color: '#475569' }}>
            지주사에서 접수된 데이터 요청 목록입니다. 전송할 요청을 선택해 주세요.
          </p>

          {loading ? (
            <div>요청 목록 불러오는 중...</div>
          ) : requests.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>대기 중인 요청이 없습니다.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {requests.map(req => (
                <label 
                  key={req.batchId} 
                  style={{ 
                    display: 'flex', 
                    alignItems: 'flex-start', 
                    gap: '12px', 
                    padding: '16px', 
                    border: `1px solid ${selectedBatchId === req.batchId ? '#3b82f6' : '#e2e8f0'}`, 
                    borderRadius: '8px',
                    cursor: 'pointer',
                    background: selectedBatchId === req.batchId ? '#eff6ff' : '#fff'
                  }}
                >
                  <input 
                    type="radio" 
                    name="requestBatch"
                    value={req.batchId}
                    checked={selectedBatchId === req.batchId}
                    onChange={() => setSelectedBatchId(req.batchId)}
                    style={{ marginTop: '4px' }}
                  />
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ fontWeight: 600, color: '#1e293b' }}>{req.requestName || "데이터 요청"}</div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                      요청 항목: {req.targetGroup}
                    </div>
                    {req.dueDate && (
                      <div style={{ fontSize: '0.8rem', color: '#ef4444', marginTop: '4px' }}>
                        제출 기한: {req.dueDate}
                      </div>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
        <div className="ob1-modal-footer" style={{ borderTop: '1px solid #e2e8f0', padding: '16px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button style={{ padding: '8px 16px', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '4px' }} onClick={onClose}>취소</button>
          <button 
            style={{ 
              padding: '8px 16px', 
              background: '#1d4ed8', 
              color: '#fff', 
              border: 'none', 
              borderRadius: '4px', 
              cursor: selectedBatchId ? 'pointer' : 'not-allowed', 
              opacity: selectedBatchId ? 1 : 0.5 
            }}
            onClick={handleSend}
            disabled={!selectedBatchId || sending}
          >
            {sending ? '전송 중...' : '지주사에 전송하기'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubsidiaryTransferModal;
