from typing import List, Literal, Optional

from pydantic import BaseModel, Field


G0ProfileStatus = Literal["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "STALE"]


class G0ProfileItemDto(BaseModel):
    metricId: str
    atomicMetricId: str
    metricName: Optional[str] = None
    atomicName: Optional[str] = None
    valueText: Optional[str] = None
    valueNumeric: Optional[float] = None
    unit: Optional[str] = None
    requiredYn: bool = True
    updatedAt: Optional[str] = None


class G0ProfileResponseDto(BaseModel):
    companyId: int
    reportingYear: int
    g0ProfileStatus: G0ProfileStatus
    items: List[G0ProfileItemDto] = Field(default_factory=list)
    missingRequiredItems: List[G0ProfileItemDto] = Field(default_factory=list)
    message: str = "OK"
    implementationStatus: str = "READY"


class G0ProfileStatusResponseDto(BaseModel):
    companyId: int
    reportingYear: int
    g0ProfileStatus: G0ProfileStatus
    requiredItemCount: int = 0
    completedRequiredItemCount: int = 0
    missingRequiredItemCount: int = 0
    message: str = "OK"
    implementationStatus: str = "READY"


class G0ProfileUpsertItemDto(BaseModel):
    metricId: str
    atomicMetricId: str
    valueText: Optional[str] = None
    valueNumeric: Optional[float] = None
    unit: Optional[str] = None


class G0ProfileUpsertRequestDto(BaseModel):
    reportingYear: int
    items: List[G0ProfileUpsertItemDto]


class G0ProfileUpsertResponseDto(BaseModel):
    companyId: int
    reportingYear: int
    savedItemCount: int = 0
    g0ProfileStatus: G0ProfileStatus
    message: str = "OK"
    implementationStatus: str = "READY"
