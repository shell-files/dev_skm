<<<<<<< HEAD
"""
company.py
레이어: API Router
역할: 회사 선택 엔드포인트 — 선택한 회사 ID를 Redis에 저장.

엔드포인트:
  POST /  — 회사 선택 (회사 ID → Redis 저장)
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter, Depends
from src.models.model import CompanyModel
from src.models.company import companyProcess
from src.utils.auth import get_token

router = APIRouter()

<<<<<<< HEAD

=======
# --------------------------
# 회사 선택 API
# --------------------------
>>>>>>> origin/skm_test
@router.post("",
        summary="회사 선택 api",
        description="회사 ID를 받아서 redis에 저장")
def company(companyModel: CompanyModel, userModel = Depends(get_token)):
    return companyProcess(companyModel, userModel)
