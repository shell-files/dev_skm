from src.models.model import UserModel, EmailModel,ResponseModel
from src.utils.rediscl import getCompanyRedis
from src.utils.settings import settings
from src.utils.db import findOne, save, findAll
from src.utils.kafkasv import sendToKafka

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
            aes_d(r.`name`, '{settings.maria_db_key}') AS role_name
            aes_d(u.`email` ,'{settings.maria_db_key}') AS email
        FROM `with`.`USER_ROLE` AS ur
        INNER JOIN `skm`.`COMPANY` AS c
            ON (c.id = ur.company_id)
        INNER JOIN `with`.`ROLE` AS r
            ON (r.id = ur.role_id)
        INNER JOIN `with`.`USER` AS u
            ON (u.id - ur.id)
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