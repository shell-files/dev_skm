"""
Domain: DMA Materiality
Layer: utils/repository
Responsibility:
- Read G0 facts and materiality run context
- Persist latest company context profile and modifier payload
- Update context modifier columns for DMA score summary
Public functions:
- getRun
- getMaterialityRunContext
- listG0Facts
- getCompanyG0Facts
- listScoreRows
- getDmaScoreSummaryRowsForContext
- replaceProfile
- replaceCompanyContextProfile
- updateModifiers
- updateContextModifiers
- getLatestProfile
- getLatestCompanyContextProfile
- clampModifier
- clampSystemModifier
- decimalToFloat
Do not:
- do not mutate unrelated DB state
- do not calculate modifier rules
- do not change scoring formula unless explicitly requested
- do not change score formula
- do not call FastAPI router directly
- do not modify auth/token/common code
"""

import json
from decimal import Decimal
from typing import Any, Optional

from src.utils.db import addKey, findAll, findOne, save


SYSTEM_MODIFIER_MIN = -0.5
SYSTEM_MODIFIER_MAX = 0.5


def getRun(runId: int) -> dict:
    sql = """
        SELECT
            r.id,
            r.company_id,
            r.reporting_year,
            r.industry_profile,
            p.company_code,
            p.company_scope_type
        FROM ESG_MATERIALITY_RUN r
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = r.company_id
         AND p.delete_yn = 0
        WHERE r.id = ?
          AND r.delete_yn = 0
    """
    return findOne(sql, (runId,)) or {}


def listG0Facts(companyId: int, reportingYear: int) -> list[dict]:
    params = (companyId, reportingYear, companyId, reportingYear, companyId, reportingYear)
    sql = """
        SELECT
            'onboarding_input' AS source_table,
            iv.metric_id,
            iv.atomic_metric_id,
            amm.metric_name_kr AS metric_name,
            amm.atomic_name_kr AS atomic_name,
            iv.value_numeric,
            iv.value_text,
            iv.unit
        FROM ESG_ONBOARDING_INPUT_VALUE iv
        LEFT JOIN ESG_ATOMIC_METRIC_MASTER amm
          ON amm.atomic_metric_id = iv.atomic_metric_id
         AND amm.delete_yn = 0
        WHERE iv.company_id = ?
          AND iv.reporting_year = ?
          AND iv.delete_yn = 0
          AND (iv.metric_id LIKE 'G0-%' OR iv.atomic_metric_id LIKE 'G0-%')

        UNION ALL

        SELECT
            'kpi_fact' AS source_table,
            kf.metric_id,
            kf.atomic_metric_id,
            amm.metric_name_kr AS metric_name,
            amm.atomic_name_kr AS atomic_name,
            kf.value_numeric,
            kf.value_text,
            kf.unit
        FROM ESG_KPI_FACT kf
        LEFT JOIN ESG_ATOMIC_METRIC_MASTER amm
          ON amm.atomic_metric_id = kf.atomic_metric_id
         AND amm.delete_yn = 0
        WHERE kf.company_id = ?
          AND kf.reporting_year = ?
          AND kf.delete_yn = 0
          AND (kf.metric_id LIKE 'G0-%' OR kf.atomic_metric_id LIKE 'G0-%')

        UNION ALL

        SELECT
            'group_rollup_result' AS source_table,
            gr.group_metric_id AS metric_id,
            gr.group_atomic_metric_id AS atomic_metric_id,
            gr.group_metric_id AS metric_name,
            gr.group_atomic_name AS atomic_name,
            gr.value_numeric,
            gr.value_text,
            gr.unit
        FROM ESG_GROUP_ROLLUP_RESULT gr
        WHERE gr.parent_company_id = ?
          AND gr.reporting_year = ?
          AND gr.delete_yn = 0
          AND (gr.group_metric_id LIKE 'G0-%' OR gr.group_atomic_metric_id LIKE 'G0-%')
        ORDER BY metric_id, atomic_metric_id, source_table
    """
    return findAll(sql, params) or []


def listScoreRows(runId: int) -> list[dict]:
    sql = """
        SELECT
            id,
            sub_issue_code,
            benchmark_impact_score,
            benchmark_financial_score,
            media_external_impact_score,
            media_external_financial_score,
            survey_impact_score,
            survey_financial_score,
            context_impact_modifier,
            context_financial_modifier,
            final_impact_score,
            final_financial_score,
            final_score,
            rank_no
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
        ORDER BY
            CASE WHEN rank_no IS NULL THEN 1 ELSE 0 END,
            rank_no ASC,
            id ASC
    """
    return findAll(sql, (runId,)) or []


def replaceProfile(
    runId: int,
    companyId: int,
    reportingYear: int,
    industryProfile: Optional[str],
    businessModel: Optional[str],
    contextPayload: dict,
    modifierPayload: dict,
    confidenceScore: float,
) -> Optional[int]:
    save(
        """
        UPDATE ESG_DMA_CONTEXT_PROFILE
        SET delete_yn = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
        """,
        (runId,),
    )

    result = addKey(
        """
        INSERT INTO ESG_DMA_CONTEXT_PROFILE (
            esg_materiality_run_id,
            company_id,
            reporting_year,
            industry_profile,
            business_model,
            context_json,
            modifier_json,
            confidence_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            runId,
            companyId,
            reportingYear,
            industryProfile,
            businessModel,
            json.dumps(contextPayload, ensure_ascii=False),
            json.dumps(modifierPayload, ensure_ascii=False),
            confidenceScore,
        ),
    )
    return int(result[1]) if result and result[0] else None


def updateModifiers(runId: int, modifiers: list[dict]) -> int:
    updated = 0
    for modifier in modifiers:
        impactModifier = clampModifier(modifier.get("impactModifier", 0.0))
        financialModifier = clampModifier(modifier.get("financialModifier", 0.0))
        ok = save(
            """
            UPDATE ESG_DMA_SCORE_SUMMARY
            SET context_impact_modifier = ?,
                context_financial_modifier = ?
            WHERE esg_materiality_run_id = ?
              AND sub_issue_code = ?
              AND delete_yn = 0
            """,
            (
                impactModifier,
                financialModifier,
                runId,
                modifier.get("subIssueCode"),
            ),
        )
        if ok:
            updated += 1
    return updated


def getLatestProfile(runId: int) -> dict:
    sql = """
        SELECT
            id,
            esg_materiality_run_id,
            company_id,
            reporting_year,
            industry_profile,
            business_model,
            context_json,
            modifier_json,
            confidence_score,
            created_at,
            updated_at
        FROM ESG_DMA_CONTEXT_PROFILE
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
    """
    return findOne(sql, (runId,)) or {}


def decimalToFloat(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def clampModifier(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    if parsed < SYSTEM_MODIFIER_MIN:
        return SYSTEM_MODIFIER_MIN
    if parsed > SYSTEM_MODIFIER_MAX:
        return SYSTEM_MODIFIER_MAX
    return parsed


# Compatibility wrappers for previous public names

def getMaterialityRunContext(runId: int) -> dict:
    return getRun(runId)


def getCompanyG0Facts(companyId: int, reportingYear: int) -> list[dict]:
    return listG0Facts(companyId, reportingYear)


def getDmaScoreSummaryRowsForContext(runId: int) -> list[dict]:
    return listScoreRows(runId)


def replaceCompanyContextProfile(
    runId: int,
    companyId: int,
    reportingYear: int,
    industryProfile: Optional[str],
    businessModel: Optional[str],
    contextPayload: dict,
    modifierPayload: dict,
    confidenceScore: float,
) -> Optional[int]:
    return replaceProfile(
        runId,
        companyId,
        reportingYear,
        industryProfile,
        businessModel,
        contextPayload,
        modifierPayload,
        confidenceScore,
    )


def updateContextModifiers(runId: int, modifiers: list[dict]) -> int:
    return updateModifiers(runId, modifiers)


def getLatestCompanyContextProfile(runId: int) -> dict:
    return getLatestProfile(runId)


def clampSystemModifier(value: Any) -> float:
    return clampModifier(value)


__all__ = [
    "getRun",
    "getMaterialityRunContext",
    "listG0Facts",
    "getCompanyG0Facts",
    "listScoreRows",
    "getDmaScoreSummaryRowsForContext",
    "replaceProfile",
    "replaceCompanyContextProfile",
    "updateModifiers",
    "updateContextModifiers",
    "getLatestProfile",
    "getLatestCompanyContextProfile",
    "clampModifier",
    "clampSystemModifier",
    "decimalToFloat",
]
