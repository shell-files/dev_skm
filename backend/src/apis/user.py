# apis/user.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] HTTP 요청 수신 후 models/user.py의 비즈니스 로직에 위임.
#        라우터는 요청/응답 처리만 담당, SQL 로직 포함하지 않음.
# [변경점] schemas/user.py 제거 → models/user.py에서 직접 import
# ────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter
from src.models.model import userUpdateModel, userDeleteModel
from src.models.user import updateUserProcess, deleteUserProcess

router = APIRouter()

# --------------------------
# 회원 정보 수정 API
# --------------------------
@router.patch("", 
        summary="회원수정 api", 
        description="회원 정보를 수정합니다.")
def updateUser(userUpdateModel: userUpdateModel):
    return updateUserProcess(userUpdateModel)

# --------------------------
# 회원 탈퇴 API
# --------------------------
@router.delete("", 
        summary="회원탈퇴 api", 
        description="회원 탈퇴 처리(delete_yn)입니다.")
def deleteUser(userDeleteModel: userDeleteModel):
    return deleteUserProcess(userDeleteModel)
