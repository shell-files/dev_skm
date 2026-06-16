from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KcgsGradeRowDto(BaseModel):
    """모달에서 입력하는 단일 연도 KCGS 등급 행."""

    model_config = ConfigDict(extra="forbid")

    ratingYear: int = Field(..., ge=2000, le=2100)
    overallGrade: str = Field(..., min_length=1)
    environmentGrade: str = Field(..., min_length=1)
    socialGrade: str = Field(..., min_length=1)
    governanceGrade: str = Field(..., min_length=1)
    sourceDocumentRef: Optional[str] = None


class KcgsGradeSaveRequest(BaseModel):
    """KCGS 등급 저장 요청. 점수 반영을 위해 정확히 3개 연속 연도가 필요하다."""

    model_config = ConfigDict(extra="forbid")

    companyId: int = Field(..., gt=0)
    grades: List[KcgsGradeRowDto]


class KcgsGradeSaveResponse(BaseModel):
    companyId: int
    savedCount: int
    reviewStatus: str
