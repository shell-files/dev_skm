"""
typeutils.py
레이어: Utils
역할: 타입 변환 헬퍼 — Decimal·숫자·딕셔너리 안전 변환 유틸리티.
"""
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence


def asFloat(value: Any, default: Optional[float] = None) -> Optional[float]:
    """safeFloat alias used by adapter layers; explicitly treats '' as None."""
    if value == "":
        return default
    return safeFloat(value, default)


def safeFloat(value, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safeInt(value, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def formatDatetime(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        return int(value) != 0
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"y", "yes", "true", "1"}


def firstNonNull(values: list) -> Optional[int]:
    for value in values:
        if value is not None:
            return int(value)
    return None


def groupRows(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def firstPresent(row: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def maskEmail(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[0]}***@{domain}"


def normalizeIssueDomain(value: Optional[str]) -> Optional[str]:
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"E", "ENVIRONMENT", "ENVIRONMENTAL"} or normalizedValue.startswith("E_"):
        return "environmental"
    if normalizedValue in {"S", "SOCIAL"} or normalizedValue.startswith("S_"):
        return "social"
    if normalizedValue in {"G", "GOVERNANCE"} or normalizedValue.startswith("G_"):
        return "governance"
    if normalizedValue in {"G0", "GENERAL"}:
        return "general"
    return None
