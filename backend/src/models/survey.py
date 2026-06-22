"""
survey.py
레이어: Model
역할: 설문 생성 요청 및 응답 DTO 정의.
"""
from pydantic import BaseModel


class SurveyCreateRequestDto(BaseModel):
    companyId: int
    runId: int
    year: int


class SurveyCreateResponseDto(BaseModel):
    status: str
    urls: dict
    sheet: dict