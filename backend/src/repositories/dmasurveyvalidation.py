"""
dmasurveyvalidation.py
레이어: Repository
역할: DMA 설문 runId·formId 유효성 검증 헬퍼.
"""
from __future__ import annotations


def validateRunId(runId) -> None:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")


def validateFormId(formId) -> None:
    if isinstance(formId, bool) or not isinstance(formId, int):
        raise ValueError(f"surveyFormId must be a strict int, got {type(formId).__name__}")
    if formId <= 0:
        raise ValueError(f"surveyFormId must be > 0, got {formId}")
