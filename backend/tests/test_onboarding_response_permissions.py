from unittest.mock import patch, MagicMock
from src.apis.onboarding import list_onboarding_metrics
import pytest

@pytest.mark.asyncio
async def test_list_onboarding_metrics_passes_user_model():
    with patch("src.apis.onboarding.listMetrics") as mock_listMetrics:
        with patch("src.apis.onboarding.checkScope") as mock_checkScope:
            user_model = {"id": 123, "role": "EMPLOYEE"}
            await list_onboarding_metrics(
                companyId=1,
                reportingYear=2024,
                cycleType="ROLLUP_RESPONSE",
                metricId=None,
                batchId=None,
                userModel=user_model
            )
            
            mock_listMetrics.assert_called_once_with(
                companyId=1,
                reportingYear=2024,
                cycleType="ROLLUP_RESPONSE",
                metricId=None,
                batchId=None,
                userModel=user_model
            )
