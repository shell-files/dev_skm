"""
auth.py
레이어: API Router
역할: 인증 관련 엔드포인트 — 토큰 확인, 로그인, 사용자 정보 확인, 비밀번호 확인, 로그아웃.

엔드포인트:
  GET    /  — 토큰 확인 (로그인 여부 반환)
  POST   /login  — 이메일/비밀번호 로그인 (uuid 반환)
  POST   /  — 사용자 정보 확인
  PATCH  /  — 비밀번호 확인
  DELETE /  — 로그아웃
"""
from fastapi import APIRouter, Depends, Response, Request
from src.models.model import ResponseModel, pwdCheckModel, LoginModel
from src.models.auth import checkUser, logoutProcess, pwdCheckProcess, loginProcess
from src.utils.auth import get_token


router = APIRouter()


@router.get("",
        summary="Token 확인 api",
        description="사용자 로그인 여부 반환")
async def tokenCheck(userModel = Depends(get_token)):
    if userModel:
        return ResponseModel(True, "")
    return ResponseModel(False, "로그인이 필요합니다.")


@router.post("/login",
        summary="로그인 api",
        description="email/pwd 받아서 uuid 반환")
def login(response: Response, request: Request, loginModel: LoginModel):
    return loginProcess(response, request, loginModel)


@router.post("",
        summary="사용자 정보 확인 api",
        description="사용자 & 회사 선택 정보 반환")
async def userCheck(userModel = Depends(get_token)):
    return checkUser(userModel)


@router.patch("",
              summary="비밀번호 확인",
              description="회원수정 버튼 누를때 비밀번호 확인")
async def pwdCheck(request: Request, pwdCheckModel: pwdCheckModel):
    # 3. 여기에서 request를 넘겨주어야 합니다!
    return pwdCheckProcess(request, pwdCheckModel)


@router.delete("",
        summary="로그아웃 api",
        description="deleteYn 0 : 로그인 상태 / 1 : 로그아웃")
def userDel(response: Response, request: Request, userModel = Depends(get_token)):
    return logoutProcess(response, request, userModel)
