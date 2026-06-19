/**
 * OnboardingMetricTable.jsx
 * 레이어: Component (onboards)
 * 역할: 온보딩 지표 목록을 테이블로 렌더링하며, 담당자 지정·일괄 선택·입력 버튼 등을 제공하는 데이터 테이블
 *
 * Props:
 *   g0Error — 지표 조회 오류 메시지
 *   g0Items — 표시할 지표 항목 배열 (할당·승인 상태 포함)
 *   loadingG0 — 지표 로딩 여부
 *   selectedMetricIds — 일괄 선택된 metricId 배열
 *   onSelectMetric — 행 체크박스 토글 핸들러
 *   onToggleSelectAll — 전체 선택/해제 핸들러
 *   onBulkAssignRequested — 일괄 담당자 지정 요청 핸들러
 *   onOpenMetric — 지표 입력 모달 열기 핸들러
 *   onRetry — 오류 발생 시 재시도 핸들러
 *   viewerRole — 현재 사용자 역할
 *   canManageAssignments — 담당자 지정 권한 여부
 *   isConsultantViewer — 컨설턴트 뷰어 여부 (읽기 전용 상세 보기만 허용)
 *   readOnlyYn — 읽기 전용 모드 여부
 */
import { calculateMetricStatus } from "./onboardingUtils";
import EmptyState from "@components/UI/EmptyState";

const groupByMetric = (items = []) => {
  const grouped = [];
  const seen = new Set();
  items.forEach((item) => {
    if (!seen.has(item.metricId)) {
      seen.add(item.metricId);
      grouped.push(item);
    }
  });
  return grouped;
};

const OnboardingMetricTable = ({
  g0Error,
  g0Items,
  loadingG0,
  selectedMetricIds,
  onSelectMetric,
  onToggleSelectAll,
  onBulkAssignRequested,
  onOpenMetric,
  onRetry,
  viewerRole,
  canManageAssignments,
  isConsultantViewer,
  readOnlyYn = false,
}) => {
  if (g0Error) {
    return (
      <div className="ob1-inline-error">
        <span className="ob1-error-icon">!</span>
        <span>{g0Error}</span>
        <button type="button" className="ob1-btn-retry" onClick={onRetry}>
          다시 시도
        </button>
      </div>
    );
  }

  if (loadingG0 && g0Items.length === 0) {
    return (
      <div className="ob1-table-loading">
        <div className="ob1-spinner" />
        <p>경영일반 데이터를 불러오고 있습니다...</p>
      </div>
    );
  }

  if (g0Items.length === 0) {
    return (
      <EmptyState
        title="할당된 데이터가 없습니다."
        desc="보고서 워크플로우를 먼저 시작해 주세요."
      />
    );
  }

  const groupedItems = groupByMetric(g0Items);
  const isAllSelected = groupedItems.length > 0 && selectedMetricIds.length === groupedItems.length;

  return (
    <div className="ob1-table-container">
      <table className="ob1-table">
        <colgroup>
          {canManageAssignments && <col style={{ width: "4%" }} />}
          <col style={{ width: "8%" }} />
          <col style={{ width: "28%" }} />
          <col style={{ width: "12%" }} />
          <col style={{ width: "14%" }} />
          <col style={{ width: "13%" }} />
          <col style={{ width: "13%" }} />
          <col style={{ width: "8%" }} />
        </colgroup>
        <thead className={selectedMetricIds.length > 0 && canManageAssignments ? "ob1-thead-selected" : ""}>
          {selectedMetricIds.length > 0 && canManageAssignments && !readOnlyYn ? (
            <tr style={{ backgroundColor: "#e0e7ff" }}>
              <th style={{ width: "44px" }}>
                <input
                  type="checkbox"
                  className="ob1-checkbox"
                  checked={isAllSelected}
                  onChange={() => onToggleSelectAll(groupedItems.map(i => i.metricId))}
                  disabled={readOnlyYn}
                />
              </th>
              <th colSpan="7">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: '#1e293b', fontSize: '14px' }}>
                    {selectedMetricIds.length}개 항목 선택됨
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="ob1-btn-batch-assign-header"
                      onClick={onBulkAssignRequested}
                      disabled={readOnlyYn}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                      담당자 일괄 지정
                    </button>
                    <button
                      type="button"
                      className="ob1-btn-batch-cancel-header"
                      onClick={() => onToggleSelectAll([])}
                      disabled={readOnlyYn}
                    >
                      ✕ 일괄 선택 해제
                    </button>
                  </div>
                </div>
              </th>
            </tr>
          ) : (
            <tr>
              {canManageAssignments && (
                <th style={{ width: "4%" }}>
                  <input
                    type="checkbox"
                    className="ob1-checkbox"
                    aria-label="전체 선택"
                    checked={isAllSelected}
                    onChange={() => onToggleSelectAll(groupedItems.map(i => i.metricId))}
                    disabled={readOnlyYn}
                  />
                </th>
              )}
              <th style={{ width: "8%" }}>Data ID</th>
              <th style={{ width: "28%" }}>입력 데이터 설명</th>
              <th style={{ width: "12%" }}>담당자</th>
              <th style={{ width: "14%" }}>제출 기한</th>
              <th style={{ width: "13%" }}>입력 상태</th>
              <th style={{ width: "13%" }}>승인 상태</th>
              <th style={{ width: "8%" }}>관리</th>
            </tr>
          )}
        </thead>
        <tbody>
          {groupedItems.map((item) => {
            const subMetrics = g0Items.filter((sub) => sub.metricId === item.metricId);
            const statusInfo = calculateMetricStatus(subMetrics);

            const formatInputStatus = (rawStatus, fallbackStatusInfo) => {
              if (!rawStatus) return { label: fallbackStatusInfo.label, cls: fallbackStatusInfo.cls || 'not-started' };
              const normalized = String(rawStatus).toLowerCase().trim();
              switch (normalized) {
                case 'approved': return { label: '입력 완료', cls: 'approved' };
                case 'submitted': return { label: '제출 완료', cls: 'submitted' };
                case 'rejected': return { label: '반려', cls: 'rejected' };
                case 'in_progress':
                case 'partial': return { label: '작성중', cls: 'draft' };
                case 'not_started': return { label: '미입력', cls: 'not-started' };
                case '입력 완료': return { label: '입력 완료', cls: 'approved' };
                case '제출완료': return { label: '제출 완료', cls: 'submitted' };
                case '작성중': return { label: '작성중', cls: 'draft' };
                default: return { label: rawStatus, cls: 'not-started' };
              }
            };

            const formatApprovalStatus = (rawStatus) => {
              if (!rawStatus) return { label: '미제출', cls: 'not-started' };
              const normalized = String(rawStatus).toLowerCase().trim();
              switch (normalized) {
                case 'approved': return { label: '승인 완료', cls: 'approved' };
                case 'submitted':
                case 'pending': return { label: '승인 대기', cls: 'draft' };
                case 'reviewed': return { label: '검토 완료', cls: 'reviewed' };
                case 'rejected': return { label: '반려', cls: 'rejected' };
                case '미제출': return { label: '미제출', cls: 'not-started' };
                case '승인대기':
                case '검토대기': return { label: '승인 대기', cls: 'draft' };
                case '검토완료': return { label: '검토 완료', cls: 'reviewed' };
                case '승인완료': return { label: '승인 완료', cls: 'approved' };
                case '반려': return { label: '반려', cls: 'rejected' };
                default: return { label: rawStatus, cls: 'not-started' };
              }
            };

            const inputStatus = formatInputStatus(item.inputStatus, statusInfo);
            const approvalStatus = formatApprovalStatus(item.approvalStatus);

            const isSelected = selectedMetricIds.includes(item.metricId);
            const isEsgManager = viewerRole === 'ESG 담당자' || viewerRole === '관리자' || viewerRole === 'ESG' || viewerRole === 'ADMIN';
            const isAssigned = item.assignmentStatus === 'ASSIGNED' || item.assignmentStatus === 'assigned';
            const isInvitePending = item.inviteStatus === 'PENDING';
            const isSelfAssigned = item.selfAssignedYn === true;
            const isAssignedToOther = isAssigned && !isSelfAssigned;

            const todayStr = new Date().toISOString().slice(0, 10);
            const isOverdue = item.submissionDueDate && item.submissionDueDate < todayStr;

            return (
              <tr key={item.metricId} className={isSelected ? "selected ob1-row-selected" : ""}>
                {canManageAssignments && (
                  <td>
                    <input
                      type="checkbox"
                      className="ob1-checkbox"
                      aria-label={`${item.metricId} 선택`}
                      checked={isSelected}
                      onChange={() => onSelectMetric(item.metricId)}
                      disabled={readOnlyYn}
                    />
                  </td>
                )}
                <td>{item.metricId}</td>
                <td className="ob1-td-name">{item.metricName || item.atomicName || "-"}</td>

                <td>
                  <div className="ob1-assignee-cell">
                    {isSelfAssigned ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-status">본인 입력</span></>
                    ) : isInvitePending ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-email">{item.assigneeEmail}</span><span className="ob1-assignee-status pending">초대 대기</span></>
                    ) : isAssigned ? (
                      <><span className="ob1-assignee-name">{item.assigneeName}</span><span className="ob1-assignee-email">{item.assigneeEmail}</span></>
                    ) : (
                      <span className="ob1-assignee-status unassigned">미지정</span>
                    )}
                  </div>
                </td>

                <td>
                  {item.submissionDueDate ? (
                    <div style={{ color: isOverdue ? '#ef4444' : '#334155', fontWeight: isOverdue ? 600 : 400 }}>
                      {item.submissionDueDate}
                      {isOverdue && <div style={{ fontSize: '0.75rem', marginTop: '2px' }}>기한 초과</div>}
                    </div>
                  ) : (
                    <span style={{ color: '#94a3b8' }}>미설정</span>
                  )}
                </td>

                <td>
                  <span className={`ob1-status-pill ${inputStatus.cls}`}>
                    {inputStatus.label}
                  </span>
                </td>

                <td>
                  <span className={`ob1-status-pill ${approvalStatus.cls}`}>
                    {approvalStatus.label}
                  </span>
                </td>

                <td>
                  <div className="ob1-td-actions" style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                    {isConsultantViewer ? (
                      <button type="button" className="ob1-btn-input" onClick={() => onOpenMetric(item, subMetrics)}>상세 보기</button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="ob1-btn-input"
                          onClick={() => {
                            if (readOnlyYn) return;
                            if (isEsgManager && isAssignedToOther) {
                              if (!window.confirm("이 지표는 다른 담당자에게 할당되어 있습니다. 그래도 수정하시겠습니까?")) {
                                return;
                              }
                            }
                            onOpenMetric(item, subMetrics);
                          }}
                          disabled={readOnlyYn || (!isEsgManager && (!isAssigned || !isSelfAssigned))}
                        >
                          입력
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default OnboardingMetricTable;
