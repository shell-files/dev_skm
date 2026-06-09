import pytest
from unittest.mock import MagicMock

from src.utils.onboardingscoperepository import ensureRollupResponseWorkspaceTx

def test_ensure_rollup_response_workspace_tx():
    cur = MagicMock()
    
    # Mocking the fetchone for SELECT source_cycle_id
    cur.fetchone.side_effect = [
        {"source_cycle_id": 100, "rollup_purpose_code": "REPORT_DISCLOSURE"}, # batch
        {"id": 300}, # cycle (existing)
    ]
    
    cur.fetchall.return_value = [
        {
            "metric_id": "M1",
            "scope_source_type": "PRE_DMA_G0",
            "source_materiality_run_id": 1,
            "source_selected_sub_issue_id": 2,
            "source_sub_issue_code": "GENERAL_MANAGEMENT"
        }
    ]
    
    cur.lastrowid = 200
    
    ensureRollupResponseWorkspaceTx(
        cur=cur,
        companyId=1,
        reportingYear=2024,
        batchId=50,
        actionableInputMetricIds=["M1"],
        actorUserId=99
    )
    
    # Verify the scope deactivation for existing cycle
    deactivation_found = any(
        "UPDATE ESG_ONBOARDING_CYCLE_METRIC_SCOPE" in args[0] and "active_yn = 0" in args[0]
        for args, kwargs in cur.execute.call_args_list
    )
    assert deactivation_found
    
    # Verify the final INSERT into scope
    found_insert = False
    for call in cur.execute.call_args_list:
        args, kwargs = call
        if "INSERT INTO ESG_ONBOARDING_CYCLE_METRIC_SCOPE" in args[0]:
            found_insert = True
            # (cycleId, companyId, metricId, scope_source_type, source_materiality_run_id, source_selected_sub_issue_id, source_sub_issue_code, approvalPolicy, displayIndex * 10, actorUserId)
            assert args[1][2] == "M1"
            assert args[1][3] == "PRE_DMA_G0"
            assert args[1][4] == 1
            assert args[1][5] == 2
            assert args[1][6] == "GENERAL_MANAGEMENT"
            
    assert found_insert

def test_ensure_rollup_response_workspace_dma_precheck():
    cur = MagicMock()
    
    # Mocking the fetchone for SELECT source_cycle_id
    cur.fetchone.side_effect = [
        {"source_cycle_id": 100, "rollup_purpose_code": "DMA_PRECHECK"}, # batch
        None, # cycle (not existing)
    ]
    
    cur.fetchall.return_value = []
    
    cur.lastrowid = 200
    
    ensureRollupResponseWorkspaceTx(
        cur=cur,
        companyId=1,
        reportingYear=2024,
        batchId=50,
        actionableInputMetricIds=["G0-02"],
        actorUserId=99
    )
    
    # Verify the final INSERT into scope
    found_insert = False
    for call in cur.execute.call_args_list:
        args, kwargs = call
        if "INSERT INTO ESG_ONBOARDING_CYCLE_METRIC_SCOPE" in args[0]:
            found_insert = True
            # (cycleId, companyId, metricId, scope_source_type, source_materiality_run_id, source_selected_sub_issue_id, source_sub_issue_code, approvalPolicy, displayIndex * 10, actorUserId)
            assert args[1][2] == "G0-02"
            assert args[1][3] == "PRE_DMA_G0"
            
    assert found_insert
