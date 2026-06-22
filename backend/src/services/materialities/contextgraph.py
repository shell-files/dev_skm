"""
contextgraph.py
레이어: Service (materialities)
역할: LangGraph/LangChain 기반 기업 컨텍스트 프로필 생성 — LLM 비활성화 시 결정론적 빌더 폴백.

주요 함수:
  buildCompanyContextProfileWithOptionalGraph — 기업 컨텍스트 프로필 생성
"""

from __future__ import annotations

import json
import re
from typing import Callable, Optional, TypedDict

from src.models.materialitycontext import CompanyContextFactDto, CompanyContextProfileDto
from src.utils.settings import settings


MIN_LLM_PROFILE_CONFIDENCE = 0.5
PROFILE_SOURCE_LLM = "LANGGRAPH_LLM"
PROFILE_SOURCE_FALLBACK = "DETERMINISTIC_FALLBACK"
ALLOWED_LEVELS = {"unknown", "low", "medium", "high"}
ALLOWED_INDUSTRY_EXPOSURES = {"unknown", "automotive_parts_high"}


class CompanyContextGraphState(TypedDict, total=False):
    runId: int
    runContext: dict
    facts: list[CompanyContextFactDto]
    normalizedFacts: list[dict]
    evidenceMetricIds: list[str]
    evidenceAtomicMetricIds: list[str]
    llmPayload: dict
    profile: CompanyContextProfileDto
    fallbackReason: Optional[str]
    trace: list[dict]


def buildCompanyContextProfileWithOptionalGraph(
    runId: int,
    runContext: dict,
    facts: list[CompanyContextFactDto],
    deterministicBuilder: Callable[[int, dict, list[CompanyContextFactDto]], CompanyContextProfileDto],
) -> tuple[CompanyContextProfileDto, list[dict]]:
    """LLM(Ollama) 사용 여부에 따라 LangGraph 파이프라인 또는 결정론적 빌더로 회사 컨텍스트 프로필을 생성하고 trace 로그와 함께 반환한다."""
    trace: list[dict] = []
    fallbackProfile = deterministicBuilder(runId, runContext, facts)
    fallbackProfile.profileSource = PROFILE_SOURCE_FALLBACK

    if not _llmEnabled():
        trace.append(_trace("fallbackIfLowConfidence", "SKIPPED", "COMPANY_CONTEXT_LLM_ENABLED is not true."))
        return fallbackProfile, trace

    provider = settings.company_context_llm_provider.strip().lower()
    model = settings.company_context_llm_model.strip()
    if provider != "ollama" or not model:
        trace.append(_trace("fallbackIfLowConfidence", "SKIPPED", "LLM provider/model is not configured."))
        return fallbackProfile, trace

    try:
        from langgraph.graph import END, StateGraph
        from langchain_ollama import ChatOllama
    except Exception as exc:
        trace.append(_trace("fallbackIfLowConfidence", "SKIPPED", f"LangGraph/LangChain import failed: {exc}"))
        return fallbackProfile, trace

    try:
        timeout = settings.company_context_llm_timeout_sec
        llm = ChatOllama(model=model, timeout=timeout)

        def loadG0Facts(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """G0 fact 목록을 state에 로드하고 trace를 기록한다."""
            state.setdefault("trace", []).append(_trace("loadG0Facts", "OK", f"{len(facts)} facts loaded."))
            return state

        def normalizeG0Context(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """fact 목록을 정규화하고 증거 metricId·atomicMetricId 집합을 state에 저장한다."""
            normalizedFacts = [_normalizeFact(fact) for fact in facts]
            state["normalizedFacts"] = normalizedFacts
            state["evidenceMetricIds"] = sorted({item["metricId"] for item in normalizedFacts if item.get("metricId")})
            state["evidenceAtomicMetricIds"] = sorted({item["atomicMetricId"] for item in normalizedFacts if item.get("atomicMetricId")})
            state.setdefault("trace", []).append(_trace("normalizeG0Context", "OK", f"{len(normalizedFacts)} facts normalized."))
            return state

        def analyzeCompanyProfileByLLM(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """LLM에 프롬프트를 전송하고 JSON 응답을 파싱해 llmPayload로 state에 저장한다."""
            prompt = _buildPrompt(runContext, state.get("normalizedFacts", []))
            response = llm.invoke(prompt)
            content = getattr(response, "content", response)
            state["llmPayload"] = _parseJsonPayload(str(content))
            state.setdefault("trace", []).append(_trace("analyzeCompanyProfileByLLM", "OK", "LLM profile candidate generated."))
            return state

        def validateProfileSchema(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """llmPayload를 정제해 CompanyContextProfileDto로 변환하고 state에 저장한다."""
            payload = _sanitizePayload(state.get("llmPayload") or {})
            payload.update({
                "runId": runId,
                "companyId": int(runContext["company_id"]),
                "reportingYear": int(runContext["reporting_year"]),
                "industryProfile": runContext.get("industry_profile"),
                "profileSource": PROFILE_SOURCE_LLM,
                "facts": facts,
            })
            state["profile"] = CompanyContextProfileDto(**payload)
            state.setdefault("trace", []).append(_trace("validateProfileSchema", "OK", "Pydantic schema validated."))
            return state

        def verifyProfileAgainstEvidence(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """프로필의 증거 ID를 실제 fact와 교차 검증하고, 일치하는 증거가 없으면 신뢰도를 하향 조정한다."""
            profile = state["profile"]
            metricIds = set(state.get("evidenceMetricIds") or [])
            atomicIds = set(state.get("evidenceAtomicMetricIds") or [])
            profile.evidenceMetricIds = [item for item in profile.evidenceMetricIds if item in metricIds]
            profile.evidenceAtomicMetricIds = [item for item in profile.evidenceAtomicMetricIds if item in atomicIds]
            if not profile.evidenceMetricIds and not profile.evidenceAtomicMetricIds:
                profile.confidence = min(float(profile.confidence or 0.0), 0.3)
                _downgradeUnsupportedHighExposure(profile)
                state.setdefault("trace", []).append(_trace("verifyProfileAgainstEvidence", "WARN", "No linked evidence ids; confidence downgraded."))
            else:
                state.setdefault("trace", []).append(_trace("verifyProfileAgainstEvidence", "OK", "Evidence ids verified."))
            state["profile"] = profile
            return state

        def fallbackIfLowConfidence(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """신뢰도가 임계값 미만이면 폴백 이유를 기록하고, 그렇지 않으면 LLM 프로필을 승인한다."""
            profile = state.get("profile")
            if not profile or float(profile.confidence or 0.0) < MIN_LLM_PROFILE_CONFIDENCE:
                state["fallbackReason"] = "LOW_CONTEXT_CONFIDENCE"
                state.setdefault("trace", []).append(_trace("fallbackIfLowConfidence", "FALLBACK", "LLM profile confidence is below threshold."))
            else:
                state.setdefault("trace", []).append(_trace("fallbackIfLowConfidence", "OK", "LLM profile accepted."))
            return state

        def returnCompanyContextProfile(state: CompanyContextGraphState) -> CompanyContextGraphState:
            """최종 프로필 반환 완료를 trace에 기록한다."""
            state.setdefault("trace", []).append(_trace("returnCompanyContextProfile", "OK", "CompanyContextProfile returned."))
            return state

        graph = StateGraph(CompanyContextGraphState)
        graph.add_node("loadG0Facts", loadG0Facts)
        graph.add_node("normalizeG0Context", normalizeG0Context)
        graph.add_node("analyzeCompanyProfileByLLM", analyzeCompanyProfileByLLM)
        graph.add_node("validateProfileSchema", validateProfileSchema)
        graph.add_node("verifyProfileAgainstEvidence", verifyProfileAgainstEvidence)
        graph.add_node("fallbackIfLowConfidence", fallbackIfLowConfidence)
        graph.add_node("returnCompanyContextProfile", returnCompanyContextProfile)
        graph.set_entry_point("loadG0Facts")
        graph.add_edge("loadG0Facts", "normalizeG0Context")
        graph.add_edge("normalizeG0Context", "analyzeCompanyProfileByLLM")
        graph.add_edge("analyzeCompanyProfileByLLM", "validateProfileSchema")
        graph.add_edge("validateProfileSchema", "verifyProfileAgainstEvidence")
        graph.add_edge("verifyProfileAgainstEvidence", "fallbackIfLowConfidence")
        graph.add_edge("fallbackIfLowConfidence", "returnCompanyContextProfile")
        graph.add_edge("returnCompanyContextProfile", END)

        result = graph.compile().invoke({
            "runId": runId,
            "runContext": runContext,
            "facts": facts,
            "trace": trace,
        })
        resultTrace = result.get("trace") or trace
        if result.get("fallbackReason"):
            fallbackProfile.profileSource = PROFILE_SOURCE_FALLBACK
            return fallbackProfile, resultTrace
        return result["profile"], resultTrace
    except Exception as exc:
        trace.append(_trace("fallbackIfLowConfidence", "FALLBACK", f"LangGraph profiler failed: {exc}"))
        fallbackProfile.profileSource = PROFILE_SOURCE_FALLBACK
        return fallbackProfile, trace


def _llmEnabled() -> bool:
    return settings.company_context_llm_enabled


def _normalizeFact(fact: CompanyContextFactDto) -> dict:
    return {
        "sourceTable": fact.sourceTable,
        "metricId": fact.metricId,
        "atomicMetricId": fact.atomicMetricId,
        "metricName": _truncate(fact.metricName),
        "atomicName": _truncate(fact.atomicName),
        "valueText": _truncate(fact.valueText, 700),
        "valueNumeric": fact.valueNumeric,
        "unit": fact.unit,
    }


def _buildPrompt(runContext: dict, normalizedFacts: list[dict]) -> str:
    return (
        "You are an ESG company context profiler. "
        "Return JSON only. Do not calculate DMA scores, modifiers, ranks, or selected issues.\n"
        "Allowed industryExposure: unknown, automotive_parts_high.\n"
        "Allowed exposure levels: unknown, low, medium, high.\n"
        "Required JSON keys: industryExposure, valueChainExposure, globalCustomerExposure, "
        "euRegulationExposure, transitionExposure, supplyChainDependency, productSafetyExposure, "
        "businessScaleExposure, profileSummary, evidenceMetricIds, evidenceAtomicMetricIds, "
        "evidenceText, confidence.\n"
        f"Run context: {json.dumps(runContext, ensure_ascii=False, default=str)}\n"
        f"G0 facts: {json.dumps(normalizedFacts, ensure_ascii=False, default=str)}"
    )


def _parseJsonPayload(content: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
    raw = fenced.group(1) if fenced else content
    if "{" in raw and "}" in raw:
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def _sanitizePayload(payload: dict) -> dict:
    result = dict(payload)
    result["industryExposure"] = _allowed(result.get("industryExposure"), ALLOWED_INDUSTRY_EXPOSURES)
    for key in [
        "valueChainExposure",
        "globalCustomerExposure",
        "euRegulationExposure",
        "transitionExposure",
        "supplyChainDependency",
        "productSafetyExposure",
        "businessScaleExposure",
    ]:
        result[key] = _allowed(result.get(key), ALLOWED_LEVELS)
    result["evidenceMetricIds"] = _stringList(result.get("evidenceMetricIds"))
    result["evidenceAtomicMetricIds"] = _stringList(result.get("evidenceAtomicMetricIds"))
    result["evidenceText"] = _stringList(result.get("evidenceText"))[:5]
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    except (TypeError, ValueError):
        result["confidence"] = 0.0
    return result


def _downgradeUnsupportedHighExposure(profile: CompanyContextProfileDto) -> None:
    for field in [
        "valueChainExposure",
        "globalCustomerExposure",
        "euRegulationExposure",
        "transitionExposure",
        "supplyChainDependency",
        "productSafetyExposure",
        "businessScaleExposure",
    ]:
        if getattr(profile, field) == "high":
            setattr(profile, field, "medium")


def _allowed(value: object, allowed: set[str]) -> str:
    parsed = str(value or "unknown").strip()
    return parsed if parsed in allowed else "unknown"


def _stringList(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _truncate(value: Optional[str], limit: int = 250) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit]


def _trace(node: str, status: str, message: str) -> dict:
    return {
        "node": node,
        "status": status,
        "message": message,
    }
