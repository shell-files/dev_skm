"""
dmasurveyresponsestatus.py
레이어: Model
역할: DMA 설문 응답 현황(그룹별 참여율) DTO 정의.
"""
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict


class SurveyGroupStatusDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    targetCount: int
    responseCount: int
    responseRate: float


class SurveyTotalsDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targetCount: int
    responseCount: int
    responseRate: float


class SurveyResponseStatusDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int
    surveyFormId: Optional[int] = None
    surveyStatus: Optional[str] = None
    masterSheetId: Optional[str] = None
    lastImportedAt: Optional[str] = None
    groups: Dict[str, SurveyGroupStatusDto]
    totals: Optional[SurveyTotalsDto] = None


class SurveyResponseTargetsRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: Dict[str, int]
