from fastapi import APIRouter, Depends
from src.models.model import ResponseModel
from src.models.auth import checkUser
from src.utils.auth import get_token

router = APIRouter()

# 토큰 확인 API
@router.get("",
        summary="Token 확인 api",
        description="사용자 로그인 여부 반환")
async def tokenCheck(userModel = Depends(get_token)):
    if userModel:
        return ResponseModel(True, "")
    return ResponseModel(False, "로그인이 필요합니다.")

# 사용자 정보 불러오기 API
@router.post("",
        summary="사용자 정보 확인 api",
        description="사용자 & 회사 선택 정보 반환")
async def userCheck(userModel = Depends(get_token)):
    return checkUser(userModel)