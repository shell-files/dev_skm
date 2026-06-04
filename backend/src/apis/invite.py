from fastapi import APIRouter

from src.models.model import ResponseModel, inviteSignUpUserInfo
from src.utils.rediscl import getInviteRedis
from src.utils.tokenset import decryptFromJwe
from src.utils.invite import inviteProcess, inviteSignUp

from src.utils.kafkasv import startConsumer


router = APIRouter()
@router.on_event("startup")
def startup_event():
    startConsumer()

@router.get("/{inviteId}",
            summary="초대 링크 접속",
            description="초대 링크 접속 시 회원가입 폼을 렌더링하는 API입니다.")
def invite(inviteId: str):
  return inviteProcess(inviteId)
  

@router.post("/{inviteId}", 
             summary="초대 링크 data 처리",
             description="초대 링크 접속 시 토큰에서 이메일과 회사명 추출하여 반환하는 API입니다.")
def invite(inviteId: str):
  inviteData = getInviteRedis(inviteId)
  if not inviteData or inviteData.get("status") is not True or not inviteData.get("token"):
    return ResponseModel(False, "초대 토큰을 찾을 수 없습니다.")

  try:
    payload = decryptFromJwe(inviteData["token"])
  except Exception:
    return ResponseModel(False, "초대 토큰이 유효하지 않습니다.")
  if not payload:
    return ResponseModel(False, "초대 토큰이 유효하지 않습니다.")

  email = payload.get("email")
  companyName = payload.get("sub")

  data = { "companyName": companyName, "email": email, "name": "", "password": "" }
  return ResponseModel(True, "초대 링크 데이터가 성공적으로 처리되었습니다.", data)

@router.put("/{inviteId}",
             summary="초대 링크로 회원가입",
             description="초대 링크로 회원가입을 처리하는 API입니다.")
def invite(inviteId: str, inviteSignUpUserInfo: inviteSignUpUserInfo):
  return inviteSignUp(inviteId, inviteSignUpUserInfo)
