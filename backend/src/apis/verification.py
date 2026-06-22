<<<<<<< HEAD
"""
verification.py
레이어: API Router
역할: 비밀번호 찾기 엔드포인트.

엔드포인트:
  PUT /  — 이메일로 비밀번호 찾기
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter
from src.models.model import EmailModel
from src.models.auth import findPwdProcess

router = APIRouter()
<<<<<<< HEAD


@router.put("",
        summary="비밀번호 찾기",
        description="비밀번호 찾기")
def findPwd(emailModel: EmailModel):
    return findPwdProcess(emailModel)
=======
# --------------------------
# 비밀번호 찾기 API
# --------------------------
@router.put("", 
        summary="비밀번호 찾기", 
        description="비밀번호 찾기")
def findPwd(emailModel: EmailModel):
    return findPwdProcess(emailModel)
>>>>>>> origin/skm_test
