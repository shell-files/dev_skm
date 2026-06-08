from fastapi import APIRouter, Depends

from src.utils.auth import get_token
from src.models.survey import SurveyCreateRequestDto

from src.services.surveys.service import (createFormProcess, exportCsvProcess, getRawProcess, getSurveyResultProcess)

router = APIRouter()

@router.post("",
    summary="설문 생성",
    description="구글 설문 생성"
)
async def createForm(req: SurveyCreateRequestDto, token=Depends(get_token)):
    return await createFormProcess(req, token)


@router.get("/{sheet_id}",
    summary="설문 결과 CSV 추출",
    description="구글 시트 응답 데이터 CSV 생성 DB 저장 X"
)
async def exportCsv(sheet_id: str, token=Depends(get_token)):
    return await exportCsvProcess(sheet_id, token)

@router.get("/result/{sheet_id}",
    summary="설문 응답 현황"
)
async def getSurveyResult(sheet_id: str, token=Depends(get_token)
):
    return await getSurveyResultProcess(sheet_id, token)

@router.get("/raw",
    summary="설문 템플릿 조회"
)
def getRaw():
    return getRawProcess()