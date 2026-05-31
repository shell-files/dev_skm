import { useState, useEffect } from "react";
import "@styles/onboarding1.css";
import initialMetrics from "@assets/data/onboardingData.js";
import { useAuth } from "@hooks/AuthContext.jsx";
import { showDefaultAlert } from "@components/UI/ServiceAlert";
import OnboardingModalShell from "./modal/OnboardingModalShell";
import SubsidiaryRequestModal from "./modal/SubsidiaryRequestModal";
import SubsidiaryTransferModal from "./modal/SubsidiaryTransferModal";
import RollupSummaryPanel from "./RollupSummaryPanel";
import { DEFAULT_REPORTING_YEAR, getCurrent } from "@/apis/report";

const USE_DUMMY_API = false;

const requestApi = {
  saveDraft: async (id, payload) => {
    if (USE_DUMMY_API) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      return { status: true };
    }
    return { status: true };
  },
  submit: async (id) => {
    if (USE_DUMMY_API) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      return { status: true };
    }
    return { status: true };
  },
  uploadEvidence: async (id, file) => {
    if (USE_DUMMY_API) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      return { status: true };
    }
    return { status: true };
  }
};

const getInputTypeInfo = (metric) => {
  if (metric.category === "E") return { label: "계산형", cls: "calc" };
  if (metric.category === "S") return { label: "정량 직접입력", cls: "direct" };
  if (metric.category === "G") return { label: "계산형", cls: "calc" };
  return { label: "문장형", cls: "narrative" };
};

const getStatusInfo = (status) => {
  switch (status) {
    case "NOT_STARTED":
      return { label: "미입력", cls: "not-started" };
    case "DRAFT":
      return { label: "입력 진행중", cls: "draft" };
    case "SUBMITTED":
    case "APPROVED":
      return { label: "입력 완료", cls: "approved" };
    default:
      return { label: "미입력", cls: "not-started" };
  }
};

const OnBoard = () => {
  const { selectedCompany } = useAuth();
  const companyId =
    selectedCompany?.company_id ??
    selectedCompany?.companyId;

  const [metrics, setMetrics] = useState(() => {
    const cached = JSON.parse(localStorage.getItem("onboarding_metrics_dummy"));
    return cached || initialMetrics.filter((metric) => metric.issueId.startsWith("G0"));
  });

  const [workflow, setWorkflow] = useState(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  const [isSubReqModalOpen, setIsSubReqModalOpen] = useState(false);
  const [isSubTransferModalOpen, setIsSubTransferModalOpen] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState(null);

  useEffect(() => {
    const fetchWorkflow = async () => {
      if (!companyId) {
        setWorkflow(null);
        setLoadingWorkflow(false);
        return;
      }

      setLoadingWorkflow(true);
      try {
        const res = await getCurrent(companyId, DEFAULT_REPORTING_YEAR);
        if (res?.status && res.data) {
          setWorkflow(res.data);
        } else {
          setWorkflow(null);
          showDefaultAlert("오류", res?.error?.message || "보고서 워크플로우 조회에 실패했습니다.", "error");
        }
      } catch (error) {
        console.error(error);
        setWorkflow(null);
        showDefaultAlert("오류", "보고서 워크플로우 조회에 실패했습니다.", "error");
      } finally {
        setLoadingWorkflow(false);
      }
    };

    fetchWorkflow();
  }, [companyId]);

  const totalCount = metrics.length;
  let completedCount = 0;
  let notStartedCount = 0;

  metrics.forEach((metric) => {
    const statusLabel = getStatusInfo(metric.status).label;
    if (statusLabel === "입력 완료") completedCount += 1;
    else if (statusLabel === "미입력") notStartedCount += 1;
  });

  const rnrDisplay = (assignees = []) => {
    const accepted = assignees.filter((assignee) => assignee.status === "ACCEPTED");
    if (!accepted.length) return { name: "-", team: "" };
    return { name: accepted[0].name, team: "환경경영팀" };
  };

  const getSubMetrics = (issueGroup) => {
    return metrics.filter((metric) => metric.issueGroup === issueGroup);
  };

  const handleCtaClick = () => {
    if (!workflow) return;

    switch (workflow?.nextAction) {
      case "START_DMA":
        showDefaultAlert("진행", "이중중대성평가를 시작합니다.", "success");
        break;
      case "REQUEST_ROLLUP":
        setIsSubReqModalOpen(true);
        break;
      case "WAIT_ROLLUP":
        showDefaultAlert("대기", "자회사 데이터 수집 및 롤업 완료를 기다리고 있습니다.", "info");
        break;
      default:
        showDefaultAlert("안내", workflow?.message || "G0 입력 상태를 확인해 주세요.", "info");
    }
  };

  const basisLabel = workflow?.reportBasisType === "CONSOLIDATED" ? "연결기준" : "독립기준";

  return (
    <div id="ob1-page">
      <div className="ob1-header">
        <h1 className="ob1-title">온보딩 [{basisLabel}]</h1>
        <p className="ob1-desc">
          지속가능경영보고서 작성을 위한 기본 경영일반(G0) 지표를 입력하고 확인합니다.<br />
          {workflow?.reportBasisType === "CONSOLIDATED" && "본사 및 자회사의 데이터를 통합 관리합니다."}
        </p>
      </div>

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
          <div className="ob1-stat-value success">0</div>
        </div>
        <div className="ob1-stat-card">
          <div className="ob1-stat-title">미승인</div>
          <div className="ob1-stat-value warning">{totalCount}</div>
        </div>
      </div>

      <div className="ob1-content-layout">
        <div className="ob1-sidebar-panel">
          <div className="ob1-sidebar-title">할당 항목</div>
          <ul className="ob1-sidebar-menu">
            <li className="ob1-sidebar-menu-item active">
              1. 경영일반 - G0
            </li>
          </ul>
        </div>

        <div className="ob1-main-area">
          {activeBatchId && (
            <RollupSummaryPanel
              batchId={activeBatchId}
              onCalculated={() => console.log("롤업 계산 완료")}
            />
          )}
          <div className="ob1-table-container">
            <table className="ob1-table">
              <thead>
                <tr>
                  <th style={{ width: "10%" }}>Metrics ID</th>
                  <th style={{ width: "15%" }}>Atomic ID</th>
                  <th style={{ width: "30%" }}>지표명</th>
                  <th style={{ width: "10%" }}>입력 유형</th>
                  <th style={{ width: "12%" }}>R&R 담당자</th>
                  <th style={{ width: "10%" }}>마감기한</th>
                  <th style={{ width: "8%" }}>상태</th>
                  <th style={{ width: "5%" }}>데이터 입력</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((item, index) => {
                  const typeInfo = getInputTypeInfo(item);
                  const statusInfo = getStatusInfo(item.status);
                  const rnr = rnrDisplay(item.assignees);

                  return (
                    <tr key={`${item.issueId}-${index}`}>
                      <td>{item.issueId}</td>
                      <td>{item.issueId}_A</td>
                      <td className="ob1-td-name">{item.checklistQuestion}</td>
                      <td><span className={`ob1-type-badge ${typeInfo.cls}`}>{typeInfo.label}</span></td>
                      <td className="ob1-td-rnr">
                        <div className="ob1-rnr-info">
                          <span className="ob1-rnr-name">{rnr.name}</span>
                          <span className="ob1-rnr-team">{rnr.team}</span>
                        </div>
                      </td>
                      <td>2026-06-30</td>
                      <td><span className={`ob1-status-pill ${statusInfo.cls}`}>{statusInfo.label}</span></td>
                      <td>
                        <button
                          type="button"
                          className="ob1-btn-input"
                          onClick={() => {
                            setSelectedItem({ parent: item, metrics: getSubMetrics(item.issueGroup) });
                            setIsModalOpen(true);
                          }}
                        >
                          입력
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="ob1-cta-container">
            <button
              className="ob1-btn-cta"
              onClick={handleCtaClick}
              disabled={loadingWorkflow}
            >
              {loadingWorkflow ? "로딩중..." :
                workflow?.nextAction === "REQUEST_ROLLUP" ? "자회사 데이터 요청하기" :
                workflow?.nextAction === "WAIT_ROLLUP" ? "롤업 대기" :
                "이중중대성평가 진행하기"
              }
            </button>
          </div>
        </div>
      </div>

      <OnboardingModalShell
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metricItem={selectedItem?.parent}
        subMetrics={selectedItem?.metrics || []}
        modalType="MIXED"
        onSaveAndSubmit={async (values, files, status) => {
          if (!selectedItem) return;

          try {
            for (const issueId in files) {
              if (files[issueId] && files[issueId].name) {
                await requestApi.uploadEvidence(issueId, files[issueId]);
              }
            }
            const targetIds = selectedItem.metrics.map((metric) => metric.issueId);
            setMetrics((prev) =>
              prev.map((metric) => {
                if (targetIds.includes(metric.issueId)) {
                  return {
                    ...metric,
                    value: values[metric.issueId] || "",
                    status: status || "SUBMITTED",
                    evidenceAttached: !!files[metric.issueId],
                    evidenceFileName: files[metric.issueId]?.name || ""
                  };
                }
                return metric;
              })
            );

            for (const issueId in values) {
              await requestApi.saveDraft(issueId, { value: values[issueId] });
              if (status === "SUBMITTED") await requestApi.submit(issueId);
            }

            showDefaultAlert("완료", status === "DRAFT" ? "임시저장이 완료되었습니다." : "데이터 제출이 완료되었습니다.", "success");
            setIsModalOpen(false);
          } catch (error) {
            console.error(error);
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
          console.log("전송 완료된 배치", batchId);
        }}
      />
    </div>
  );
};

export default OnBoard;
