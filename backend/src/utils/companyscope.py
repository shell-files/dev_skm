"""
Domain: Company Scope
Layer: utils
Responsibility:
- Resolve selected company scope from user model or Redis
- Provide shared company scope guard for API/service layers
Public functions:
- resolveScope
- checkScope
Do not:
- do not modify auth/token/common code
- do not mutate Redis or DB state
- do not bypass tenant isolation
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
