"""
user.py
레이어: API Router
역할: 회원 정보 수정·탈퇴 엔드포인트.

엔드포인트:
  PATCH  /  — 회원 정보 수정
  DELETE /  — 회원 탈퇴
"""
from fastapi import APIRouter, Request
from src.models.model import userUpdateModel, userDeleteModel
from src.models.user import updateUserProcess, deleteUserProcess

router = APIRouter()


@router.patch("",
        summary="회원수정 api",
        description="회원 정보를 수정합니다.")
async def updateUser(request: Request, userUpdateModel: userUpdateModel):
    return updateUserProcess(request, userUpdateModel)


@router.delete("",
        summary="회원탈퇴 api",
        description="회원 탈퇴 처리입니다.")
def deleteUser(request: Request):
    return deleteUserProcess(request)
