from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from src.utils.db import findAll


FINANCIAL_BASIS_ATOMIC_MAP = {
    "revenue": {
        "entity": "G0-02__Q0001",
        "consolidated": "G0-02__G0001",
    },
    "operatingProfit": {
        "entity": "G0-02__Q0002",
        "consolidated": "G0-02__G0002",
    },
    "netIncome": {
        "entity": "G0-02__Q0003",
        "consolidated": "G0-02__G0003",
    },
    "capex": {
        "entity": "G0-02__Q0004",
        "consolidated": "G0-02__G0004",
    },
    "depreciation": {
        "entity": "G0-02__Q0005",
        "consolidated": "G0-02__G0005",
    },
}

FINANCIAL_BASIS_FIELDS = list(FINANCIAL_BASIS_ATOMIC_MAP.keys())

PRIORITY_GROUP_ROLLUP_G = "GROUP_ROLLUP_RESULT_G"
PRIORITY_KPI_FACT_G = "KPI_FACT_G"
PRIORITY_KPI_FACT_Q = "KPI_FACT_Q"
PRIORITY_ONBOARDING_INPUT_Q = "ONBOARDING_INPUT_Q"

PRIORITY_CONFIG = {
    PRIORITY_GROUP_ROLLUP_G: {
        "basisType": "CONSOLIDATED",
        "basisSource": "ESG_GROUP_ROLLUP_RESULT",
        "atomicKind": "consolidated",
    },
    PRIORITY_KPI_FACT_G: {
        "basisType": "CONSOLIDATED",
        "basisSource": "ESG_KPI_FACT",
        "atomicKind": "consolidated",
    },
    PRIORITY_KPI_FACT_Q: {
        "basisType": "ENTITY",
        "basisSource": "ESG_KPI_FACT",
        "atomicKind": "entity",
    },
    PRIORITY_ONBOARDING_INPUT_Q: {
        "basisType": "ENTITY",
        "basisSource": "ESG_ONBOARDING_INPUT_VALUE",
        "atomicKind": "entity",
    },
}


def getG0FinancialBasis(
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> dict:
    priorityList = buildFinancialBasisPriority(preferConsolidated)
    attempts = []
    minimalRevenueBasis = None
    minimalRevenueIndex = 0

    for index, priority in enumerate(priorityList):
        rows = fetchFinancialBasisRows(companyId, reportingYear, priority)
        basis = buildBasisFromRows(companyId, reportingYear, rows, priority)
        presentFields = _presentFields(basis)
        attempts.append(
            {
                "priority": priority,
                "rowCount": len(rows),
                "presentFieldCount": len(presentFields),
                "presentFields": presentFields,
                "missingFields": basis.get("missingFields", []),
            }
        )

        if len(presentFields) >= 3:
            basis["fallbackUsedYn"] = index > 0
            basis["trace"]["priority"] = priorityList
            basis["trace"]["attempts"] = attempts
            basis["trace"]["reason"] = _selectedReason(
                preferConsolidated=preferConsolidated,
                selectedPriority=priority,
                presentFieldCount=len(presentFields),
            )
            return basis

        if minimalRevenueBasis is None and isUsableBasis(basis):
            minimalRevenueBasis = basis
            minimalRevenueIndex = index

    if minimalRevenueBasis:
        presentFields = _presentFields(minimalRevenueBasis)
        selectedPriority = minimalRevenueBasis["trace"].get("selectedPriority", "UNKNOWN")
        minimalRevenueBasis["fallbackUsedYn"] = minimalRevenueIndex > 0
        minimalRevenueBasis["trace"]["priority"] = priorityList
        minimalRevenueBasis["trace"]["attempts"] = attempts
        minimalRevenueBasis["trace"]["reason"] = _selectedReason(
            preferConsolidated=preferConsolidated,
            selectedPriority=selectedPriority,
            presentFieldCount=len(presentFields),
        )
        return minimalRevenueBasis

    emptyBasis = emptyFinancialBasis(companyId, reportingYear)
    emptyBasis["trace"]["priority"] = priorityList
    emptyBasis["trace"]["attempts"] = attempts
    return emptyBasis


def buildFinancialBasisPriority(preferConsolidated: bool) -> list[str]:
    if preferConsolidated:
        return [
            PRIORITY_GROUP_ROLLUP_G,
            PRIORITY_KPI_FACT_G,
            PRIORITY_KPI_FACT_Q,
            PRIORITY_ONBOARDING_INPUT_Q,
        ]
    return [
        PRIORITY_KPI_FACT_Q,
        PRIORITY_ONBOARDING_INPUT_Q,
        PRIORITY_GROUP_ROLLUP_G,
        PRIORITY_KPI_FACT_G,
    ]


def fetchFinancialBasisRows(
    companyId: int,
    reportingYear: int,
    priority: str,
) -> list[dict]:
    if priority not in PRIORITY_CONFIG:
        return []

    atomicIds = _atomicIdsForPriority(priority)
    placeholders = ", ".join(["?"] * len(atomicIds))

    if priority == PRIORITY_GROUP_ROLLUP_G:
        sql = f"""
            SELECT
                'ESG_GROUP_ROLLUP_RESULT' AS sourceTable,
                group_atomic_metric_id AS atomicMetricId,
                value_numeric AS valueNumeric,
                unit,
                updated_at AS updatedAt
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id = ?
              AND reporting_year = ?
              AND group_metric_id = 'G0-02'
              AND group_atomic_metric_id IN ({placeholders})
              AND delete_yn = 0
            ORDER BY updated_at DESC, id DESC
        """
        return findAll(sql, (companyId, reportingYear, *atomicIds)) or []

    if priority in (PRIORITY_KPI_FACT_G, PRIORITY_KPI_FACT_Q):
        sql = f"""
            SELECT
                'ESG_KPI_FACT' AS sourceTable,
                atomic_metric_id AS atomicMetricId,
                value_numeric AS valueNumeric,
                unit,
                updated_at AS updatedAt
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id = 'G0-02'
              AND atomic_metric_id IN ({placeholders})
              AND delete_yn = 0
            ORDER BY
                CASE
                    WHEN LOWER(COALESCE(approval_status, '')) = 'approved' THEN 0
                    WHEN LOWER(COALESCE(approval_status, '')) = 'submitted' THEN 1
                    ELSE 2
                END,
                updated_at DESC,
                id DESC
        """
        return findAll(sql, (companyId, reportingYear, *atomicIds)) or []

    if priority == PRIORITY_ONBOARDING_INPUT_Q:
        sql = f"""
            SELECT
                'ESG_ONBOARDING_INPUT_VALUE' AS sourceTable,
                atomic_metric_id AS atomicMetricId,
                value_numeric AS valueNumeric,
                unit,
                updated_at AS updatedAt
            FROM ESG_ONBOARDING_INPUT_VALUE
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id = 'G0-02'
              AND atomic_metric_id IN ({placeholders})
              AND delete_yn = 0
            ORDER BY
                CASE
                    WHEN LOWER(COALESCE(input_status, '')) = 'approved' THEN 0
                    WHEN LOWER(COALESCE(input_status, '')) = 'submitted' THEN 1
                    ELSE 2
                END,
                updated_at DESC,
                id DESC
        """
        return findAll(sql, (companyId, reportingYear, *atomicIds)) or []

    return []


def buildBasisFromRows(
    companyId: int,
    reportingYear: int,
    rows: list[dict],
    priority: str,
) -> dict:
    config = PRIORITY_CONFIG.get(priority, {})
    atomicKind = config.get("atomicKind", "entity")
    atomicToField = {
        mapping[atomicKind]: fieldName
        for fieldName, mapping in FINANCIAL_BASIS_ATOMIC_MAP.items()
    }
    basis = _baseFinancialBasis(
        companyId=companyId,
        reportingYear=reportingYear,
        basisType=config.get("basisType", "NONE"),
        basisSource=config.get("basisSource"),
        selectedPriority=priority,
    )
    warnings = []
    seenFields = set()

    for row in rows:
        atomicMetricId = row.get("atomicMetricId")
        fieldName = atomicToField.get(atomicMetricId)
        if fieldName is None or fieldName in seenFields:
            continue

        valueNumeric, normalizedUnit, warning = _normalizeFinancialValueWithWarning(
            row.get("valueNumeric"),
            row.get("unit"),
        )
        if valueNumeric is None:
            continue

        seenFields.add(fieldName)
        basis[fieldName] = valueNumeric
        if warning:
            warnings.append(
                {
                    "fieldName": fieldName,
                    "atomicMetricId": atomicMetricId,
                    "warning": warning,
                }
            )
        basis["sourceRows"].append(
            {
                "sourceTable": row.get("sourceTable") or config.get("basisSource"),
                "sourcePriority": priority,
                "atomicMetricId": atomicMetricId,
                "fieldName": fieldName,
                "valueNumeric": valueNumeric,
                "unit": normalizedUnit,
                "updatedAt": _formatDateTime(row.get("updatedAt")),
            }
        )

    basis["missingFields"] = [
        fieldName
        for fieldName in FINANCIAL_BASIS_FIELDS
        if basis.get(fieldName) is None
    ]
    basis["sourceRows"] = sorted(
        basis["sourceRows"],
        key=lambda sourceRow: FINANCIAL_BASIS_FIELDS.index(sourceRow["fieldName"]),
    )
    presentFieldCount = len(FINANCIAL_BASIS_FIELDS) - len(basis["missingFields"])
    basis["trace"]["partialBasisYn"] = 0 < presentFieldCount < len(FINANCIAL_BASIS_FIELDS)
    basis["trace"]["warnings"] = warnings
    return basis


def isUsableBasis(basis: dict) -> bool:
    presentFieldCount = len(_presentFields(basis))
    if presentFieldCount >= 3:
        return True
    return basis.get("revenue") is not None


def emptyFinancialBasis(companyId: int, reportingYear: int) -> dict:
    basis = _baseFinancialBasis(
        companyId=companyId,
        reportingYear=reportingYear,
        basisType="NONE",
        basisSource=None,
        selectedPriority="NONE",
    )
    basis["fallbackUsedYn"] = True
    basis["missingFields"] = FINANCIAL_BASIS_FIELDS.copy()
    basis["trace"]["reason"] = "No G0-02 financial basis rows found"
    basis["trace"]["partialBasisYn"] = False
    basis["trace"]["warnings"] = []
    return basis


def normalizeFinancialValue(value: Any, unit: Optional[str]) -> tuple[Optional[float], str]:
    normalizedValue, normalizedUnit, _ = _normalizeFinancialValueWithWarning(value, unit)
    return normalizedValue, normalizedUnit


def _baseFinancialBasis(
    companyId: int,
    reportingYear: int,
    basisType: str,
    basisSource: Optional[str],
    selectedPriority: str,
) -> dict:
    basis = {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "basisType": basisType,
        "basisSource": basisSource,
        "fallbackUsedYn": False,
        "unit": "KRW",
        "missingFields": [],
        "sourceRows": [],
        "trace": {
            "priority": [],
            "selectedPriority": selectedPriority,
            "reason": "",
        },
    }
    for fieldName in FINANCIAL_BASIS_FIELDS:
        basis[fieldName] = None
    return basis


def _atomicIdsForPriority(priority: str) -> list[str]:
    atomicKind = PRIORITY_CONFIG[priority]["atomicKind"]
    return [
        FINANCIAL_BASIS_ATOMIC_MAP[fieldName][atomicKind]
        for fieldName in FINANCIAL_BASIS_FIELDS
    ]


def _presentFields(basis: dict) -> list[str]:
    return [
        fieldName
        for fieldName in FINANCIAL_BASIS_FIELDS
        if basis.get(fieldName) is not None
    ]


def _formatDateTime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalizeFinancialValueWithWarning(
    value: Any,
    unit: Optional[str],
) -> tuple[Optional[float], str, Optional[str]]:
    numericValue = _toDecimal(value)
    normalizedUnit = "KRW"
    if numericValue is None:
        return None, normalizedUnit, None

    unitText = str(unit or "").strip()
    unitUpper = unitText.upper()
    warning = None

    if unitText in ("", "원") or unitUpper in ("KRW", "WON"):
        multiplier = Decimal("1")
    elif unitText == "백만원" or unitUpper in ("MILLION_KRW", "MILLION KRW"):
        multiplier = Decimal("1000000")
    elif unitText == "억원":
        multiplier = Decimal("100000000")
    else:
        multiplier = Decimal("1")
        warning = f"Unknown financial unit '{unitText}', value kept as-is"

    return _decimalToNumber(numericValue * multiplier), normalizedUnit, warning


def _toDecimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError, ValueError):
        return None


def _decimalToNumber(value: Decimal) -> float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _selectedReason(
    preferConsolidated: bool,
    selectedPriority: str,
    presentFieldCount: int,
) -> str:
    if 0 < presentFieldCount < 3:
        return "Only partial G0-02 financial basis found; revenue-based minimal basis selected"
    if selectedPriority == PRIORITY_GROUP_ROLLUP_G:
        if preferConsolidated:
            return "preferConsolidated=true and consolidated G values exist"
        return "entity basis unavailable; consolidated G values selected as fallback"
    if selectedPriority == PRIORITY_KPI_FACT_G:
        return "consolidated G values selected from ESG_KPI_FACT fallback"
    if selectedPriority == PRIORITY_KPI_FACT_Q:
        return "entity Q values selected from ESG_KPI_FACT"
    if selectedPriority == PRIORITY_ONBOARDING_INPUT_Q:
        return "entity Q values selected from ESG_ONBOARDING_INPUT_VALUE fallback"
    if presentFieldCount > 0:
        return "partial G0-02 financial basis selected"
    return "No G0-02 financial basis rows found"


__all__ = [
    "FINANCIAL_BASIS_ATOMIC_MAP",
    "buildBasisFromRows",
    "buildFinancialBasisPriority",
    "emptyFinancialBasis",
    "fetchFinancialBasisRows",
    "getG0FinancialBasis",
    "isUsableBasis",
    "normalizeFinancialValue",
]
