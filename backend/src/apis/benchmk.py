<<<<<<< HEAD
"""
benchmk.py
레이어: API Router
역할: 벤치마킹 SR PDF 파일 업로드 및 AI 분석 엔드포인트.

엔드포인트:
  POST /  — SR PDF 파일 정보 DB 저장
  PUT  /  — SR PDF 파일 AI 분석 실행 및 결과 조회
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter, Form, Depends, HTTPException
from typing import List, Annotated
from src.services.benchmarks.service import uploadSr, findSr
from src.models.benchmk import FileModel, FileFindModel
from src.utils.auth import get_token


router = APIRouter()


@router.post("",
        summary="SR PDF 파일 저장",
        description="파일 정보 DB저장")
async def fileRead(fileModel: Annotated[FileModel, Form()], userModel = Depends(get_token)):
  return uploadSr(fileModel, userModel)


@router.put("",
        summary="SR PDF 파일 분석",
        description="분석 및 파일 정보 조회 후 분석 결과 추출")
async def fileAnalyze(fileFindModel: FileFindModel, userModel = Depends(get_token)):
    try:
        return await findSr(fileFindModel, userModel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
