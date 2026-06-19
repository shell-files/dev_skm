"""
companyscope.py
레이어: Utils
역할: 선택된 회사 스코프 확인 — UserModel 또는 Redis에서 companyId 조회 및 API/서비스 가드.

주요 함수:
  resolveScope — 회사 스코프 조회
  checkScope   — 회사 스코프 유효성 검증
"""

from __future__ import annotations

from typing import Optional


def resolveScope(userModel) -> Optional[int]:
    if isinstance(userModel, dict):
        directCompanyId = userModel.get("companyId") or userModel.get("company_id")
        userUuid = userModel.get("uuid")
    else:
        directCompanyId = getattr(userModel, "companyId", None) or getattr(userModel, "company_id", None)
        userUuid = getattr(userModel, "uuid", None)

    if directCompanyId is not None:
        return int(directCompanyId)
    if not userUuid:
        return None

    from src.utils.rediscl import getCompanyRedis

    companyRedis = getCompanyRedis(userUuid) or {}
    if companyRedis.get("status") and companyRedis.get("companyId") is not None:
        return int(companyRedis["companyId"])
    return None


def checkScope(companyId: int, userModel) -> None:
    scopeCompanyId = resolveScope(userModel)
    if scopeCompanyId != int(companyId):
        raise PermissionError("Forbidden company scope")


__all__ = ["resolveScope", "checkScope"]
