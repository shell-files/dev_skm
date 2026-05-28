from src.models.model import UserModel, EmailModel,ResponseModel
from src.utils.rediscl import getCompanyRedis, delTokenRedis, getTokenRedis
from src.utils.settings import settings
from src.utils.db import findOne, save, findAll
from src.utils.kafkasv import sendToKafka
from src.utils.tokenset import decryptFromJwe
from src.utils.validatetok import validateToken

import string
import random

def checkUser(userModel: UserModel):
    uuid = userModel.uuid
    company = getCompanyRedis(uuid)
    if company is None:
        return ResponseModel(False, "회사를 선택해주세요.")
    
    companySql = f"""
        SELECT
            c.id AS company_id,
            aes_d(c.company_name, '{settings.maria_db_key}') AS company_name,
            aes_d(r.`role`, '{settings.maria_db_key}') AS role,
            aes_d(r.`name`, '{settings.maria_db_key}') AS role_name,
            aes_d(u.`email` ,'{settings.maria_db_key}') AS email
        FROM `with`.`USER_ROLE` AS ur
        INNER JOIN `skm`.`COMPANY` AS c
            ON (c.id = ur.company_id)
        INNER JOIN `with`.`ROLE` AS r
            ON (r.id = ur.role_id)
        INNER JOIN `with`.`USER` AS u
            ON (u.id = ur.user_id)
        WHERE 1 = 1
        AND ur.user_id = ?
        AND ur.role_id IN (2,3,4)
        AND ur.delete_yn = 0
    """
    companyParams = (userModel.id, )
    companyResult = findAll(companySql, companyParams)

    for com in companyResult:
        if com["company_id"] == int(company["companyId"]):
            selectedCompany = com
            break

    return ResponseModel(True, "사용자 정보가 유효합니다.", {"user": userModel.email, "userName": userModel.name, "companys": companyResult, "selectedCompany": selectedCompany})

# --------------------------
# 비밀번호 찾기 로직 처리 함수
# --------------------------
def findPwdProcess(emailModel: EmailModel):
    """
    - 비밀번호 찾기
    1. db에서 이메일 체크 (id, email 조회)
    2. 임시 비밀번호 생성(12자리) / redis에 key(임시비밀번호):value(email)
    3. 임시 비밀번호 포함된 메일(kafka이용) 발송
    """
    try:
        # 1. db에서 이메일 확인
        emailCheckSql=f"""
                    SELECT id, aes_d(email, '{settings.maria_db_key}' ) as email
                    FROM `with`.`USER`
                    WHERE email = aes_e( ? , '{settings.maria_db_key}' ) AND delete_yn = 0;
                    """
        emailCheckParams = (emailModel.email,)
        user = findOne(emailCheckSql, emailCheckParams)
        if not user:
            return ResponseModel(False, "등록되지 않은 이메일이거나 탈퇴한 회원입니다.")

        # 2. 임시 비밀번호 생성(10자리) / redis에 key(임시비밀번호):value(email)
        specialChars = "!@#$%^&*"
        tempPwdList = [random.choice(string.ascii_uppercase),
                        random.choice(string.ascii_lowercase),
                        random.choice(string.digits),
                        random.choice(specialChars)]
        characters = string.ascii_letters + string.digits
        tempPwdList += [random.choice(characters) for _ in range(6)]

        random.shuffle(tempPwdList)
        tempPwd = ''.join(tempPwdList)

        updatePwdSql = f"""
            UPDATE `with`.`USER`
            SET password = aes_e( ? , '{settings.maria_db_key}' )
            WHERE id = ?
        """
        updatePwdParams = (tempPwd, user["id"])
        save(updatePwdSql, updatePwdParams)
        # setPasswordRedis(tempPwd, user["email"])

        # 3. 임시 비밀번호 포함된 메일(kafka이용) 발송
        kafkaData = {"type":4, "email": user["email"], "tempPwd": tempPwd}
        sendToKafka(kafkaData)

        return ResponseModel(True, "임시 비밀번호가 메일로 발송 됐습니다.")
    except Exception as e:
        return ResponseModel(False, f"오류 발생 : {e}")
    
    
# --------------------------
# 로그아웃 로직 처리 함수
# --------------------------     
def logoutProcess(logoutModel):
    """
    1. db에서 refresh token delete_yn 1으로 변경
    2. redis에서 uuid 삭제
    """
    uuidKey = logoutModel.uuid
  
    try:
        # 1. db에서 refresh token delete_yn 1으로 변경
        logoutSql="""
                UPDATE TOKEN
                    SET `delete_yn` = 1
                    WHERE uuid = ?;
                """
        logoutParams = (uuidKey,)
        save(logoutSql, logoutParams)

        # 2. redis에서 uuid 삭제
        delTokenRedis(uuidKey)
        
        return ResponseModel(True, "로그아웃 완료")        
    except Exception as e:
        return ResponseModel(False, f"오류 발생 : {e}")

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
            return ResponseModel(False, "존재하지 않는 사용자입니다.")
            
        dbPassword = userRecord[0]['password']

        # 5. 비밀번호 최종 대조 및 결과 반환
        if pwdCheckModel.password == dbPassword:
            # 성공 시, 프론트엔드가 다음 요청에 사용할 수 있도록 최신 uuid를 데이터에 담아 보냅니다.
            return ResponseModel(True, "비밀번호 확인에 성공하였습니다.", {"uuid": authResponse})
        
        return ResponseModel(False, "비밀번호가 일치하지 않습니다.", {"uuid": authResponse})

    except Exception as e:
        print(f"pwdCheckProcess Error: {e}")
        return ResponseModel(False, f"서버 내부 오류가 발생했습니다: {str(e)}")