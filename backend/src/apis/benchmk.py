from fastapi import APIRouter, UploadFile, File
from src.utils.file import uploadSr
from src.models.model import SrFileModel

router = APIRouter()

# SR PDF 파일 업로드 및 저장, 불러오기 API
@router.post("",
        summary="SR PDF 파일 분석",
        description="분석 및 파일 정보 DB저장")
async def fileRead(SrFileModel:SrFileModel):
   return uploadSr(SrFileModel)
