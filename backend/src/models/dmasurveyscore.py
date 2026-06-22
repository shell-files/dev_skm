"""
dmasurveyscore.py
레이어: Model
역할: DMA 설문 점수 미리보기·재산정 결과 DTO 정의.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SurveyScorePreviewDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int
    surveyFormId: int
    activeResponseCount: int
    scorableResponseCount: int
    excludedResponseCount: int
    scoredSubIssueCount: int
    scores: list[dict]


class SurveyScoreRecalculateResultDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runId: int
    surveyFormId: int
    activeResponseCount: int
    scorableResponseCount: int
    excludedResponseCount: int
    scoredSubIssueCount: int
    affectedSubIssueCount: int
    finalRecalculatedCount: int
    rankUpdatedCount: int
    status: str
