from fastapi import APIRouter, Response, Depends
from src.models.model import ResponseModel
from src.models.auth import checkUser
from src.utils.auth import get_token

router = APIRouter()

# 토큰 확인 API
@router.get("",
        summary="Token 확인 api",
        description="사용자 여부 반환")
async def tokenCheck():
    return ResponseModel(True, "")

@router.post("")
async def userCheck(userModel = Depends(get_token)):
    return checkUser(userModel)