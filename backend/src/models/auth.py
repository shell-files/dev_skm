"""
auth.py
레이어: Model / Service
역할: 로그인·로그아웃·비밀번호 찾기·사용자 확인 비즈니스 로직.

주요 함수:
  loginProcess    — 로그인 처리 (DB 인증 → 토큰 발급 → Redis/쿠키 저장)
  checkUser       — 현재 세션 사용자 정보 확인
  findPwdProcess  — 임시 비밀번호 생성 및 이메일 발송
  logoutProcess   — 로그아웃 처리 (쿠키·Redis 삭제)
  pwdCheckProcess — 비밀번호 재확인 처리
"""
from src.models.model import UserModel, EmailModel, ResponseModel, LoginModel
from src.utils.auth import delete_cookie, get_domain
from src.utils.rediscl import getCompanyRedis, getTokenRedis, setTokenRedis
from src.utils.settings import settings
from src.utils.db import findOne, save, findAll
from src.utils.kafkasv import sendToKafka
from src.utils.tokenset import decryptFromJwe, createUserTokens
from src.utils.validatetok import validateToken
from fastapi import Request, Response

import json
import string
import random

def loginProcess(response: Response, request: Request, loginModel: LoginModel):
    """
    1. 임시 비밀번호 redis에서 조회 (비밀번호 찾기 후 로그인 시도하는 경우)
    2. DB에서 사용자 검증 및 사용자 정보 추출
    3. access token 생성
    4. refresh token DB 저장
    5. accessToken redis 저장
    """
    try:
        # 1. DB에서 사용자 검증 및 사용자 정보 추출
        loginSql=f"""
            SELECT
                u.id,
                aes_d(u.name, '{settings.maria_db_key}') AS name,
                aes_d(u.email, '{settings.maria_db_key}') AS email,
                JSON_ARRAYAGG(DISTINCT aes_d(r.`role`, '{settings.maria_db_key}')) AS role_json,
                JSON_ARRAYAGG(DISTINCT aes_d(r.`name`, '{settings.maria_db_key}')) AS role_name_json
            FROM `with`.`USER` AS u
            INNER JOIN `with`.`USER_ROLE` AS ur
               ON (u.id = ur.user_id)
            INNER JOIN `skm`.`COMPANY` AS c
               ON (c.id = ur.company_id)
            INNER JOIN `with`.`ROLE` AS r
               ON (r.id = ur.role_id)
            WHERE 1 = 1
            AND u.email = aes_e( ? , '{settings.maria_db_key}' )
            AND u.password = aes_e( ? , '{settings.maria_db_key}' )
            AND u.delete_yn = 0
            """

        loginParams = (loginModel.email, loginModel.password)
        userResult = findOne(loginSql, loginParams)
        if userResult is None:
            return ResponseModel(False, "이메일 또는 비밀번호가 올바르지 않습니다.")

        roles = json.loads(userResult["role_json"])
        roleNames = json.loads(userResult["role_name_json"])

        user = UserModel(
            uuid="",
            id=userResult["id"],
            email=userResult["email"],
            name=userResult["name"],
            role=roles[0] if len(roles) > 0 else None,
            role_name=roleNames[0] if len(roleNames) > 0 else None
        )

        companySql = f"""
            SELECT
              c.id AS company_id,
              aes_d(c.company_name, '{settings.maria_db_key}') AS company_name,
              aes_d(r.`role`, '{settings.maria_db_key}') AS role,
              aes_d(r.`name`, '{settings.maria_db_key}') AS role_name
            FROM `with`.`USER_ROLE` AS ur
            INNER JOIN `skm`.`COMPANY` AS c
              ON (c.id = ur.company_id)
            INNER JOIN `with`.`ROLE` AS r
              ON (r.id = ur.role_id)
            WHERE 1 = 1
            AND ur.user_id = ?
            AND ur.role_id IN (2,3,4)
            AND ur.delete_yn = 0
        """
        companyParams = (user.id, )
        companyResult = findAll(companySql, companyParams)
        selectedCompany = ""
        if len(companyResult) == 1 :
          selectedCompany = companyResult[0]

        # 2. access token 생성
        accessToken, refreshToken, tokenUuid = createUserTokens(user)

        # 3. refresh token DB 저장
        refreshTokenSql="""
          INSERT INTO `with`.TOKEN (`user_id`,`refresh_token`,`uuid`)
          VALUES (?,?,?)
          """
        tokenParams = (user.id, refreshToken, tokenUuid)
        save(refreshTokenSql, tokenParams)

        # 4. accessToken redis 저장
        # 로그인 직후 세션 유실
        # 원인: loginProcess()에서 setTokenRedis() 반환값을 검증하지 않아 Redis 저장 실패 시에도 성공 응답 반환
        # 수정: setTokenRedis() 결과 확인 후 실패 시 에러 반환
        redisResult = setTokenRedis(tokenUuid, accessToken)
        if not redisResult or not redisResult.get("status"):
            return ResponseModel(False, "세션 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.")
        max_age = (60 * 60 * 24 * settings.refresh_token_expire_days)
        response.set_cookie(key=settings.cookie_key, value=tokenUuid, domain=get_domain(request),
          httponly=True, samesite="lax",
          # secure=True,
          max_age=max_age)

        return ResponseModel(True, "로그인에 성공했습니다.", {"companies": companyResult, "userName": user.name, "selectedCompany": selectedCompany})
    except Exception as e:
        return ResponseModel(False, f"로그인 처리 중 오류가 발생했습니다: {str(e)}")


def checkUser(userModel: UserModel):
    userName = None
    selectedCompany = None

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
    if len(companyResult) == 1 :
      selectedCompany = companyResult[0]
    else :
      uuid = userModel.uuid
      company = getCompanyRedis(uuid)
      if company.get("status") is True:
        for com in companyResult:
           if int(com["company_id"]) == int(company["companyId"]):
               selectedCompany = com
               break

    userSql = f"""
       SELECT aes_d(u.`name`, '{settings.maria_db_key}') AS `name`
       FROM `with`.`USER` AS u
       WHERE `u`.`email` = aes_e(?, '{settings.maria_db_key}')
    """
    userParams = (userModel.email, )
    userResult = findOne(userSql, userParams)

    if userResult is not None:
        userName = userResult.get("name")

    return ResponseModel(True, "사용자 정보가 유효합니다.", {"user": userModel.email, "userName": userName, "companys": companyResult, "selectedCompany": selectedCompany})


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
            return ResponseModel(True, "비밀번호 확인에 성공하였습니다.", {"uuid": activeUuid})

        return ResponseModel(False, "비밀번호가 일치하지 않습니다.")

    except Exception as e:
        print(f"pwdCheckProcess Error: {e}")
        return ResponseModel(False, f"서버 내부 오류가 발생했습니다: {str(e)}")
