import pytest
from src.utils.onboardingapprovalrepository import resolveCycleApprovalStatus

def test_resolveCycleApprovalStatus_submitted():
    # 3. Input 5건 submitted, KPI Fact 0건 -> 승인 작업함 SUBMITTED
    requiredAtomicSet = {"A1", "A2", "A3", "A4", "A5"}
    inputRows = [
        {"atomic_metric_id": f"A{i}", "input_status": "submitted"} for i in range(1, 6)
    ]
    status = resolveCycleApprovalStatus(
        requiredAtomicCount=5,
        completedAtomicCount=5,
        submittedAtomicCount=5,
        approvedAtomicCount=0,
        inputRows=inputRows,
        latestHistory={"action_status": "submit"},
        requiredAtomicSet=requiredAtomicSet,
    )
    assert status == "SUBMITTED"

def test_resolveCycleApprovalStatus_not_approved_yet():
    # 4. Input 5건 approved, KPI Fact 0건 -> 승인 작업함 APPROVED 아님
    # If the policy is PROMOTE_TO_KPI_FACT, approvedAtomicCount only counts facts.
    requiredAtomicSet = {"A1", "A2", "A3", "A4", "A5"}
    inputRows = [
        {"atomic_metric_id": f"A{i}", "input_status": "approved"} for i in range(1, 6)
    ]
    status = resolveCycleApprovalStatus(
        requiredAtomicCount=5,
        completedAtomicCount=5,
        submittedAtomicCount=5,
        approvedAtomicCount=0,
        inputRows=inputRows,
        latestHistory={"action_status": "approve"},
        requiredAtomicSet=requiredAtomicSet,
    )
    # The status function will see approvedCount=0. Since 5 > 0 and submitted >= 5, it falls back to SUBMITTED
    assert status == "SUBMITTED"

def test_resolveCycleApprovalStatus_approved():
    # 5. KPI Fact 5건 approved -> 승인 작업함 APPROVED
    requiredAtomicSet = {"A1", "A2", "A3", "A4", "A5"}
    inputRows = [
        {"atomic_metric_id": f"A{i}", "input_status": "approved"} for i in range(1, 6)
    ]
    status = resolveCycleApprovalStatus(
        requiredAtomicCount=5,
        completedAtomicCount=5,
        submittedAtomicCount=5,
        approvedAtomicCount=5,
        inputRows=inputRows,
        latestHistory={"action_status": "approve"},
        requiredAtomicSet=requiredAtomicSet,
    )
    assert status == "APPROVED"
