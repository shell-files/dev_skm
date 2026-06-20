/**
 * UserManagementModal.jsx
 * 레이어: Component (mains/modal)
 * 역할: 개별 사용자의 기본 정보·역할·담당 데이터 현황을 조회하고 권한 변경·연결 해제 등 관리 액션을 제공하는 모달
 *
 * Props:
 *   isOpen — 모달 표시 여부
 *   onClose — 모달 닫기 핸들러
 *   userItem — 관리할 사용자 객체 (name, email, company, role, assignmentScopes 등)
 */
import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { showDefaultAlert } from '@components/UI/ServiceAlert';
import ModalWrapper from "@components/UI/ModalWrapper";

const getRoleLabel = (role) => {
  const map = {
    '관리자': '관리자', ADMIN: '관리자',
    'ESG담당자': 'ESG 담당자', ESG_MANAGER: 'ESG 담당자',
    '컨설턴트': '컨설턴트', CONSULTANT: '컨설턴트',
    '부서담당자': '부서담당자', EMPLOYEE: '부서담당자', ASSIGNEE: '부서담당자',
  };
  return map[role] || role || '-';
};

const getConnectionStatus = (role) => {
  if (role === '컨설턴트' || role === 'CONSULTANT') return '컨설턴트 연결';
  if (['관리자','ADMIN','ESG담당자','ESG_MANAGER'].includes(role)) return '정상 연결';
  if (['부서담당자','EMPLOYEE','ASSIGNEE'].includes(role)) return '부서 연결';
  return '미확인';
};

const isEmployee = (role) => ['부서담당자', 'EMPLOYEE', 'ASSIGNEE'].includes(role);
const isConsultant = (role) => ['컨설턴트', 'CONSULTANT'].includes(role);

export default function UserManagementModal({ isOpen, onClose, userItem }) {
  const [selectedRole, setSelectedRole] = useState(userItem?.role || '');

  React.useEffect(() => {
    if (isOpen && userItem) {
      setSelectedRole(userItem.role || '');
    }
  }, [isOpen, userItem]);

  if (!isOpen || !userItem) return null;

  const role = userItem.role;
  const scopes = userItem.assignmentScopes || [];

  const handlePreviewAction = (label) => {
    showDefaultAlert('안내', `${label} 작업은 후속 단계에서 진행됩니다.`, 'info');
  };

  return createPortal(
    <ModalWrapper
      title={`${userItem.name} 사용자 관리`}
      onClose={onClose}
      maxWidth="640px"
      footer={
        <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-confirm" onClick={onClose}>닫기</button>
        </div>
      }
    >
        <div style={{ padding: '24px' }}>
          {/* User Info */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <InfoRow label="사용자명" value={userItem.name} />
            <InfoRow label="이메일" value={userItem.email} />
            <InfoRow label="소속 회사" value={userItem.company} />
            <InfoRow label="역할" value={getRoleLabel(role)} />
            <InfoRow label="연결 상태" value={getConnectionStatus(role)} />
          </div>

          {/* Role Change */}
          <h4 style={{ fontSize: '0.95rem', color: '#1e293b', marginBottom: '12px' }}>역할·권한</h4>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', alignItems: 'center' }}>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem', color: '#334155', minWidth: '160px' }}
            >
              <option value="관리자">관리자</option>
              <option value="ESG담당자">ESG담당자</option>
              <option value="컨설턴트">컨설턴트</option>
              <option value="부서담당자">부서담당자</option>
            </select>
            <button
              className="btn-outline"
              onClick={() => handlePreviewAction('권한 변경 저장')}
              style={{ ...actionBtnStyle, background: '#f8fafc' }}
            >
              권한 변경 저장
            </button>
          </div>

          {/* Assignment Scopes */}
          <h4 style={{ fontSize: '0.95rem', color: '#1e293b', marginBottom: '12px' }}>담당 데이터 현황</h4>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden', marginBottom: '24px' }}>
            {scopes.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                  <tr>
                    <th style={thStyle}>보고 연도</th>
                    <th style={thStyle}>프로젝트 명</th>
                    <th style={thStyle}>보고 유형</th>
                    <th style={thStyle}>담당 Sub-Issue</th>
                    <th style={thStyle}>데이터 입력 수</th>
                  </tr>
                </thead>
                <tbody>
                  {scopes.map((scope, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={tdStyle}>{scope.reportingYear}</td>
                      <td style={tdStyle}>{scope.projectName}</td>
                      <td style={tdStyle}><span style={{ fontSize: '11px', background: '#f1f5f9', padding: '2px 8px', borderRadius: '4px' }}>{scope.cycleType}</span></td>
                      <td style={tdStyle}>{scope.assignedSubIssues?.join(' · ') || '-'}</td>
                      <td style={{ ...tdStyle, textAlign: 'center', fontWeight: 600 }}>{scope.assignedMetricCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
                할당된 프로젝트와 담당 데이터가 없습니다.
              </div>
            )}
          </div>

          {/* Actions */}
          <h4 style={{ fontSize: '0.95rem', color: '#1e293b', marginBottom: '12px' }}>관리 액션</h4>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {isEmployee(role) && (
              <>
                <button
                  className="btn-outline"
                  onClick={() => handlePreviewAction('담당 데이터 수정')}
                  style={actionBtnStyle}
                >
                  온보딩에서 담당 데이터 수정
                </button>
                <button
                  className="btn-outline"
                  onClick={() => handlePreviewAction('연결 해제')}
                  style={{ ...actionBtnStyle, borderColor: '#fecaca', color: '#dc2626' }}
                >
                  회사 연결 해제
                </button>
              </>
            )}
            {isConsultant(role) && (
              <>
                <button
                  className="btn-outline"
                  onClick={() => handlePreviewAction('연결 해제')}
                  style={{ ...actionBtnStyle, borderColor: '#fecaca', color: '#dc2626' }}
                >
                  컨설턴트 연결 해제
                </button>
              </>
            )}
            {!isEmployee(role) && !isConsultant(role) && (
              <button
                className="btn-outline"
                onClick={() => handlePreviewAction('권한 초기화 등 추가 기능')}
                style={actionBtnStyle}
              >
                추가 권한 관리
              </button>
            )}
          </div>
        </div>

    </ModalWrapper>,
    document.body
  );
}

const InfoRow = ({ label, value }) => (
  <div>
    <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '14px', color: '#1e293b', fontWeight: 500 }}>{value || '-'}</div>
  </div>
);

const thStyle = { padding: '10px 12px', fontWeight: 600, color: '#475569', textAlign: 'left', fontSize: '0.8rem' };
const tdStyle = { padding: '10px 12px', color: '#1e293b' };
const actionBtnStyle = { padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' };
