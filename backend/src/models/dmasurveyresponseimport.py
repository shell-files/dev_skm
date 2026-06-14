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
