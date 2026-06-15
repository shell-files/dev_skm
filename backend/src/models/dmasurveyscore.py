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
