"""
companyutils.py
레이어: Repository
역할: 회사 정보 조회 유틸리티 — 회사명·사업자번호·규모 등 공통 조회.
"""
from typing import Optional

from src.utils.db import findAll, findOne
from src.utils.settings import settings


# COMPANY 테이블 컬럼 구조 조회 — 스키마별 id/name 컬럼명 및 delete_yn 여부 반환
def getCompanyTableInfo(schemaName: Optional[str]) -> Optional[dict]:
    schemaFilter = "DATABASE()" if schemaName is None else "?"
    params = [] if schemaName is None else [schemaName]
    rows = findAll(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = {schemaFilter}
          AND table_name = 'COMPANY'
        """,
        tuple(params),
    ) or []
    columns = {str(row.get("column_name") or "").lower() for row in rows}
    if not columns:
        return None
    idColumn = "company_id" if "company_id" in columns else "id" if "id" in columns else None
    nameColumn = "company_name" if "company_name" in columns else "name" if "name" in columns else None
    if not idColumn or not nameColumn:
        return None
    qualifiedTable = "COMPANY" if schemaName is None else f"`{schemaName}`.`COMPANY`"
    return {
        "qualifiedTable": qualifiedTable,
        "idColumn": idColumn,
        "nameColumn": nameColumn,
        "hasDeleteYn": "delete_yn" in columns,
    }


# COMPANY 테이블에서 회사명 조회 (다중 스키마 폴백: None→skm→with)
def getCompanyNameFromCompanyTable(companyId: int) -> Optional[str]:
    for schemaName in [None, "skm", "with"]:
        tableInfo = getCompanyTableInfo(schemaName)
        if not tableInfo:
            continue
        qualifiedTable = tableInfo["qualifiedTable"]
        idColumn = tableInfo["idColumn"]
        nameColumn = tableInfo["nameColumn"]
        deleteFilter = "AND delete_yn = 0" if tableInfo.get("hasDeleteYn") else ""
        try:
            row = findOne(
                f"""
                SELECT aes_d({nameColumn}, '{settings.maria_db_key}') AS company_name
                FROM {qualifiedTable}
                WHERE {idColumn} = ?
                  {deleteFilter}
                ORDER BY {idColumn} DESC
                LIMIT 1
                """,
                (companyId,),
            ) or {}
        except Exception:
            continue
        companyName = str(row.get("company_name") or "").strip()
        if companyName:
            return companyName
    return None


# 회사 ID 기준 회사명 조회 — COMPANY 테이블 우선, 없으면 ESG_COMPANY_PROFILE 폴백
def getCompanyName(companyId: int) -> str:
    companyName = getCompanyNameFromCompanyTable(companyId)
    if companyName:
        return companyName
    row = findOne(
        """
        SELECT COALESCE(company_code, CAST(company_id AS CHAR)) AS company_name
        FROM ESG_COMPANY_PROFILE
        WHERE company_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId,),
    ) or {}
    return row.get("company_name") or str(companyId)
