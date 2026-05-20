import React, { useState, useEffect } from 'react';
import '@styles/onboarding.css';

export default function DataInputModal({
  isOpen,
  onClose,
  metricItem,
  subMetrics,
  onSaveAndSubmit
}) {
  const [includeReport, setIncludeReport] = useState(true);
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});

  useEffect(() => {
    if (!metricItem || !subMetrics) return;

    const initialValues = {};
    const initialFiles = {};

    subMetrics.forEach(sub => {
      initialValues[sub.issueId] = sub.value || '';
      initialFiles[sub.issueId] =
        sub.evidenceFileName
          ? { name: sub.evidenceFileName }
          : null;
    });

    setAtomicValues(initialValues);
    setAtomicFiles(initialFiles);
  }, [metricItem, subMetrics]);

  const handleInputChange = (issueId, value) => {
    setAtomicValues(prev => ({
      ...prev,
      [issueId]: value
    }));
  };

  const handleFileChange = (issueId, e) => {
    const file = e.target.files[0];
    if (file) {
      setAtomicFiles(prev => ({
        ...prev,
        [issueId]: file
      }));
    }
  };

  const handleSubmitSequence = () => {
    if (typeof onSaveAndSubmit === 'function') {
      onSaveAndSubmit(atomicValues, atomicFiles);
    }
  };

  if (!isOpen || !metricItem || !subMetrics) return null;

  return (
    // 🔴 중요: 불필요한 id="onboarding_page" div를 제거했습니다.
    // 기존 css의 display: none을 덮어쓰고 화면 중앙 정렬을 위해 인라인 스타일(flex)을 안전하게 부여합니다.
    <div 
      className="ob-modal-overlay" 
      id="mixMetricModal" 
      style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }} 
      onClick={onClose}
    >
      {/* 🔴 ob-modal 본체가 정상적으로 감싸지며 css 여백과 둥근 모서리가 살아납니다. */}
      <div className="ob-modal" onClick={(e) => e.stopPropagation()}>
        
        {/* 헤더 섹션 */}
        <div className="ob-modal-header">
          <div>
            <h2 className="ob-modal-title">
              <span className="ob-modal-tag">{metricItem.issueId}</span>
              {metricItem.issueName} 세부 데이터 마스터 명세
            </h2>
          </div>
          <div className="ob-deadline-badge">마감기한: 2026-06-30 까지</div>
        </div>

        {/* 바디 섹션 */}
        <div className="ob-modal-body">
          
          {/* 마스터 정보 요약 박스 */}
          <div className="ob-info-summary-box">
            <div className="ob-info-item">
              <span className="ob-info-label">대표 코드 / Trigger ID</span>
              <span className="ob-info-val">{metricItem.issueId}__E0001</span>
            </div>
            <div className="ob-info-item">
              <span className="ob-info-label">Matrix Code / 입력 수준</span>
              <span className="ob-info-val" style={{ color: '#0284c7' }}>MIX_QL (정성+정량 혼합)</span>
            </div>
            <div className="ob-info-item">
              <span className="ob-info-label">기업 데이터 유형</span>
              <span className="ob-info-val">그룹 원천 입력 데이터</span>
            </div>
          </div>

          {/* 라디오 설정 가이드 그룹 */}
          <div className="ob-form-section">
            <div className="ob-form-group">
              <label className="ob-form-label">환경 사고 내부 관리체계 분류기준<span className="ob-req-dot">*</span></label>
              <div className="ob-radio-tile-group">
                <label className="ob-radio-label"><input type="radio" name="mgmt_sys" className="ob-radio-input" defaultChecked /> 화학물질관리법 기준</label>
                <label className="ob-radio-label"><input type="radio" name="mgmt_sys" className="ob-radio-input" /> 내부 자체 지침</label>
              </div>
            </div>
            <div className="ob-form-group">
              <label className="ob-form-label">증빙 및 입력 프로세스 단위 설정<span className="ob-req-dot">*</span></label>
              <div className="ob-radio-tile-group">
                <label className="ob-radio-label"><input type="radio" name="scope_type" className="ob-radio-input" defaultChecked /> 이슈마다 개별 등록</label>
                <label className="ob-radio-label"><input type="radio" name="scope_type" className="ob-radio-input" /> 전체 통합 일괄 등록</label>
              </div>
            </div>
          </div>

          {/* 정성 서술 및 보고서 포함 스위치 영역 */}
          <div className="ob-modal-section">
            <div className="ob-modal-section-header">
              <h3 className="ob-modal-section-title">정성 기술 공시 서술 (Describe / Narrative)</h3>
              <div className="ob-switch-label">
                <span>보고서 포함 여부</span>
                <label className="ob-switch">
                  <input type="checkbox" checked={includeReport} onChange={(e) => setIncludeReport(e.target.checked)} />
                  <span className="ob-slider"></span>
                </label>
              </div>
            </div>
            <div className="ob-template-preview">
              <strong>[보고서형 템플릿]</strong><br />
              {"{회사명}"}은 환경 유출/누출 사고 건수 관련 사건을 {"{관리체계}"}에 따라 등록·검토하고 있으며, 보고기간 중 발생 건수는 {"{사건_건수}"}건이다. 주요 원인과 조치사항은 {"{조치내용}"}에 따라 관리된다.
            </div>
          </div>

          {/* 하위 연계 Matrix 리스트 테이블 영역 */}
          <div className="ob-modal-section">
            <h3 className="ob-modal-section-title">
              하위 연계 Metric 단위 입력 명세 목록 ({metricItem.issueId}__E0001 ~ E0003)
            </h3>
            
            <div className="ob-modal-assignee-table-wrap">
              <table className="ob-modal-assignee-table">
                <thead>
                  <tr>
                    <th style={{ width: '15%' }}>Atomic ID</th>
                    <th style={{ width: '28%' }}>지표명 / Field Label</th>
                    <th style={{ width: '18%' }}>데이터 직접 입력 (Value)</th>
                    <th style={{ width: '12%' }}>필수여부</th>
                    <th style={{ width: '12%' }}>저장 단위</th>
                    <th style={{ width: '15%' }}>증빙 파일 업로드</th>
                  </tr>
                </thead>
                <tbody>
                  {subMetrics.map((sub) => (
                    <tr key={sub.issueId}>
                      <td className="ob-td-atomic-id">{sub.issueId}</td>
                      <td className="ob-td-field-label">{sub.checklistQuestion}</td>
                      <td>
                        <input 
                          className="ob-modal-table-input" 
                          placeholder="0"
                          value={atomicValues[sub.issueId] || ''}
                          onChange={(e) => handleInputChange(sub.issueId, e.target.value)}
                        />
                      </td>
                      <td><span className="ob-table-req-badge">REQUIRED</span></td>
                      <td><span className="ob-modal-table-unit">{sub.unit}</span></td>
                      <td>
                        <label className="ob-inline-uploader">
                          <input type="file" style={{ display: 'none' }} onChange={(e) => handleFileChange(sub.issueId, e)} />
                          <span>
                            {atomicFiles[sub.issueId] ? `📎 ${atomicFiles[sub.issueId].name.slice(0, 8)}...` : '파일선택'}
                          </span>
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div className="ob-modal-table-footer-guide">
              <span>* 정량 데이터 수동 검증 완료 후 확정 처리됩니다.</span>
              <button type="button" className="ob-invite-link-btn">
                ✉️ 이메일로 공동 작업자 초대하기
              </button>
            </div>
          </div>

        </div>

        {/* 푸터 액션 바 */}
        <div className="ob-modal-footer">
          <button type="button" className="ob-modal-btn secondary" onClick={onClose}>닫기</button>
          <button type="button" className="ob-modal-btn primary" onClick={handleSubmitSequence}>임시저장 후 최종제출</button>
        </div>

      </div>
    </div>
  );
}