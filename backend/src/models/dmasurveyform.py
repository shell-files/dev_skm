"""
dmasurveyform.py
레이어: Model
역할: DMA 설문 폼 응답 DTO 정의.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DmaSurveyFormResponseDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., strict=True, gt=0)
    runId: int = Field(..., strict=True, gt=0)
    templateVersion: str
    surveyStatus: str
    top20Snapshot: list[dict]

    masterSheetId: Optional[str] = None
    employeeFormUrl: Optional[str] = None
    managementFormUrl: Optional[str] = None
    externalFormUrl: Optional[str] = None

    errorMessage: Optional[str] = None
    generatedAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
