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
    """값을 float로 변환한다. None이거나 변환 불가 시 default를 반환한다. Decimal도 지원한다."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safeInt(value, default: Optional[int] = None) -> Optional[int]:
    """값을 int로 변환한다. None이거나 변환 불가 시 default를 반환한다."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def formatDatetime(value) -> Optional[str]:
    """datetime 객체를 ISO 8601 문자열로 변환한다. None이면 None을 반환하고 그 외는 str()로 변환한다."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def truthy(value) -> bool:
    """DB/JSON에서 오는 다양한 truthy 표현(0/1, 'Y'/'y', 'true', bool)을 bool로 정규화한다."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        return int(value) != 0
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"y", "yes", "true", "1"}


def firstNonNull(values: list) -> Optional[int]:
    """목록에서 None이 아닌 첫 번째 값을 int로 변환하여 반환한다. 모두 None이면 None을 반환한다."""
    for value in values:
        if value is not None:
            return int(value)
    return None


def groupRows(rows: list[dict], key: str) -> dict[str, list[dict]]:
    """dict 목록을 지정 키 값으로 그룹핑하여 반환한다."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def firstPresent(row: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    """row에서 keys 순서대로 조회하여 None이 아닌 첫 번째 값을 반환한다. 모두 없으면 default를 반환한다."""
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def maskEmail(email: Optional[str]) -> Optional[str]:
    """이메일 주소를 로그 출력용으로 마스킹한다 (ex: k***@gmail.com)."""
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[0]}***@{domain}"


def normalizeIssueDomain(value: Optional[str]) -> Optional[str]:
    """ESG 도메인 코드/문자열을 표준 소문자 형식(environmental/social/governance/general)으로 정규화한다."""
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
