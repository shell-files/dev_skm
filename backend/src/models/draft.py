from pydantic import BaseModel
from typing import Dict


class DraftSaveRequestDto(BaseModel):
    companyId: int
    year: int
    # { pageKey: { atomicMetricId: displayValue } }
    metrics: Dict[str, Dict[str, str]] = {}
    # { pageKey: narrativeText }
    narrative: Dict[str, str] = {}
