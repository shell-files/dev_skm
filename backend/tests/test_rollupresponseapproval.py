import asyncio
import unittest
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.onboardings import approval_service
from src.apis import onboardingApproval

class TestRollupResponseApproval(unittest.TestCase):
    def setUp(self):
        self.mock_cycle = {
            "id": 1,
            "cycle_type": "ROLLUP_RESPONSE",
            "parent_rollup_batch_id": 100,
            "company_id": 6,
            "reporting_year": 2026
        }
        
    def test_require_writable_cycle_tx_raises_409_when_sent(self):
        # Setup mock db and logic
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"transfer_status": "sent"}
        
        with self.assertRaises(ValueError) as ctx:
            approval_service.requireWritableCycleTx(mock_cur, self.mock_cycle, 6, batchId=100)
            
        self.assertIn("read-only", str(ctx.exception))
        
    def test_require_writable_cycle_tx_passes_when_not_sent(self):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"transfer_status": "not_sent"}
        
        # Should not raise
        try:
            approval_service.requireWritableCycleTx(mock_cur, self.mock_cycle, 6, batchId=100)
        except ValueError:
            self.fail("requireWritableCycleTx raised ValueError unexpectedly")

    @patch("src.services.onboardings.approval_service.getConn")
    @patch("src.services.onboardings.approval_service.resolveActiveCycleTx")
    def test_submit_approval_checks_batch_id(self, mock_resolve, mock_getConn):
        mock_resolve.return_value = self.mock_cycle
        
        # BatchId missing
        with self.assertRaises(ValueError) as ctx:
            approval_service.submitMetricApproval(
                companyId=6,
                reportingYear=2026,
                cycleType="ROLLUP_RESPONSE",
                metricId="G0-01",
                actorUserId=1,
                batchId=None
            )
        self.assertIn("batchId is required", str(ctx.exception))
        
        # BatchId mismatch
        with self.assertRaises(ValueError) as ctx2:
            approval_service.submitMetricApproval(
                companyId=6,
                reportingYear=2026,
                cycleType="ROLLUP_RESPONSE",
                metricId="G0-01",
                actorUserId=1,
                batchId=999
            )
        self.assertIn("ROLLUP_RESPONSE batch context mismatch", str(ctx2.exception))

if __name__ == "__main__":
    unittest.main()
