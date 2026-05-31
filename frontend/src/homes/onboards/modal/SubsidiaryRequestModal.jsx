import { useState, useEffect } from "react";
import { listSubsidiaries, saveBatch } from "@/apis/report";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

const SubsidiaryRequestModal = ({ isOpen, onClose, runId, onRequested }) => {
  const [subsidiaries, setSubsidiaries] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSubsidiaries();
    } else {
      setSelectedIds([]);
    }
  }, [isOpen]);

  const loadSubsidiaries = async () => {
    setLoading(true);
    try {
      const res = await listSubsidiaries(runId);
      if (res?.data) {
        const items = res?.data?.items || [];
        setSubsidiaries(items);
        setSelectedIds(items.map(item => item.companyId));
      }
    } catch (e) {
      console.error(e);
      // Fallback mock data 제거
      showDefaultAlert("오류", "자회사 목록을 불러오지 못했습니다.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleRequest = async () => {
    if (selectedIds.length === 0) return;
    setRequesting(true);
    try {
      const res = await saveBatch({
        runId,
        sourceCompanyIds: selectedIds
      });
      if (res?.status) {
        onRequested?.(res.data);
        onClose();
      } else {
        showDefaultAlert("오류", "요청에 실패했습니다.", "error");
      }
    } catch (e) {
      console.error(e);
      // mock success 제거
      showDefaultAlert("오류", "데이터 요청 중 오류가 발생했습니다.", "error");
    } finally {
      setRequesting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ob1-modal-overlay">
      <div className="ob1-modal-content" style={{ width: 480 }}>
        <div className="ob1-modal-header">
          <h2>G0 데이터 요청 자회사 선택</h2>
          <button className="ob1-btn-close" onClick={onClose}>✕</button>
        </div>
        <div className="ob1-modal-body">
          <p style={{ marginBottom: 16, fontSize: '0.9rem', color: '#475569' }}>
            데이터를 수집할 자회사를 선택해 주세요.
          </p>
          
          {loading ? (
            <div>불러오는 중...</div>
          ) : (
            <ul className="sub-list" style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {subsidiaries.map(sub => (
                <li key={sub.companyId} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', flex: 1 }}>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(sub.companyId)}
                      onChange={() => handleToggle(sub.companyId)}
                    />
                    <span style={{ fontWeight: 500 }}>{sub.companyName} ({sub.companyCode})</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="ob1-modal-footer" style={{ borderTop: '1px solid #e2e8f0', padding: '16px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button style={{ padding: '8px 16px', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '4px' }} onClick={onClose}>취소</button>
          <button 
            style={{ padding: '8px 16px', background: '#1d4ed8', color: '#fff', border: 'none', borderRadius: '4px', cursor: selectedIds.length ? 'pointer' : 'not-allowed', opacity: selectedIds.length ? 1 : 0.5 }}
            onClick={handleRequest}
            disabled={!selectedIds.length || requesting}
          >
            {requesting ? '요청 중...' : '요청 보내기'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubsidiaryRequestModal;
