from fastapi import APIRouter, Depends, HTTPException

from src.models.report import (
    ReportDownloadRequestDto,
    ReportDownloadResponseDto,
    ReportDraftPatchRequestDto,
    ReportDraftPatchResponseDto,
    ReportDraftResponseDto,
    ReportTraceResponseDto,
)
from src.services.reports.service import (
    createReportDownload,
    getParagraphTrace,
    getReportDrafts,
    patchReportDraft,
)
from src.utils.auth import get_token


router = APIRouter(tags=["report"])


@router.get("/drafts/{runId}", response_model=ReportDraftResponseDto, summary="보고서 초안 조회")
async def get_report_drafts(runId: int, userModel=Depends(get_token)):
    try:
        return getReportDrafts(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/drafts/{draftId}", response_model=ReportDraftPatchResponseDto, summary="보고서 문단 수정 저장")
async def patch_report_draft(draftId: int, request: ReportDraftPatchRequestDto, userModel=Depends(get_token)):
    try:
        return patchReportDraft(draftId, request.editedText)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/drafts/{runId}/paragraphs/{paragraphId}/trace",
    response_model=ReportTraceResponseDto,
    summary="문단별 데이터 추적 조회",
)
async def get_report_paragraph_trace(runId: int, paragraphId: int, userModel=Depends(get_token)):
    try:
        return getParagraphTrace(runId, paragraphId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{runId}/download", response_model=ReportDownloadResponseDto, summary="보고서 다운로드 생성")
async def download_report_draft(runId: int, request: ReportDownloadRequestDto, userModel=Depends(get_token)):
    try:
        return createReportDownload(runId, request.fileType)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
