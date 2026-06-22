<<<<<<< HEAD
"""
dmasurveyresponseimport.py
레이어: Model
역할: DMA 설문 응답 데이터 가져오기 결과·미리보기 DTO 정의.
"""
=======
>>>>>>> origin/skm_test
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SurveyImportResultDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int
    surveyFormId: int
    masterSheetId: str
    importedRowCount: int
    insertedCount: int
    updatedCount: int
    skippedCount: int
    respondentCounts: dict
    status: str


class SurveyImportPreviewDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int
    surveyFormId: int
    masterSheetId: str
    metaSheets: dict
    responseSheets: list[str]
    previewRows: list[dict]
