import pytest
from unittest.mock import MagicMock

from src.utils.onboardingscoperepository import ensureRollupResponseWorkspaceTx

def test_ensure_rollup_response_workspace_tx():
    cur = MagicMock()
    
    # Mocking the fetchone for SELECT source_cycle_id
    cur.fetchone.side_effect = [
        {"source_cycle_id": 100}, # batch
        None, # cycle
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
    
    # verify SELECT source_cycle_id
    cur.execute.assert_any_call(
        "\n        SELECT source_cycle_id \n        FROM ESG_ROLLUP_BATCH \n        WHERE id = ? AND delete_yn = 0\n        ",
        (50,)
    )
    
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
