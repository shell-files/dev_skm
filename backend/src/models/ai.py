from pydantic import BaseModel


class AiReportRequestDto(BaseModel):
    companyId: int
    runId: int
    year: int