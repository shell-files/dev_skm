"""
company.py
레이어: Model / Service
역할: 회사 선택 처리 — UUID와 companyId를 Redis에 저장.

주요 함수:
  companyProcess — Redis에 선택 회사 저장
"""
from src.models.model import UserModel, CompanyModel, ResponseModel
from src.utils.rediscl import setCompanyRedis


def companyProcess(companyModel: CompanyModel, userModel: UserModel):
    """
    1. redis에서 uuid 와 companyId 저장
    """
    try:
        status = setCompanyRedis(userModel.uuid, companyModel.companyId)
        if status:
            return ResponseModel(True, "")
    except Exception as e:
        return ResponseModel(False, f"오류 발생 : {e}")
