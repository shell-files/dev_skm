"""
dmaworkflowstatus.py
레이어: Model
역할: DMA 워크플로우 진행 상태 응답 DTO 정의.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DmaWorkflowStatusResponseDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int = Field(..., strict=True, gt=0)
    workflowType: str
    overallStatus: str
    currentStage: str
    progressPercent: int = Field(..., ge=0, le=100)
    progressMode: str

    processedCount: Optional[int] = Field(default=None, ge=0)
    totalCount: Optional[int] = Field(default=None, ge=0)

    errorStage: Optional[str] = None
    errorMessage: Optional[str] = None

    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
