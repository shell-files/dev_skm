from fastapi import APIRouter, UploadFile, File
from src.models.model import  userUpdateModel, userDeleteModel, pwdCheckModel
from src.models.user import  updateUserProcess, deleteUserProcess
from src.models.auth import pwdCheckProcess

router = APIRouter()

# 비밀번호 확인
@router.post("",
              summary="비밀번호 확인",
              description="회원수정 버튼 누를때 비밀번호 확인")
def pwdCheck(pwdCheckModel: pwdCheckModel):
    return pwdCheckProcess(pwdCheckModel)

# 회원 정보 수정 API
@router.patch("", 
        summary="회원수정 api", 
        description="회원 정보를 수정합니다.")
def updateUser(userUpdateModel: userUpdateModel):
    return updateUserProcess(userUpdateModel)

# 회원 탈퇴 API
@router.delete("", 
        summary="회원탈퇴 api", 
        description="회원 탈퇴 처리(delete_yn)입니다.")
def deleteUser(userDeleteModel: userDeleteModel):
    return deleteUserProcess(userDeleteModel)
