"""
validatetok.py
레이어: Utils
역할: 세션 토큰 검증 — UUID 기반 Redis 조회 및 만료 시 자동 갱신.
"""
from src.utils.tokenset import decryptFromJwe, refreshAccessToken
from src.utils.rediscl import getTokenRedis, setTokenRedis, delTokenRedis, getCompanyRedis, delCompanyRedis, setCompanyRedis, setRotatedTokenRedis, getRotatedTokenRedis
from src.utils.db import findOne, save
from src.models.model import ResponseModel

def validateToken(currentUuid: str):
    """
    UUID로 Redis 세션을 검증한다.
    동시 요청 Race Condition을 방지하기 위해 rotatedKey를 먼저 확인하며,
    액세스 토큰 만료 시 refresh token으로 재발급하고 구 UUID를 30초간 유예한다.
    """
    try:
        # 0. 다른 동시 요청이 이미 이 UUID를 갱신했는지 먼저 확인 (Race Condition 방지)
        rotatedRes = getRotatedTokenRedis(currentUuid)
        if rotatedRes.get("status"):
            newUuid = rotatedRes["newUuid"]
            return ResponseModel(True, "성공적으로 조회하였습니다.", {"uuid": newUuid, "is_updated": True})

        # 1. Redis에서 현재 UUID로 액세스 토큰 조회
        redisRes = getTokenRedis(currentUuid)

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

            # 구 UUID → 신 UUID 매핑을 30초간 Redis에 보존 (동시 요청 Race Condition 방지)
            # 이후 도착하는 동시 요청들이 DB 조회 없이 신 UUID를 바로 받아 처리됨
            setRotatedTokenRedis(currentUuid, newUuid, 30)
            delTokenRedis(currentUuid)
            delCompanyRedis(currentUuid)

            return ResponseModel(True, "성공적으로 조회하였습니다.", {"uuid": newUuid, "is_updated": True})

        # --- [CASE: 액세스 토큰이 아직 유효함] ---
        return ResponseModel(True, "액세스 토큰이 유효합니다.", {"uuid": currentUuid, "is_updated": False})

    except Exception as e:
        print(f"Auth Module Error: {e}")
        return ResponseModel(False, "오류 발생")