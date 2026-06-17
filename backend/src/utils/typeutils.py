from decimal import Decimal
from typing import Optional


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
