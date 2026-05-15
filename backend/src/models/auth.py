from src.utils.db import findAll
from src.utils.tokenset import decryptFromJwe
from src.utils.rediscl import getTokenRedis
from src.utils.validatetok import validateToken


# --------------------------
# 비밀번호 확인 로직 처리 함수
# --------------------------  
def pwdCheckProcess(pwdCheckModel):
    """
    비밀번호 확인 프로세스:
    1. 통합 인증 모듈을 통한 토큰 검증 및 자동 갱신
    2. 최신 UUID를 기반으로 유저 정보 추출
    3. DB 비밀번호와 대조 후 결과 반환
    """
    try:
        # 1. 세션 검증 및 자동 갱신 모듈 호출
        # 이 한 줄로 Redis 조회, Access 만료 체크, Refresh 재발급, DB/Redis 업데이트가 완료됩니다.
        authResponse = validateToken(pwdCheckModel.uuid)
        
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

        # 4. DB에서 해당 유저의 비밀번호 조회
        userSql = "SELECT password FROM `USER` WHERE id = ? AND delete_yn = 0"
        userRecord = findAll(userSql, (userId,))
        
        if not userRecord:
            return responseModel(False, "존재하지 않는 사용자입니다.")
            
        dbPassword = userRecord[0]['password']

        # 5. 비밀번호 최종 대조 및 결과 반환
        if pwdCheckModel.password == dbPassword:
            # 성공 시, 프론트엔드가 다음 요청에 사용할 수 있도록 최신 uuid를 데이터에 담아 보냅니다.
            return responseModel(True, "비밀번호 확인에 성공하였습니다.", {"uuid": authResponse})
        
        return responseModel(False, "비밀번호가 일치하지 않습니다.", {"uuid": authResponse})

    except Exception as e:
        print(f"pwdCheckProcess Error: {e}")
        return responseModel(False, f"서버 내부 오류가 발생했습니다: {str(e)}")