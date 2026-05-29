from fastapi import APIRouter, Depends, Response, Request
from src.models.model import ResponseModel, logoutModel, pwdCheckModel
from src.models.auth import checkUser, logoutProcess, pwdCheckProcess
from src.utils.auth import get_token


router = APIRouter()

# 토큰 확인 API
@router.get("",
        summary="Token 확인 api",
        description="사용자 로그인 여부 반환")
async def tokenCheck(userModel = Depends(get_token)):
    if userModel:
        return ResponseModel(True, "")
    return ResponseModel(False, "로그인이 필요합니다.")

# 사용자 정보 불러오기 API
@router.post("",
        summary="사용자 정보 확인 api",
        description="사용자 & 회사 선택 정보 반환")
async def userCheck(userModel = Depends(get_token)):
    return checkUser(userModel)

# --------------------------
# 비밀번호 확인
# --------------------------

@router.patch("",
              summary="비밀번호 확인",
              description="회원수정 버튼 누를때 비밀번호 확인")
async def pwdCheck(request: Request, pwdCheckModel: pwdCheckModel):
    
    # 3. 여기에서 request를 넘겨주어야 합니다!
    return pwdCheckProcess(request, pwdCheckModel)

# --------------------------
# 로그아웃 API
# --------------------------
@router.delete("",
        summary="로그아웃 api",
        description="deleteYn 0 : 로그인 상태 / 1 : 로그아웃")
def userDel(response: Response, request: Request, userModel = Depends(get_token)):
    return logoutProcess(response, request, userModel)

