from fastapi import APIRouter, Depends, HTTPException

from src.utils.auth import get_token
from src.models.survey import SurveyCreateRequestDto
from src.models.dmasurveyform import DmaSurveyFormResponseDto
from src.models.dmasurveyresponseimport import SurveyImportResultDto, SurveyImportPreviewDto

from src.services.surveys.service import exportCsvProcess, getRawProcess
from src.services.surveys.formservice import createFormProcess, ensureSurveyFormForRun
from src.services.surveys.importservice import (
    importSurveyResponsesForRun,
    previewSurveyResponses,
)
from src.utils.dmasurveyformrepository import getSurveyFormByRunId, toSurveyFormResponse

router = APIRouter()


@router.post(
    "",
    summary="설문 생성",
    description="구글 설문 생성",
)
async def createForm(req: SurveyCreateRequestDto, token=Depends(get_token)):
    return await createFormProcess(req, token)


@router.get(
    "/raw",
    summary="설문 템플릿 조회",
)
def getRaw():
    return getRawProcess()


@router.get(
    "/form/{runId}",
    response_model=DmaSurveyFormResponseDto,
    summary="설문 폼 상태 조회",
)
async def get_survey_form(runId: int, token=Depends(get_token)):
    try:
        row = getSurveyFormByRunId(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail=f"Survey form not found for runId={runId}")
    return toSurveyFormResponse(row)


@router.post(
    "/form/{runId}/retry",
    response_model=DmaSurveyFormResponseDto,
    summary="설문 폼 재시도",
)
async def retry_survey_form(runId: int, token=Depends(get_token)):
    try:
        result = ensureSurveyFormForRun(runId)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/form/{runId}/responses/preview",
    response_model=SurveyImportPreviewDto,
    summary="설문 응답 Import Preview (DB 저장 없음)",
)
async def preview_survey_responses(runId: int, token=Depends(get_token)):
    try:
        return previewSurveyResponses(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/form/{runId}/responses/import",
    response_model=SurveyImportResultDto,
    summary="설문 응답 Import (ESG_DMA_SURVEY_RESPONSE UPSERT)",
)
async def import_survey_responses(runId: int, token=Depends(get_token)):
    try:
        return importSurveyResponsesForRun(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{sheet_id}",
    summary="설문 결과 CSV 추출",
    description="구글 시트 응답 데이터 CSV 생성 DB 저장 X",
)
async def exportCsv(sheet_id: str, token=Depends(get_token)):
    return await exportCsvProcess(sheet_id, token)
