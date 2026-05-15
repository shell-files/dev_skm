from fastapi import APIRouter
from src.models.model import inviteMemberModel, responseModel
from src.utils.tokenset import decryptFromJwe
from src.utils.rediscl import getTokenRedis
from src.utils.validatetok import validateToken
from src.utils.db import findOne, save, addKey
from src.utils.tokenset import generateInviteTokenWithUuid
from src.utils.rediscl import setInviteRedis
from src.utils.kafkasv import sendToKafka

router = APIRouter()
@router.post("",
             summary="내부 직원 초대",
             description="내부 직원을 초대하는 API입니다. 4: 부서담당자")
def inviteMember(inviteMemberModel: inviteMemberModel):
    try:
        # 1. 세션 검증 및 자동 갱신 모듈 호출
        # 이 한 줄로 Redis 조회, Access 만료 체크, Refresh 재발급, DB/Redis 업데이트가 완료됩니다.
        authResponse = validateToken(inviteMemberModel.uuid)
        
        # 인증 실패 시 (세션 만료, 리프레시 만료 등) 그대로 반환
        if not authResponse["status"]:
            return authResponse

        # 2. 검증 통과 후 최신 UUID 획득
        # 재발급되었다면 신규 UUID가, 유효하다면 기존 UUID가 들어있습니다.
        activeUuid = authResponse["data"]["uuid"]

        # 3. 최신 UUID를 통해 유저 ID(sub) 추출
        # Redis에서 토큰을 가져와 복호화하여 sub(userId)를 얻습니다.
        tokenRes = getTokenRedis(activeUuid)
        payload = decryptFromJwe(tokenRes["accessToken"])
        userId = payload.get("sub")
        selectSql = f"SELECT company_name, id FROM `COMPANY` WHERE user_id = ?"
        selectParams = (userId,)
        company = findOne(selectSql, selectParams)
        
        for email in inviteMemberModel.email:
            # DB에 초대 정보 저장
            inviteSql = f"INSERT INTO `INVITE` (company_id, user_id, role_id, project_id, email) values (?, ?, ?, ?, ?)"
            inviteParams = (company["id"], userId, inviteMemberModel.role, inviteMemberModel.projectId, email)
            result = addKey(inviteSql, inviteParams)

            if not result[0]:  # DB 저장 실패 시
                return responseModel(False, "초대 정보 저장에 실패했습니다.")

            inviteId = result[1]

            # 받는 사람 이메일, 이슈 그룹, 권한 정보 토큰화
            token, uuid = generateInviteTokenWithUuid(inviteMemberModel.issue, company["company_name"], email, inviteMemberModel.role, inviteMemberModel.projectId, inviteId, company["id"])

            # Redis에 초대 토큰 저장
            setInviteRedis(uuid, token)
        
            # 메일 발송
            mailData = {"type": 1, "uuid": uuid}
            sendToKafka(mailData)
            
        return responseModel(True, "초대장이 성공적으로 발송되었습니다.")
    except Exception as e:
        return responseModel(False, f"인증 오류 발생 : {e}")