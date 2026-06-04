from src.utils.tokenset import decryptFromJwe, refreshAccessToken
from src.utils.rediscl import getTokenRedis, setTokenRedis, delTokenRedis, getCompanyRedis, delCompanyRedis, setCompanyRedis
from src.utils.db import findOne, save
from src.models.model import ResponseModel

def validateToken(currentUuid: str):
    try:
        # 1. Redis에서 현재 UUID로 액세스 토큰 조회
        redisRes = getTokenRedis(currentUuid)

        # [방어 코드] 만약 다른 요청이 이미 토큰을 갱신해서 구 UUID가 삭제 중이거나 없을 때
        if not redisRes or not redisRes.get("status"):
            return ResponseModel(False, "세션이 존재하지 않습니다. 다시 로그인 해주세요.")

        accessJwe = redisRes["accessToken"]
        payload = decryptFromJwe(accessJwe)
        
        # --- [CASE: 액세스 토큰 만료 시 재발급 로직] ---
        if payload is None:
            userSql = """
                SELECT u.id, t.refresh_token 
                FROM `with`.`USER` u 
                JOIN `with`.`TOKEN` t ON u.id = t.user_id 
                WHERE t.uuid = ? AND u.delete_yn = 0 AND t.delete_yn = 0
                ORDER BY t.id DESC
            """
            userRecord = findOne(userSql, (currentUuid,))
            if userRecord is None:
                return ResponseModel(False, "로그인 정보가 만료되었습니다.")

            companyRedis = getCompanyRedis(currentUuid)
            if not companyRedis or companyRedis.get("status") is not True or companyRedis.get("companyId") is None:
                return ResponseModel(False, "선택 회사 정보를 찾을 수 없습니다.")

            # 새로운 액세스 토큰 및 UUID 생성
            newAccessToken, newUuid, user_id = refreshAccessToken(userRecord['refresh_token'])
            
            # DB 업데이트
            updateSql = "UPDATE `with`.`TOKEN` SET uuid = ?, updated_at = now() WHERE user_id = ? and uuid = ? ORDER BY created_at DESC LIMIT 1"
            save(updateSql, (newUuid, user_id, currentUuid))

            # 🚨 [개선] Redis 업데이트: 구 UUID를 '즉시 삭제'하지 말고 '유예' 시킵니다.
            # 동시 다발적 요청이 전부 처리될 수 있도록 신규 UUID를 먼저 등록합니다.
            setTokenRedis(newUuid, newAccessToken)
            setCompanyRedis(newUuid, int(companyRedis["companyId"]))
            
            # 구 UUID 데이터 삭제 (★중요: 만약 rediscl에 expire 기능이 있다면 5~10초 유예를 주면 완벽합니다)
            # 여기서는 즉시 지우더라도 신규 토큰 등록이 완료된 후 순차 처리되게 배치합니다.
            delTokenRedis(currentUuid)
            delCompanyRedis(currentUuid)

            # 결과에 새로 발급된 uuid임을 명시하는 플래그(is_updated)를 함께 주면 프론트나 라우터에서 처리하기 좋습니다.
            return ResponseModel(True, "성공적으로 조회하였습니다.", {"uuid": newUuid, "is_updated": True})

        # --- [CASE: 액세스 토큰이 아직 유효함] ---
        return ResponseModel(True, "액세스 토큰이 유효합니다.", {"uuid": currentUuid, "is_updated": False})

    except Exception as e:
        print(f"Auth Module Error: {e}")
        return ResponseModel(False, "오류 발생")