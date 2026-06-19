"""
inviteMember.py
레이어: API Router
역할: 내부 직원 초대 엔드포인트.

엔드포인트:
  POST /  — 내부 직원 초대 (role: 4 부서담당자)
"""
from fastapi import APIRouter, Depends
from src.models.model import inviteMemberModel
from src.utils.auth import get_token
from src.utils.invite import inviteMember

router = APIRouter()


@router.post("",
             summary="내부 직원 초대",
             description="내부 직원을 초대하는 API입니다. 4: 부서담당자")
def inviteMember(inviteMemberModel, userModel = Depends(get_token)):
    return inviteMember(inviteMemberModel, userModel)
