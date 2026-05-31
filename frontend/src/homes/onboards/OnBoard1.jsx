import { useMemo, useState, useEffect } from "react";
import { useNavigate } from "react-router";
import "@styles/onboarding1.css";
import { useAuth } from '@hooks/AuthContext.jsx';
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import OnboardingModalShell from "./modal/OnboardingModalShell";
import SubsidiaryRequestModal from "./modal/SubsidiaryRequestModal";
import SubsidiaryTransferModal from "./modal/SubsidiaryTransferModal";
import RollupSummaryPanel from "./RollupSummaryPanel";
import { getCurrent, getG0Status, getG0Profile, saveG0Profile, DEFAULT_REPORTING_YEAR } from "@/apis/report";

const getInputTypeInfo = (metric) => {
  // DB에서 아직 입력 유형 분기를 제공하지 않으므로 기본적으로 문장형 처리
  return { label: '문장형', cls: 'narrative' };
};

const getStatusInfo = (status) => {
  switch (status) {
    case 'NOT_STARTED': return { label: '미입력', cls: 'not-started' };
    case 'DRAFT': return { label: '작성 중', cls: 'draft' };
    case 'SUBMITTED': return { label: '제출 완료', cls: 'submitted' };
    case 'APPROVED': return { label: '승인 완료', cls: 'approved' };
    case 'REJECTED': return { label: '반려', cls: 'rejected' };
    default: return { label: '미입력', cls: 'not-started' };
  }
};

const OnBoard1 = () => {
  const { selectedCompany } = useAuth();
  const navigate = useNavigate();
  
  const [metrics, setMetrics] = useState([]);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  const [workflow, setWorkflow] = useState(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState(null);

  const reportingYear = selectedCompany?.reportingYear || DEFAULT_REPORTING_YEAR;

  const loadG0Metrics = async () => {
    if (!selectedCompany?.companyId) return;
    setLoadingMetrics(true);
    try {
      const res = await getG0Profile(selectedCompany.companyId, reportingYear);
      setMetrics(res?.items || []);
    } catch (error) {
      showDefaultAlert("오류", "경영일반 정보를 불러오지 못했습니다.", "error");
      setMetrics([]);
    } finally {
      setLoadingMetrics(false);
    }
  };

  useEffect(() => {
    loadG0Metrics();
  }, [selectedCompany?.companyId, reportingYear]);

  useEffect(() => {
    if (!selectedCompany?.companyId) return;

    const fetchWorkflow = async () => {
      try {
        const current = await getCurrent(selectedCompany.companyId, reportingYear);
        if (!current?.data) {
          throw new Error("Workflow response is empty");
        }

        let latest = current.data;
        if (latest.runId) {
          const g0Status = await getG0Status(latest.runId);
          if (g0Status?.data) {
            latest = g0Status.data;
          }
        }

        setWorkflow(latest);
        setActiveBatchId(latest.requiredRollupBatchId || null);
      } catch (e) {
        console.error(e);
        showDefaultAlert("오류", "보고서 진행 상태를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", "error");
      } finally {
        setLoadingWorkflow(false);
      }
    };
    fetchWorkflow();
  }, [selectedCompany?.companyId, reportingYear]);

  // 통계 계산
  const totalCount = metrics.length;
  let completedCount = 0;
  let approvedCount = 0;
  
  metrics.forEach(m => {
    if (m.status === 'SUBMITTED' || m.status === 'APPROVED') completedCount++;
    if (m.status === 'APPROVED') approvedCount++;
  });
  const unapprovedCount = totalCount - approvedCount;

  const rnrDisplay = (assignees = []) => {
    const accepted = assignees.filter(a => a.status === "ACCEPTED");
    if (!accepted.length) return { name: "-", team: "" };
    return { name: accepted[0].name, team: "환경경영팀" };
  };

  const getMetricItems = (metricId) => {
    return metrics.filter(item => item.metricId === metricId);
  };

  const canStartDma = workflow?.nextAction === "START_DMA";
  const canRequestSubsidiaries = workflow?.nextAction === "REQUEST_ROLLUP";
  const shouldWaitRollup = workflow?.nextAction === "WAIT_ROLLUP";

  const handleCtaClick = () => {
    if (!workflow) return;
    if (workflow.financialBasis === 'ENTITY') {
      if (canStartDma) {
        showDefaultAlert("진행", "이중중대성평가를 시작합니다.", "success");
        // navigate('/dma') 등의 처리
      }
    } else if (workflow.financialBasis === 'CONSOLIDATED') {
      if (workflow.isParent) {
        if (canStartDma) {
          showDefaultAlert("진행", "이중중대성평가를 시작합니다.", "success");
        } else if (canRequestSubsidiaries) {
          setIsSubReqModalOpen(true);
        }
      } else {
        setIsSubTransferModalOpen(true);
      }
    }
  };

  const basisLabel = workflow?.financialBasis === 'CONSOLIDATED' ? '연결기준' : '독립기준';

  return (
    <div id="ob1-page">
      {/* 상단 헤더 */}
      <div className="ob1-header">
        <h1 className="ob1-title">온보딩 [{basisLabel}]</h1>
        <p className="ob1-desc">
          지속가능경영보고서 작성을 위한 기본 경영일반(G0) 지표를 입력하고 확인합니다.<br/>
          {workflow?.financialBasis === 'CONSOLIDATED' && "본사 및 자회사의 데이터를 통합 관리합니다."}
        </p>
      </div>

      {/* 상단 4개 카드 */}
      <div className="ob1-cards">
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">필수 G0 지표</div>
          <div className="ob1-stat-value">{totalCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">입력 완료</div>
          <div className="ob1-stat-value success">{completedCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">승인 완료</div>
          <div className="ob1-stat-value success">{approvedCount}</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">미승인</div>
          <div className="ob1-stat-value warning">{unapprovedCount}</div>
        </div>
      </div>

      <div className="ob1-content-layout">
        {/* 좌측 패널 */}
        <div className="ob1-sidebar-panel">
          <div className="ob1-sidebar-title">할당 항목</div>
          <ul className="ob1-sidebar-menu">
            <li className="ob1-sidebar-menu-item active">
              1. 경영일반 - G0
            </li>
          </ul>
        </div>

        {/* 우측 데이터 테이블 */}
        <div className="ob1-main-area">
          {activeBatchId && (
            <RollupSummaryPanel 
              batchId={activeBatchId} 
              onCalculated={() => console.log('연결 집계 완료')} 
            />
          )}
          <div className="ob1-table-container">
            <table className="ob1-table">
              <thead>
                <tr>
                  <th style={{ width: '10%' }}>지표 코드</th>
                  <th style={{ width: '15%' }}>세부 항목 코드</th>
                  <th style={{ width: '30%' }}>지표명</th>
                  <th style={{ width: '10%' }}>입력 유형</th>
                  <th style={{ width: '12%' }}>담당자</th>
                  <th style={{ width: '10%' }}>마감기한</th>
                  <th style={{ width: '8%' }}>상태</th>
                  <th style={{ width: '5%' }}>데이터 입력</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((item, i) => {
                  const tInfo = getInputTypeInfo(item);
                  const sInfo = getStatusInfo(item.status);
                  const rnr = rnrDisplay(item.assignees);
                  const displayValue = item.valueNumeric ?? item.valueText;

                  return (
                    <tr key={`${item.metricId}-${item.atomicMetricId}-${i}`}>
                      <td>{item.metricId}</td>
                      <td>{item.atomicMetricId || "-"}</td>
                      <td className="ob1-td-name">{item.atomicName}</td>
                      <td><span className={`ob1-type-badge ${tInfo.cls}`}>{tInfo.label}</span></td>
                      <td className="ob1-td-rnr">
                        <div className="ob1-rnr-info">
                          <span className="ob1-rnr-name">{rnr.name}</span>
                          <span className="ob1-rnr-team">{rnr.team}</span>
                        </div>
                      </td>
                      <td>2026-06-30</td>
                      <td><span className={`ob1-status-pill ${sInfo.cls}`}>{sInfo.label}</span></td>
                      <td>
                        <button type="button" className="ob1-btn-input" onClick={() => {
                          setSelectedItem({ metricId: item.metricId, metricName: item.metricName, items: getMetricItems(item.metricId) });
                          setIsModalOpen(true);
                        }}>
                          입력
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          
          {/* CTA 하단 분기 */}
          <div className="ob1-cta-container">
            {workflow?.financialBasis === 'CONSOLIDATED' && workflow?.isParent && shouldWaitRollup ? (
              // 자회사 데이터 요청 중 (연결 집계 현황 표시) 시점엔 CTA 버튼 숨김
              null
            ) : (
              <button 
                className="ob1-btn-cta" 
                onClick={handleCtaClick}
                disabled={loadingWorkflow || 
                  (workflow?.financialBasis === 'ENTITY' && !canStartDma) || 
                  (workflow?.financialBasis === 'CONSOLIDATED' && workflow?.isParent && !canStartDma && !canRequestSubsidiaries)
                }
              >
                {loadingWorkflow ? "로딩중..." : 
                  workflow?.financialBasis === 'ENTITY' ? "이중중대성평가 진행하기" :
                  workflow?.isParent ? (canStartDma ? "이중중대성평가 진행하기" : "자회사 데이터 요청하기") : "지주사에 데이터 전송하기"
                }
              </button>
            )}
            {(workflow?.financialBasis === 'ENTITY' && !canStartDma && !loadingWorkflow) && (
              <div style={{ fontSize: '0.85rem', color: '#ea580c', marginTop: '8px' }}>
                G0 입력 및 승인 완료 후 진행할 수 있습니다.
              </div>
            )}
            {(workflow?.financialBasis === 'CONSOLIDATED' && workflow?.isParent && !canStartDma && !canRequestSubsidiaries && !shouldWaitRollup && !loadingWorkflow) && (
              <div style={{ fontSize: '0.85rem', color: '#ea580c', marginTop: '8px' }}>
                G0 입력 및 승인 완료 후 진행할 수 있습니다.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* TODO: replace fallback with onboarding modal adapter resolver */}
      <OnboardingModalShell 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricId={selectedItem?.metricId}
        metricName={selectedItem?.metricName}
        items={selectedItem?.items || []}
        modalType="MIXED"
        onSaveAndSubmit={async (values, files, status) => {
          if (!selectedItem) return;

          try {
            const payload = {
              reportingYear,
              items: selectedItem.items.map(item => {
                const updatedVal = values[item.atomicMetricId] !== undefined ? values[item.atomicMetricId] : (item.valueNumeric ?? item.valueText ?? null);
                // 여기서 임시로 numeric과 text 구분 (간단한 타입 체크)
                const isNumeric = !isNaN(parseFloat(updatedVal)) && isFinite(updatedVal);
                return {
                  metricId: item.metricId,
                  atomicMetricId: item.atomicMetricId,
                  valueText: isNumeric ? null : (updatedVal === "" ? null : updatedVal),
                  valueNumeric: isNumeric ? parseFloat(updatedVal) : null,
                  unit: item.unit ?? null,
                };
              })
            };

            await saveG0Profile(selectedCompany.companyId, payload);
            await loadG0Metrics();

            showDefaultAlert("완료", status === 'DRAFT' ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.", "success");
            setIsModalOpen(false);
          } catch (err) {
            console.error(err);
            showDefaultAlert("오류", "처리 중 오류가 발생했습니다.", "error");
          }
        }}
      />

      <SubsidiaryRequestModal 
        isOpen={isSubReqModalOpen} 
        onClose={() => setIsSubReqModalOpen(false)} 
        runId={workflow?.runId} 
        onRequested={(batch) => {
          setActiveBatchId(batch.batchId);
          setIsSubReqModalOpen(false);
        }}
      />

      <SubsidiaryTransferModal 
        isOpen={isSubTransferModalOpen}
        onClose={() => setIsSubTransferModalOpen(false)}
        onTransferred={(batchId) => {
          // 전송 완료 시 추가 처리 (예: CTA 상태 변경 등)
          console.log('전송 완료된 배치', batchId);
        }}
      />
    </div>
  );
};

export default OnBoard1;
