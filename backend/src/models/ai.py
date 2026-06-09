from pydantic import BaseModel


class AiReportRequestDto(BaseModel):
    companyId: int
    materialityRunId: int
    year: int