"""
Domain: DMA Materiality
Layer: service/optional-llm
Responsibility:
- Optionally build CompanyContextProfile with LangGraph/LangChain
- Fallback to deterministic profile builder when LLM is disabled or fails
- Validate and verify profile evidence
Public functions:
- buildCompanyContextProfileWithOptionalGraph
Do not:
- do not mutate unrelated DB state
- do not calculate DMA score, modifier, rank, or selected issue
- do not make LLM failure an API failure
- do not change scoring formula unless explicitly requested
- do not modify deterministic scoring pipeline
- do not call FastAPI router directly
- do not modify auth/token/common code
"""

from __future__ import annotations

import json
import os
import re
from typing import Callable, Optional, TypedDict

from src.models.materialitycontext import CompanyContextFactDto, CompanyContextProfileDto


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
    trace: list[dict] = []
    fallbackProfile = deterministicBuilder(runId, runContext, facts)
    fallbackProfile.profileSource = PROFILE_SOURCE_FALLBACK

    if not _llmEnabled():
        trace.append(_trace("fallbackIfLowConfidence", "SKIPPED", "COMPANY_CONTEXT_LLM_ENABLED is not true."))
        return fallbackProfile, trace

    provider = os.getenv("COMPANY_CONTEXT_LLM_PROVIDER", "").strip().lower()
    model = os.getenv("COMPANY_CONTEXT_LLM_MODEL", "").strip()
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
        timeout = float(os.getenv("COMPANY_CONTEXT_LLM_TIMEOUT_SEC", "60") or 60)
        llm = ChatOllama(model=model, timeout=timeout)

        def loadG0Facts(state: CompanyContextGraphState) -> CompanyContextGraphState:
            state.setdefault("trace", []).append(_trace("loadG0Facts", "OK", f"{len(facts)} facts loaded."))
            return state

        def normalizeG0Context(state: CompanyContextGraphState) -> CompanyContextGraphState:
            normalizedFacts = [_normalizeFact(fact) for fact in facts]
            state["normalizedFacts"] = normalizedFacts
            state["evidenceMetricIds"] = sorted({item["metricId"] for item in normalizedFacts if item.get("metricId")})
            state["evidenceAtomicMetricIds"] = sorted({item["atomicMetricId"] for item in normalizedFacts if item.get("atomicMetricId")})
            state.setdefault("trace", []).append(_trace("normalizeG0Context", "OK", f"{len(normalizedFacts)} facts normalized."))
            return state

        def analyzeCompanyProfileByLLM(state: CompanyContextGraphState) -> CompanyContextGraphState:
            prompt = _buildPrompt(runContext, state.get("normalizedFacts", []))
            response = llm.invoke(prompt)
            content = getattr(response, "content", response)
            state["llmPayload"] = _parseJsonPayload(str(content))
            state.setdefault("trace", []).append(_trace("analyzeCompanyProfileByLLM", "OK", "LLM profile candidate generated."))
            return state

        def validateProfileSchema(state: CompanyContextGraphState) -> CompanyContextGraphState:
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
            profile = state.get("profile")
            if not profile or float(profile.confidence or 0.0) < MIN_LLM_PROFILE_CONFIDENCE:
                state["fallbackReason"] = "LOW_CONTEXT_CONFIDENCE"
                state.setdefault("trace", []).append(_trace("fallbackIfLowConfidence", "FALLBACK", "LLM profile confidence is below threshold."))
            else:
                state.setdefault("trace", []).append(_trace("fallbackIfLowConfidence", "OK", "LLM profile accepted."))
            return state

        def returnCompanyContextProfile(state: CompanyContextGraphState) -> CompanyContextGraphState:
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
    return os.getenv("COMPANY_CONTEXT_LLM_ENABLED", "false").strip().lower() == "true"


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
