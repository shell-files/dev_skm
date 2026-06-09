from src.models.model import UserModel, CompanyModel, ResponseModel
from src.utils.rediscl import setCompanyRedis

# --------------------------
# 회사 선택 함수
# --------------------------
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
