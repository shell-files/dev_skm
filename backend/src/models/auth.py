from src.models.model import UserModel, ResponseModel
from src.utils.rediscl import getCompanyRedis
from src.utils.settings import settings
from src.utils.db import findAll

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
    companyParams = (userModel.id, )
    companyResult = findAll(companySql, companyParams)

    for com in companyResult:
        if com["company_id"] == int(company["companyId"]):
            selectedCompany = com
            break

    return ResponseModel(True, "사용자 정보가 유효합니다.", {"userName": userModel.name, "companys": companyResult, "selectedCompany": selectedCompany})