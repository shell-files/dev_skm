from src.models.model import UserModel, EmailModel, ResponseModel
from src.utils.auth import delete_cookie, get_domain
from src.utils.rediscl import getCompanyRedis, delTokenRedis, getTokenRedis
from src.utils.settings import settings
from src.utils.db import findOne, save, findAll
from src.utils.kafkasv import sendToKafka
from src.utils.tokenset import decryptFromJwe
from src.utils.validatetok import validateToken
from fastapi import Request, Response

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

    userSql = f"""
        SELECT aes_d(u.`name`, '{settings.maria_db_key}') AS `name`
        FROM `with`.`USER` AS u
        WHERE `u`.`email` = aes_e(?, '{settings.maria_db_key}')
    """
    userParams = (userModel.email, )
    userResult = findOne(userSql, userParams)

    if userResult is not None:
        userName = userResult["name"]

    for com in companyResult:
        if com["company_id"] == int(company["companyId"]):
            selectedCompany = com
            break

    return ResponseModel(True, "사용자 정보가 유효합니다.", {"user": userModel.email, "userName": userName, "companys": companyResult, "selectedCompany": selectedCompany})

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
        emailCheckSql = f"""
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
        kafkaData = {"type": 4, "email": user["email"], "tempPwd": tempPwd}
        sendToKafka(kafkaData)

        return ResponseModel(True, "임시 비밀번호가 메일로 발송 됐습니다.")
    except Exception as e:
        return ResponseModel(False, f"오류 발생 : {e}")


# --------------------------
# 로그아웃 로직 처리 함수
# --------------------------
def logoutProcess(response: Response, request: Request, userModel: UserModel):
    """
    1. db에서 refresh token delete_yn 1으로 변경
    2. redis에서 uuid 삭제
    """
    try:
        if(delete_cookie(response, request, userModel.uuid)):
            return ResponseModel(True, "로그아웃 완료")
        return ResponseModel(False, "로그아웃 실패")
    except Exception as e:
        return ResponseModel(False, f"오류 발생 : {e}")
# --------------------------
# 비밀번호 확인 로직 처리 함수
# --------------------------


def pwdCheckProcess(request: Request, pwdCheckModel):
    try:
        # 1. 쿠키에서 uuid 추출
        current_uuid = request.cookies.get("yakgwa")

        print(f"=== 추출된 UUID: {current_uuid} ===")
        if not current_uuid:
            return ResponseModel(False, "로그인 정보가 만료되었습니다. 다시 로그인해주세요.")

        # 2. 세션 검증 (토큰 갱신 로직 포함)
        authResponse = validateToken(current_uuid)

        # [중요] 상태 체크를 먼저 해야 합니다. 실패 시 즉시 반환
        if not authResponse.get("status"):
            return authResponse

        # 3. 검증 통과 후 최신 UUID 획득
        activeUuid = authResponse.get("data", {}).get("uuid")
        if not activeUuid:
            return ResponseModel(False, "유효한 세션 정보를 찾을 수 없습니다.")

        # 4. 최신 UUID를 통해 유저 ID(sub) 추출
        tokenRes = getTokenRedis(activeUuid)

        # [중요] tokenRes가 None이거나 accessToken이 없는 경우 대비
        if not tokenRes or "accessToken" not in tokenRes:
            return ResponseModel(False, "사용자 토큰 정보를 가져올 수 없습니다.")

        payload = decryptFromJwe(tokenRes["accessToken"])
        if not payload:
            return ResponseModel(False, "토큰 복호화에 실패했습니다.")

        userId = payload.get("sub")

        # 5. DB에서 해당 유저의 비밀번호 조회
        userSql = f"""SELECT aes_d(password, '{settings.maria_db_key}' ) as password
                        FROM `with`.`USER` 
                        WHERE id = ? 
                        AND delete_yn = 0"""
        userRecord = findAll(userSql, (userId,))

        if not userRecord:
            return ResponseModel(False, "존재하지 않는 사용자입니다.")

        dbPassword = userRecord[0]['password']

        # 6. 비밀번호 최종 대조
        if pwdCheckModel.password == dbPassword:
            # 성공 시, 최신 uuid를 데이터에 담아 반환
            return ResponseModel(True, "비밀번호 확인에 성공하였습니다.", {"uuid": activeUuid})

        return ResponseModel(False, "비밀번호가 일치하지 않습니다.")

    except Exception as e:
        print(f"pwdCheckProcess Error: {e}")
        return ResponseModel(False, f"서버 내부 오류가 발생했습니다: {str(e)}")