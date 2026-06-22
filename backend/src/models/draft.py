"""
draft.py
레이어: Model
역할: ESG 보고서 초안 저장 요청 DTO 정의.
"""
from pydantic import BaseModel
from typing import Dict


class DraftSaveRequestDto(BaseModel):
    companyId: int
    year: int
    # { pageKey: { atomicMetricId: displayValue } }
    metrics: Dict[str, Dict[str, str]] = {}
    # { pageKey: narrativeText }
    narrative: Dict[str, str] = {}
    # { pageKey: subIssueId } — section_id / ai_run_id auto-lookup 용
    pageSubIssueMap: Dict[str, str] = {}
