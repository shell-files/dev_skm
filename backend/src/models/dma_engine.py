from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

# --- v8.2 DMA Pydantic Schemas ---

class DMAContextProfile(BaseModel):
    company_id: int
    reporting_year: int
    industry_profile: str
    business_model: str
    value_chain_exposure: dict
    revenue_exposure: dict
    regulatory_exposure: dict
    context_modifier_by_sub_issue: dict
    iro_horizon_hint_by_sub_issue: dict
    confidence: float

class ImpactAssessment(BaseModel):
    impact_direction: Literal["positive", "negative"]
    actuality: Literal["actual", "potential"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    irremediability: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    impact_score: float
    evidence_spans: List[str]

class FinancialAssessment(BaseModel):
    financial_iro_type: Literal["risk", "opportunity"]
    revenue_magnitude: int = Field(..., ge=0, le=5)
    cost_magnitude: int = Field(..., ge=0, le=5)
    capex_magnitude: int = Field(..., ge=0, le=5)
    asset_liability_magnitude: int = Field(..., ge=0, le=5)
    financing_magnitude: int = Field(..., ge=0, le=5)
    legal_regulatory_magnitude: int = Field(..., ge=0, le=5)
    likelihood: int = Field(..., ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    financial_score: float
    evidence_spans: List[str]

class DMAScoreDetail(BaseModel):
    sub_issue_code: str
    issue_similarity_score: float
    similarity_rank: Optional[int]
    similarity_threshold: float = 0.60
    mapping_weight: float
    mapping_method: Literal["dictionary_similarity", "hard_mapping", "manual_override", "direct_survey_item"]
    matched_dictionary_terms: List[str]
    source_step: Literal["benchmark", "media_external", "survey"]
    source_type: str
    iro_type: Literal["financial_risk", "financial_opportunity", "negative_impact", "positive_impact", "context"]
    time_horizon: Literal["short", "mid", "long"]
    impacts: List[ImpactAssessment]
    financials: List[FinancialAssessment]
    confidence_score: float
    evidence_id: Optional[str]
    judge_status: Literal["pass", "revise", "reject"]
    judge_reason: Optional[str]

# --- LLM Extractor 용 보조 스키마 (v8.2) ---
# LLM은 위 DMAScoreDetail 같은 복잡한 연산을 직접 하지 못하므로,
# 오직 본문에서 후보(Sub-issue)와 근거만 추출해내는 스키마를 별도로 정의합니다.

class LLMSubIssueExtraction(BaseModel):
    raw_issue_label: str = Field(..., description="본문에 등장한 원문 이슈 표현")
    candidate_dictionary_terms: List[str] = Field(..., description="62개 사전 중 관련성 있어 보이는 후보군 리스트")
    iro_hint: Literal["financial_risk", "financial_opportunity", "negative_impact", "positive_impact", "context"] = Field(...)
    time_horizon_hint: Literal["short", "mid", "long"] = Field(...)
    evidence_spans: List[str] = Field(..., description="이슈로 판단한 구체적인 본문 문장")

class LLMExtractorOutput(BaseModel):
    extracted_issues: List[LLMSubIssueExtraction] = Field(..., description="문서에서 추출된 이슈 목록")

# --- v8.2 Phase 1: DMA Common Contracts ---

class DMAAgentRequest(BaseModel):
    company_id: int
    reporting_year: int
    esg_materiality_run_id: int
    source_type: str
    source_step: str
    payload: dict

class ImpactFactor(BaseModel):
    impact_direction: Literal["positive", "negative"]
    actuality: Literal["actual", "potential"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    irremediability: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    evidence_spans: List[str] = []

class FinancialFactor(BaseModel):
    financial_iro_type: Literal["risk", "opportunity"]
    revenue_magnitude: Optional[int] = Field(None, ge=0, le=5)
    cost_magnitude: Optional[int] = Field(None, ge=0, le=5)
    capex_magnitude: Optional[int] = Field(None, ge=0, le=5)
    asset_liability_magnitude: Optional[int] = Field(None, ge=0, le=5)
    financing_magnitude: Optional[int] = Field(None, ge=0, le=5)
    legal_regulatory_magnitude: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    evidence_spans: List[str] = []

class DMASignal(BaseModel):
    sub_issue_code: str
    source_step: Literal["benchmark", "media_external", "survey"]
    source_type: str
    impact_factor: Optional[ImpactFactor] = None
    financial_factor: Optional[FinancialFactor] = None
    impact_score_0_5: Optional[float] = None
    financial_score_0_5: Optional[float] = None
    confidence_score: float = 1.0
    evidence_id: Optional[str] = None
    te_sr_file_id: Optional[int] = None
    raw_issue_label: Optional[str] = None
    display_sub_issue_name: Optional[str] = None
    similarity_score: Optional[float] = None
    similarity_rank: Optional[int] = None
    mapping_weight: Optional[float] = None
    mapping_method: Optional[str] = "dictionary_similarity"
    judge_status: Optional[str] = None
    evidence_spans: List[str] = []

class StageScore(BaseModel):
    impact_score_0_5: Optional[float]
    financial_score_0_5: Optional[float]

class FinalMaterialityScore(BaseModel):
    sub_issue_code: str
    final_impact_score: Optional[float]
    final_financial_score: Optional[float]
    final_score: Optional[float]
    coverage: dict
