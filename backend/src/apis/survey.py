<<<<<<< HEAD
"""
survey.py
레이어: API Router
역할: 설문 생성·조회·응답 Import·점수 계산·현황 관리 엔드포인트.

엔드포인트:
  POST /                              — 구글 설문 생성
  GET  /raw                           — 설문 템플릿 조회
  GET  /form/{runId}                  — 설문 폼 상태 조회
  POST /form/{runId}/retry            — 설문 폼 재시도
  GET  /form/{runId}/responses/preview   — 응답 Import Preview (DB 저장 없음)
  POST /form/{runId}/responses/import    — 응답 Import (ESG_DMA_SURVEY_RESPONSE UPSERT)
  GET  /form/{runId}/scores/preview      — 점수 계산 Preview (DB 저장 없음)
  POST /form/{runId}/scores/recalculate  — 점수 계산 및 Final Score 재계산
  GET  /form/{runId}/response-status     — 응답 현황 조회
  PUT  /form/{runId}/response-targets    — 목표 응답자 수 저장
  GET  /{sheet_id}                    — 설문 결과 CSV 추출
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter, Depends, HTTPException

from src.utils.auth import get_token
from src.models.survey import SurveyCreateRequestDto
from src.models.dmasurveyform import DmaSurveyFormResponseDto
from src.models.dmasurveyresponseimport import SurveyImportResultDto, SurveyImportPreviewDto
from src.models.dmasurveyscore import SurveyScorePreviewDto, SurveyScoreRecalculateResultDto
from src.models.dmasurveyresponsestatus import SurveyResponseStatusDto, SurveyResponseTargetsRequestDto

from src.services.surveys.service import exportCsvProcess, getRawProcess
<<<<<<< HEAD
from src.services.surveys.formservice import createFormProcess, ensureSurveyFormForRun, getSurveyFormDetail
=======
from src.services.surveys.formservice import createFormProcess, ensureSurveyFormForRun
>>>>>>> origin/skm_test
from src.services.surveys.importservice import (
    importSurveyResponsesForRun,
    previewSurveyResponses,
)
from src.services.surveys.scoringservice import (
    previewSurveyScores,
    recalculateSurveyScoresForRun,
)
from src.services.surveys.statusservice import getSurveyResponseStatus, saveSurveyResponseTargets
<<<<<<< HEAD
=======
from src.utils.dmasurveyformrepository import getSurveyFormByRunId, toSurveyFormResponse
>>>>>>> origin/skm_test

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
<<<<<<< HEAD
        result = getSurveyFormDetail(runId)
=======
        row = getSurveyFormByRunId(runId)
>>>>>>> origin/skm_test
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
<<<<<<< HEAD
    if result is None:
        raise HTTPException(status_code=404, detail=f"Survey form not found for runId={runId}")
    return result
=======
    if row is None:
        raise HTTPException(status_code=404, detail=f"Survey form not found for runId={runId}")
    return toSurveyFormResponse(row)
>>>>>>> origin/skm_test


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
    "/form/{runId}/scores/preview",
    response_model=SurveyScorePreviewDto,
    summary="Survey 점수 계산 Preview (DB 저장 없음)",
)
async def preview_survey_scores(runId: int, token=Depends(get_token)):
    try:
        return previewSurveyScores(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/form/{runId}/scores/recalculate",
    response_model=SurveyScoreRecalculateResultDto,
    summary="Survey 점수 계산 및 Final Score / rank_no 재계산",
)
async def recalculate_survey_scores(runId: int, token=Depends(get_token)):
    try:
        return recalculateSurveyScoresForRun(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/form/{runId}/response-status",
    response_model=SurveyResponseStatusDto,
    summary="설문 응답 현황 조회 (form 없어도 targets + zero counts 반환)",
)
async def get_survey_response_status(runId: int, token=Depends(get_token)):
    try:
        return getSurveyResponseStatus(runId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/form/{runId}/response-targets",
    response_model=SurveyResponseStatusDto,
    summary="설문 목표 응답자 수 저장 후 최신 응답 현황 반환",
)
async def put_survey_response_targets(
    runId: int,
    req: SurveyResponseTargetsRequestDto,
    token=Depends(get_token),
):
    try:
        return saveSurveyResponseTargets(runId, req.targets)
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
