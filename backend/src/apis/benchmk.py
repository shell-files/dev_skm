from fastapi import APIRouter,  Form, Depends
from typing import List, Annotated
from src.services.benchmarks.service import uploadSr, findSr
from src.models.benchmk import FileModel, FileFindModel
from src.utils.auth import get_token


router = APIRouter()

# SR PDF 파일 업로드 및 저장, 불러오기 API
@router.post("",
        summary="SR PDF 파일 저장",
        description="파일 정보 DB저장")
async def fileRead(fileModel: Annotated[FileModel, Form()], userModel = Depends(get_token)):
  return uploadSr(fileModel, userModel)

# 벤치마킹 SR AI 분석 API
@router.put("",
        summary="SR PDF 파일 분석",
        description="분석 및 파일 정보 조회 후 분석 결과 추출")
async def fileAnalyze(fileFindModel: FileFindModel, userModel = Depends(get_token)):
  return await findSr(fileFindModel,userModel)
