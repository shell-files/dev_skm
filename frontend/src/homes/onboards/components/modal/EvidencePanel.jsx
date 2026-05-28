import React, { useRef } from 'react';

export default function EvidencePanel({ subMetrics, atomicFiles, onFileChange }) {
  const fileInputRef = useRef(null);

  // 현재 모달에서 증빙이 필요한 첫 번째 atomic id를 대표로 사용하거나,
  // 여러 증빙을 각각 업로드할 수 있게 매핑. 여기선 간소화하여 리스트 형태로 보여줌.
  
  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && subMetrics && subMetrics.length > 0) {
      // 가장 첫 번째 subMetric에 증빙을 매핑하는 더미 로직 (실제로는 특정 id 지정 필요)
      const targetId = subMetrics[0].atomicMetricId || subMetrics[0].issueId;
      onFileChange(targetId, file);
    }
    e.target.value = null; // reset
  };

  const uploadedFiles = Object.entries(atomicFiles)
    .filter(([_, file]) => file !== null)
    .map(([id, file]) => ({ id, name: file.name }));

  return (
    <div className="ob-side-card">
      <h4>📎 증빙 자료 (Evidence)</h4>
      <input 
        type="file" 
        style={{ display: 'none' }} 
        ref={fileInputRef}
        onChange={handleFileChange}
      />
      <div className="ob-file-upload-btn" onClick={handleUploadClick}>
        + 파일 업로드 또는 링크 추가
      </div>
      
      {uploadedFiles.length > 0 && (
        <div className="ob-evidence-list">
          {uploadedFiles.map(file => (
            <div key={file.id} className="ob-evidence-item">
              <span>{file.name}</span>
              <button type="button" style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#ef4444' }} onClick={() => onFileChange(file.id, null)}>×</button>
            </div>
          ))}
        </div>
      )}
      {uploadedFiles.length === 0 && (
        <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8', textAlign: 'center' }}>
          등록된 증빙 자료가 없습니다.
        </div>
      )}
    </div>
  );
}
