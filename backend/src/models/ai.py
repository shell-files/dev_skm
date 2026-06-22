<<<<<<< HEAD
"""
ai.py
레이어: Model
역할: AI ESG 보고서 생성 요청 DTO 정의.
"""
=======
>>>>>>> origin/skm_test
from pydantic import BaseModel


class AiReportRequestDto(BaseModel):
    companyId: int
    materialityRunId: int
    year: int