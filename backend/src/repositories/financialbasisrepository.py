"""
financialbasisrepository.py
레이어: Repository
역할: G0-02 재무 기준 조회 — 단독/연결 재무 기준 판별 및 DMA 재무 노출 계산용 데이터 반환.

주요 함수:
  getBasis / getG0FinancialBasis              — 재무 기준 조회
  buildPriority / buildFinancialBasisPriority — 우선순위 구성
  fetchRows / fetchFinancialBasisRows          — DB 행 조회
  checkBasisReady / isUsableBasis              — 기준 준비 여부 확인
  buildEmptyBasis / emptyFinancialBasis        — 빈 기준 구성
  normalizeValue / normalizeFinancialValue     — 값 정규화
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional



def findAll(sql: str, params=None):
    from src.utils.db import findAll as dbFindAll

    return dbFindAll(sql, params)


def findOne(sql: str, params=None):
    from src.utils.db import findOne as dbFindOne

    return dbFindOne(sql, params)


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
PRIORITY_KPI_FACT_Q = "KPI_FACT_Q"
PRIORITY_ONBOARDING_INPUT_Q = "ONBOARDING_INPUT_Q"

PRIORITY_CONFIG = {
    PRIORITY_GROUP_ROLLUP_G: {
        "basisType": "CONSOLIDATED",
        "basisSource": "ESG_GROUP_ROLLUP_RESULT",
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


def getBasis(
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
    requiredRollupBatchId: Optional[int] = None,
) -> dict:
    priorityList = buildPriority(preferConsolidated)
    attempts = []

    for index, priority in enumerate(priorityList):
        rows = fetchRows(companyId, reportingYear, priority, requiredRollupBatchId)
        basis = buildBasis(companyId, reportingYear, rows, priority)
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

        if checkUsable(basis):
            basis["fallbackUsedYn"] = index > 0
            basis["trace"]["priority"] = priorityList
            basis["trace"]["attempts"] = attempts
            basis["trace"]["reason"] = _selectedReason(
                preferConsolidated=preferConsolidated,
                selectedPriority=priority,
                presentFieldCount=len(presentFields),
            )
            return basis

    emptyBasis = buildEmptyBasis(companyId, reportingYear)
    emptyBasis["trace"]["priority"] = priorityList
    emptyBasis["trace"]["attempts"] = attempts
    return emptyBasis


def buildPriority(preferConsolidated: bool) -> list[str]:
    if preferConsolidated:
        return [PRIORITY_GROUP_ROLLUP_G]
    return [
        PRIORITY_KPI_FACT_Q,
        PRIORITY_ONBOARDING_INPUT_Q,
    ]


def fetchRows(
    companyId: int,
    reportingYear: int,
    priority: str,
    requiredRollupBatchId: Optional[int] = None,
) -> list[dict]:
    if priority not in PRIORITY_CONFIG:
        return []

    atomicIds = _atomicIdsForPriority(priority)
    placeholders = ", ".join(["?"] * len(atomicIds))

    if priority == PRIORITY_GROUP_ROLLUP_G:
        if requiredRollupBatchId is None:
            return []
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
              AND esg_rollup_batch_id = ?
              AND LOWER(COALESCE(rollup_status, '')) = 'approved'
              AND delete_yn = 0
            ORDER BY updated_at DESC, id DESC
        """
        return findAll(sql, (companyId, reportingYear, *atomicIds, requiredRollupBatchId)) or []

    if priority == PRIORITY_KPI_FACT_Q:
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
              AND LOWER(COALESCE(approval_status, '')) = 'approved'
              AND delete_yn = 0
            ORDER BY updated_at DESC, id DESC
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
              AND LOWER(COALESCE(input_status, '')) = 'approved'
              AND delete_yn = 0
            ORDER BY updated_at DESC, id DESC
        """
        return findAll(sql, (companyId, reportingYear, *atomicIds)) or []

    return []


def buildBasis(
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


def checkUsable(basis: dict) -> bool:
    presentFieldCount = len(_presentFields(basis))
    return presentFieldCount == len(FINANCIAL_BASIS_FIELDS)


def checkBasisReady(
    companyId: int,
    reportingYear: int,
    reportBasisType: str = "ENTITY",
    requiredRollupBatchId: Optional[int] = None,
) -> dict:
    normalizedBasisType = str(reportBasisType or "").strip().upper()
    if normalizedBasisType == "CONSOLIDATED":
        atomicIds = [
            FINANCIAL_BASIS_ATOMIC_MAP[fieldName]["consolidated"]
            for fieldName in FINANCIAL_BASIS_FIELDS
        ]
        row = fetchApprovedBasisRow(
            companyId=companyId,
            reportingYear=reportingYear,
            atomicIds=atomicIds,
            consolidatedYn=True,
            requiredRollupBatchId=requiredRollupBatchId,
        )
    else:
        normalizedBasisType = "ENTITY"
        atomicIds = [
            FINANCIAL_BASIS_ATOMIC_MAP[fieldName]["entity"]
            for fieldName in FINANCIAL_BASIS_FIELDS
        ]
        row = fetchApprovedBasisRow(
            companyId=companyId,
            reportingYear=reportingYear,
            atomicIds=atomicIds,
            consolidatedYn=False,
            requiredRollupBatchId=None,
        )

    approvedAtomicIds = [
        atomicId
        for atomicId in str(row.get("approved_atomic_metric_ids") or "").split(",")
        if atomicId
    ]
    approvedCount = len(set(approvedAtomicIds))
    missingAtomicIds = [
        atomicId
        for atomicId in atomicIds
        if atomicId not in approvedAtomicIds
    ]
    return {
        "readyYn": approvedCount >= len(atomicIds),
        "basisType": normalizedBasisType,
        "requiredRollupBatchId": requiredRollupBatchId,
        "approvedCount": approvedCount,
        "requiredCount": len(atomicIds),
        "approvedAtomicMetricIds": approvedAtomicIds,
        "missingAtomicMetricIds": missingAtomicIds,
    }


def fetchApprovedBasisRow(
    companyId: int,
    reportingYear: int,
    atomicIds: list[str],
    consolidatedYn: bool,
    requiredRollupBatchId: Optional[int] = None,
) -> dict:
    placeholders = ", ".join(["?"] * len(atomicIds))
    if consolidatedYn:
        if requiredRollupBatchId is None:
            return {}
        sql = f"""
            SELECT
                GROUP_CONCAT(DISTINCT group_atomic_metric_id) AS approved_atomic_metric_ids
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id = ?
              AND reporting_year = ?
              AND group_metric_id = 'G0-02'
              AND group_atomic_metric_id IN ({placeholders})
              AND esg_rollup_batch_id = ?
              AND LOWER(COALESCE(rollup_status, '')) = 'approved'
              AND delete_yn = 0
        """
        return findOne(sql, (companyId, reportingYear, *atomicIds, requiredRollupBatchId)) or {}

    sql = f"""
        SELECT
            GROUP_CONCAT(DISTINCT atomic_metric_id) AS approved_atomic_metric_ids
        FROM (
            SELECT atomic_metric_id
            FROM ESG_ONBOARDING_INPUT_VALUE
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id = 'G0-02'
              AND atomic_metric_id IN ({placeholders})
              AND LOWER(COALESCE(input_status, '')) = 'approved'
              AND (
                  value_numeric IS NOT NULL
                  OR TRIM(COALESCE(value_text, '')) <> ''
              )
              AND delete_yn = 0
            UNION
            SELECT atomic_metric_id
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id = 'G0-02'
              AND atomic_metric_id IN ({placeholders})
              AND LOWER(COALESCE(approval_status, '')) = 'approved'
              AND (
                  value_numeric IS NOT NULL
                  OR TRIM(COALESCE(value_text, '')) <> ''
              )
              AND delete_yn = 0
        ) approved_basis
    """
    return findOne(sql, (companyId, reportingYear, *atomicIds, companyId, reportingYear, *atomicIds)) or {}


def buildEmptyBasis(companyId: int, reportingYear: int) -> dict:
    basis = _baseFinancialBasis(
        companyId=companyId,
        reportingYear=reportingYear,
        basisType="NONE",
        basisSource=None,
        selectedPriority="NONE",
    )
    basis["fallbackUsedYn"] = False
    basis["missingFields"] = FINANCIAL_BASIS_FIELDS.copy()
    basis["trace"]["reason"] = "No complete approved G0-02 financial basis rows found"
    basis["trace"]["partialBasisYn"] = False
    basis["trace"]["warnings"] = []
    return basis


def normalizeValue(value: Any, unit: Optional[str]) -> tuple[Optional[float], str]:
    normalizedValue, normalizedUnit, _ = _normalizeFinancialValueWithWarning(value, unit)
    return normalizedValue, normalizedUnit


# Compatibility wrappers for previous public names

def getG0FinancialBasis(
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
    requiredRollupBatchId: Optional[int] = None,
) -> dict:
    return getBasis(companyId, reportingYear, preferConsolidated, requiredRollupBatchId)


def buildFinancialBasisPriority(preferConsolidated: bool) -> list[str]:
    return buildPriority(preferConsolidated)


def fetchFinancialBasisRows(
    companyId: int,
    reportingYear: int,
    priority: str,
    requiredRollupBatchId: Optional[int] = None,
) -> list[dict]:
    return fetchRows(companyId, reportingYear, priority, requiredRollupBatchId)


def buildBasisFromRows(
    companyId: int,
    reportingYear: int,
    rows: list[dict],
    priority: str,
) -> dict:
    return buildBasis(companyId, reportingYear, rows, priority)


def isUsableBasis(basis: dict) -> bool:
    return checkUsable(basis)


def emptyFinancialBasis(companyId: int, reportingYear: int) -> dict:
    return buildEmptyBasis(companyId, reportingYear)


def normalizeFinancialValue(value: Any, unit: Optional[str]) -> tuple[Optional[float], str]:
    return normalizeValue(value, unit)


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
    if presentFieldCount < len(FINANCIAL_BASIS_FIELDS):
        return "No complete approved G0-02 financial basis rows found"
    if selectedPriority == PRIORITY_GROUP_ROLLUP_G:
        return "consolidated G0-02 group rollup result selected"
    if selectedPriority == PRIORITY_KPI_FACT_Q:
        return "entity G0-02 Q values selected from ESG_KPI_FACT"
    if selectedPriority == PRIORITY_ONBOARDING_INPUT_Q:
        return "entity G0-02 Q values selected from ESG_ONBOARDING_INPUT_VALUE"
    return "No complete approved G0-02 financial basis rows found"


__all__ = [
    "FINANCIAL_BASIS_ATOMIC_MAP",
    "buildBasis",
    "buildBasisFromRows",
    "buildEmptyBasis",
    "buildPriority",
    "buildFinancialBasisPriority",
    "emptyFinancialBasis",
    "fetchApprovedBasisRow",
    "fetchRows",
    "fetchFinancialBasisRows",
    "getBasis",
    "getG0FinancialBasis",
    "checkBasisReady",
    "checkUsable",
    "isUsableBasis",
    "normalizeValue",
    "normalizeFinancialValue",
]
