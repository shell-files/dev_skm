from fastapi import APIRouter, UploadFile, File, Form
from src.utils.file import uploadSr
from typing import List

router = APIRouter()

# SR PDF 파일 업로드 및 저장, 불러오기 API
@router.post("",
        summary="SR PDF 파일 분석",
        description="분석 및 파일 정보 DB저장")
async def fileRead(files:List[UploadFile] = File(), type:str = Form()):
   return uploadSr(files, type)
