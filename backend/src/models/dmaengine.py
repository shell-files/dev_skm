from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict

# --- v8.2 DMA Pydantic Schemas ---

class DMAContextProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    companyId: int = Field(..., alias="company_id")
    reportingYear: int = Field(..., alias="reporting_year")
    industryProfile: str = Field(..., alias="industry_profile")
    businessModel: str = Field(..., alias="business_model")
    valueChainExposure: dict = Field(..., alias="value_chain_exposure")
    revenueExposure: dict = Field(..., alias="revenue_exposure")
    regulatoryExposure: dict = Field(..., alias="regulatory_exposure")
    contextModifierBySubIssue: dict = Field(..., alias="context_modifier_by_sub_issue")
    iroHorizonHintBySubIssue: dict = Field(..., alias="iro_horizon_hint_by_sub_issue")
    confidence: float

class ImpactAssessment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    impactDirection: Literal["positive", "negative"] = Field(..., alias="impact_direction")
    actuality: Literal["actual", "potential"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    irremediability: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    timeHorizon: Literal["short", "mid", "long"] = Field(..., alias="time_horizon")
    impactScore: float = Field(..., alias="impact_score")
    evidenceSpans: List[str] = Field(..., alias="evidence_spans")

class FinancialAssessment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    financialIroType: Literal["risk", "opportunity"] = Field(..., alias="financial_iro_type")
    revenueMagnitude: int = Field(..., ge=0, le=5, alias="revenue_magnitude")
    costMagnitude: int = Field(..., ge=0, le=5, alias="cost_magnitude")
    capexMagnitude: int = Field(..., ge=0, le=5, alias="capex_magnitude")
    assetLiabilityMagnitude: int = Field(..., ge=0, le=5, alias="asset_liability_magnitude")
    financingMagnitude: int = Field(..., ge=0, le=5, alias="financing_magnitude")
    legalRegulatoryMagnitude: int = Field(..., ge=0, le=5, alias="legal_regulatory_magnitude")
    likelihood: int = Field(..., ge=0, le=5)
    timeHorizon: Literal["short", "mid", "long"] = Field(..., alias="time_horizon")
    financialScore: float = Field(..., alias="financial_score")
    evidenceSpans: List[str] = Field(..., alias="evidence_spans")

class DMAScoreDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    subIssueCode: str = Field(..., alias="sub_issue_code")
    issueSimilarityScore: float = Field(..., alias="issue_similarity_score")
    similarityRank: Optional[int] = Field(None, alias="similarity_rank")
    similarityThreshold: float = Field(0.60, alias="similarity_threshold")
    mappingWeight: float = Field(..., alias="mapping_weight")
    mappingMethod: Literal["dictionary_similarity", "hard_mapping", "manual_override", "direct_survey_item"] = Field(..., alias="mapping_method")
    matchedDictionaryTerms: List[str] = Field(..., alias="matched_dictionary_terms")
    sourceStep: Literal["benchmark", "media_external", "survey"] = Field(..., alias="source_step")
    sourceType: str = Field(..., alias="source_type")
    iroType: Literal["financial_risk", "financial_opportunity", "negative_impact", "positive_impact", "context"] = Field(..., alias="iro_type")
    timeHorizon: Literal["short", "mid", "long"] = Field(..., alias="time_horizon")
    impacts: List[ImpactAssessment]
    financials: List[FinancialAssessment]
    confidenceScore: float = Field(..., alias="confidence_score")
    evidenceId: Optional[str] = Field(None, alias="evidence_id")
    judgeStatus: Literal["pass", "revise", "reject"] = Field(..., alias="judge_status")
    judgeReason: Optional[str] = Field(None, alias="judge_reason")

class LLMSubIssueExtraction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    rawIssueLabel: str = Field(..., description="본문에 등장한 원문 이슈 표현", alias="raw_issue_label")
    candidateDictionaryTerms: List[str] = Field(..., description="62개 사전 중 관련성 있어 보이는 후보군 리스트", alias="candidate_dictionary_terms")
    iroHint: Literal["financial_risk", "financial_opportunity", "negative_impact", "positive_impact", "context"] = Field(..., alias="iro_hint")
    timeHorizonHint: Literal["short", "mid", "long"] = Field(..., alias="time_horizon_hint")
    evidenceSpans: List[str] = Field(..., description="이슈로 판단한 구체적인 본문 문장", alias="evidence_spans")

class LLMExtractorOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    extractedIssues: List[LLMSubIssueExtraction] = Field(..., description="문서에서 추출된 이슈 목록", alias="extracted_issues")

class DMAAgentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    companyId: int = Field(..., alias="company_id")
    reportingYear: int = Field(..., alias="reporting_year")
    esgMaterialityRunId: int = Field(..., alias="esg_materiality_run_id")
    sourceType: str = Field(..., alias="source_type")
    sourceStep: str = Field(..., alias="source_step")
    payload: dict

class ImpactFactor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    impactDirection: Literal["positive", "negative"] = Field(..., alias="impact_direction")
    actuality: Literal["actual", "potential"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    irremediability: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    timeHorizon: Literal["short", "mid", "long"] = Field(..., alias="time_horizon")
    evidenceSpans: List[str] = Field(default=[], alias="evidence_spans")

class FinancialFactor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    financialIroType: Literal["risk", "opportunity"] = Field(..., alias="financial_iro_type")
    revenueMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="revenue_magnitude")
    costMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="cost_magnitude")
    capexMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="capex_magnitude")
    assetLiabilityMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="asset_liability_magnitude")
    financingMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="financing_magnitude")
    legalRegulatoryMagnitude: Optional[int] = Field(None, ge=0, le=5, alias="legal_regulatory_magnitude")
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    timeHorizon: Literal["short", "mid", "long"] = Field(..., alias="time_horizon")
    evidenceSpans: List[str] = Field(default=[], alias="evidence_spans")

class DMASignal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    subIssueCode: str = Field(..., alias="sub_issue_code")
    sourceStep: Literal["benchmark", "media_external", "survey"] = Field(..., alias="source_step")
    sourceType: str = Field(..., alias="source_type")
    impactFactor: Optional[ImpactFactor] = Field(None, alias="impact_factor")
    financialFactor: Optional[FinancialFactor] = Field(None, alias="financial_factor")
    impactScore05: Optional[float] = Field(None, alias="impact_score_0_5")
    financialScore05: Optional[float] = Field(None, alias="financial_score_0_5")
    confidenceScore: float = Field(1.0, alias="confidence_score")
    evidenceId: Optional[str] = Field(None, alias="evidence_id")
    teSrFileId: Optional[int] = Field(None, alias="te_sr_file_id")
    rawIssueLabel: Optional[str] = Field(None, alias="raw_issue_label")
    displaySubIssueName: Optional[str] = Field(None, alias="display_sub_issue_name")
    similarityScore: Optional[float] = Field(None, alias="similarity_score")
    similarityRank: Optional[int] = Field(None, alias="similarity_rank")
    mappingWeight: Optional[float] = Field(None, alias="mapping_weight")
    mappingMethod: Optional[str] = Field("dictionary_similarity", alias="mapping_method")
    judgeStatus: Optional[str] = Field(None, alias="judge_status")
    evidenceSpans: List[str] = Field(default=[], alias="evidence_spans")
    
    # 확장된 메타데이터 추적 필드
    sourceTitle: Optional[str] = Field(None, alias="source_title")
    sourceUrl: Optional[str] = Field(None, alias="source_url")
    publishedAt: Optional[str] = Field(None, alias="published_at")
    scoringPayloadJson: Optional[dict] = Field(None, alias="scoring_payload_json")

class StageScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    impactScore05: Optional[float] = Field(None, alias="impact_score_0_5")
    financialScore05: Optional[float] = Field(None, alias="financial_score_0_5")

class FinalMaterialityScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    subIssueCode: str = Field(..., alias="sub_issue_code")
    finalImpactScore: Optional[float] = Field(None, alias="final_impact_score")
    finalFinancialScore: Optional[float] = Field(None, alias="final_financial_score")
    finalScore: Optional[float] = Field(None, alias="final_score")
    coverage: dict
