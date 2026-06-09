from fastapi import APIRouter, Depends
from src.models.model import CompanyModel
from src.models.company import companyProcess
from src.utils.auth import get_token

router = APIRouter()

# --------------------------
# 회사 선택 API
# --------------------------
@router.post("",
        summary="회사 선택 api",
        description="회사 ID를 받아서 redis에 저장")
def company(companyModel: CompanyModel, userModel = Depends(get_token)):
    return companyProcess(companyModel, userModel)
