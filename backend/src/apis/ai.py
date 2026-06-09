from fastapi import APIRouter, Depends

from src.utils.auth import get_token
from src.models.ai import AiReportRequestDto

from src.services.ai.service import generateReportProcess
import time

router = APIRouter()


@router.post("",
    summary="ESG 보고서 생성",
    description="ESG 보고서 자동 생성"
)
async def generateReport(req: AiReportRequestDto, token=Depends(get_token)):
    start = time.time()

    result = generateReportProcess(req, token)

    end = time.time()
    print(f"[TOTAL TIME] {end - start:.3f}s")

    return result