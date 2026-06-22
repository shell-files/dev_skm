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
    """userModel에서 companyId를 직접 추출하거나 Redis UUID 조회로 현재 선택된 회사 ID를 반환한다."""
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
    """요청 companyId가 현재 사용자 스코프와 일치하지 않으면 PermissionError를 발생시킨다."""
    scopeCompanyId = resolveScope(userModel)
    if scopeCompanyId != int(companyId):
        raise PermissionError("Forbidden company scope")


__all__ = ["resolveScope", "checkScope"]
