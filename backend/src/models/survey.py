from pydantic import BaseModel


class SurveyCreateRequestDto(BaseModel):
    companyId: int
    runId: int
    year: int


class SurveyCreateResponseDto(BaseModel):
    status: str
    urls: dict
    sheet: dict