from fastapi import APIRouter
from src.models.model import EmailModel
from src.models.auth import findPwdProcess

router = APIRouter()
# --------------------------
# 비밀번호 찾기 API
# --------------------------
@router.put("", 
        summary="비밀번호 찾기", 
        description="비밀번호 찾기")
def findPwd(emailModel: EmailModel):
    return findPwdProcess(emailModel)