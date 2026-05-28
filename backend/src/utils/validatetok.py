import uuid
from src.utils.token import decryptFromJwe, refreshAccessToken
from src.utils.rediscl import getTokenRedis, setTokenRedis, delTokenRedis, getCompanyRedis, delCompanyRedis, setCompanyRedis
from src.utils.db import findOne, save
from src.models.model import ResponseModel, UserModel, CompanyModel

def validateToken(currentUuid: str):
    """
    UUID를 기반으로 액세스 토큰을 검증하고, 
    만료 시 리프레시 토큰을 통해 세션을 자동 갱신하는 통합 모듈
    """
    try:
        # 1. Redis에서 현재 UUID로 액세스 토큰 조회
        redisRes = getTokenRedis(currentUuid)

        if not redisRes["status"]:
            return ResponseModel(False, "세션이 존재하지 않습니다. 다시 로그인 해주세요.")

        accessJwe = redisRes["accessToken"]
        # 2. 액세스 토큰 유효성 검사 (복호화)
        payload = decryptFromJwe(accessJwe)
        # --- [CASE: 액세스 토큰 만료 시 재발급 로직] ---
        if payload is None:
            # DB에서 UUID를 통해 리프레시 토큰 조회
            # (TOKEN 테이블과 USER 테이블 조인하여 유효성 확인)
            userSql = """
                SELECT u.id, t.refresh_token 
                FROM `with`.`USER` u 
                JOIN `with`.`TOKEN` t ON u.id = t.user_id 
                WHERE t.uuid = ? AND u.delete_yn = 0 AND t.delete_yn = 0
                ORDER BY t.id DESC
            """
            userRecord = findOne(userSql, (currentUuid,))
            if userRecord is None :
                return ResponseModel(False, "로그인 정보가 만료되었습니다.")

            # 새로운 액세스 토큰 및 UUID 생성
            newAccessToken, newUuid, user_id = refreshAccessToken(userRecord['refresh_token'])
            # DB 업데이트: TOKEN 테이블의 uuid 수정
            updateSql = "UPDATE `with`.`TOKEN` SET uuid = ?, updated_at = now() WHERE user_id = ? and uuid = ? ORDER BY created_at DESC LIMIT 1"
            save(updateSql, (newUuid, user_id, currentUuid))

            # Redis 업데이트: 구 UUID 삭제 후 신규 등록
            delTokenRedis(currentUuid)
            setTokenRedis(newUuid, newAccessToken)
            companyRedis = getCompanyRedis(currentUuid)
            if companyRedis is None:
                return ResponseModel(False, "Redis 오류 발생")
            delCompanyRedis(currentUuid)
            setCompanyRedis(newUuid, int(companyRedis.get("companyId")))

            return ResponseModel(True, "성공적으로 조회하였습니다.", {"uuid": newUuid} )

        # --- [CASE: 액세스 토큰이 아직 유효함] ---
        return ResponseModel(True, "액세스 토큰이 유효합니다.",{"uuid": currentUuid})

    except Exception as e:
        print(f"Auth Module Error: {e}")
        return ResponseModel(False, "오류 발생")
    
