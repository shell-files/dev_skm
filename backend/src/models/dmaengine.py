from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, List, Optional, Literal, Dict

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


# =====================================================================================
# DMA v1.3 MVP Slim Canonical Engine — DTO / Enum (PARALLEL ADDITION)
# =====================================================================================
# These types are added IN PARALLEL to the legacy v8.2 schemas above. Nothing above is
# modified or removed. The v1.3 canonical path is opt-in and not wired into any service,
# API, or DB in Phase A.
#
# Hard rules enforced by these types:
#  - AI emits FACTS ONLY. Score fields are forbidden in ExtractedFactsV13 (extra="forbid").
#  - Missing required factor -> axis UNOBSERVED (never 0 substitution).
#  - Screening signal != canonical impact/financial score != final DMA rank.
# =====================================================================================


class TriState(str, Enum):
    """Three-valued logic for AI-extracted boolean-ish facts (no implicit False)."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class FactorStatusV13(str, Enum):
    """Per-factor / per-axis observation status."""

    AUTO_CONFIRMED = "AUTO_CONFIRMED"
    PRESET_FALLBACK = "PRESET_FALLBACK"
    UNOBSERVED = "UNOBSERVED"
    REJECTED = "REJECTED"
    CONFLICTED = "CONFLICTED"


class DecisionSourceV13(str, Enum):
    """Where a factor decision came from (rule engine vs preset vs rejection)."""

    RULE_AUTO = "RULE_AUTO"
    PRESET_FALLBACK = "PRESET_FALLBACK"
    UNOBSERVED = "UNOBSERVED"
    REJECTED = "REJECTED"
    CONFLICTED = "CONFLICTED"


class ScorePurposeV13(str, Enum):
    """The purpose of a computed score. Screening is NOT a canonical IRO score."""

    CANONICAL_IRO = "CANONICAL_IRO"
    PRESURVEY_SCREENING = "PRESURVEY_SCREENING"
    STAKEHOLDER_OVERLAY = "STAKEHOLDER_OVERLAY"
    LEGACY_STAGE_SCORE = "LEGACY_STAGE_SCORE"


class EvidenceSpanV13(BaseModel):
    """A single piece of supporting evidence for a fact/score. Read-only provenance."""

    model_config = ConfigDict(populate_by_name=True)

    textSpan: str = Field(..., alias="text_span")
    sourceType: Optional[str] = Field(None, alias="source_type")
    sourceTitle: Optional[str] = Field(None, alias="source_title")
    sourceUrl: Optional[str] = Field(None, alias="source_url")
    sourcePageNo: Optional[int] = Field(None, alias="source_page_no")
    publishedAt: Optional[str] = Field(None, alias="published_at")
    teCrawlingId: Optional[int] = Field(None, alias="te_crawling_id")


class ExtractedFactsV13(BaseModel):
    """
    AI-extracted facts only. NO score fields are permitted here.

    ``extra="forbid"`` means any forbidden field (e.g. proposedScore, scale,
    magnitude, sameEventGroupId) raises pydantic ValidationError on construction.
    Only ``eventGroupCandidateId`` (a candidate, not a confirmed dedup decision)
    is allowed among grouping fields.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    subIssueCode: Optional[str] = Field(None, alias="sub_issue_code")
    eventType: Optional[str] = Field(None, alias="event_type")
    impactDirection: Optional[Literal["positive", "negative"]] = Field(None, alias="impact_direction")
    financialIroType: Optional[Literal["risk", "opportunity"]] = Field(None, alias="financial_iro_type")
    actualYn: Optional[TriState] = Field(None, alias="actual_yn")
    officialConfirmedYn: Optional[TriState] = Field(None, alias="official_confirmed_yn")
    explicitImmediateActionYn: Optional[TriState] = Field(None, alias="explicit_immediate_action_yn")
    explicitNoUrgencyYn: Optional[TriState] = Field(None, alias="explicit_no_urgency_yn")
    affectedCount: Optional[int] = Field(None, alias="affected_count")
    financialAmount: Optional[float] = Field(None, alias="financial_amount")
    ratioValue: Optional[float] = Field(None, alias="ratio_value")
    probabilityValue: Optional[float] = Field(None, alias="probability_value")
    eventDate: Optional[str] = Field(None, alias="event_date")
    effectiveDate: Optional[str] = Field(None, alias="effective_date")
    deadlineDate: Optional[str] = Field(None, alias="deadline_date")
    sourceType: Optional[str] = Field(None, alias="source_type")
    classificationConfidence: Optional[float] = Field(None, alias="classification_confidence")
    eventGroupCandidateId: Optional[str] = Field(None, alias="event_group_candidate_id")
    evidenceSpans: List[EvidenceSpanV13] = Field(default_factory=list, alias="evidence_spans")
    rawMetadata: Dict[str, Any] = Field(default_factory=dict, alias="raw_metadata")


class FactorTraceV13(BaseModel):
    """Explainability trace for a single scoring factor within an axis."""

    model_config = ConfigDict(populate_by_name=True)

    factorName: str = Field(..., alias="factor_name")
    observedValue: Optional[float] = Field(None, alias="observed_value")
    status: FactorStatusV13
    decisionSource: DecisionSourceV13 = Field(..., alias="decision_source")
    baseWeight: Optional[float] = Field(None, alias="base_weight")
    effectiveWeight: Optional[float] = Field(None, alias="effective_weight")
    contribution: Optional[float] = Field(None, alias="contribution")
    note: Optional[str] = None


class AxisScoreTraceV13(BaseModel):
    """
    Canonical axis (impact|financial) result + full reweight trace.

    ``score`` is None iff ``status == UNOBSERVED`` (a required factor was missing).
    ``score`` is always on the 0..5 canonical scale otherwise.
    """

    model_config = ConfigDict(populate_by_name=True)

    axis: Literal["impact", "financial"]
    polarity: str  # negative|positive (impact) / risk|opportunity (financial)
    score: Optional[float] = None
    status: FactorStatusV13
    scorePurpose: ScorePurposeV13 = Field(ScorePurposeV13.CANONICAL_IRO, alias="score_purpose")
    requiredFactors: List[str] = Field(default_factory=list, alias="required_factors")
    optionalFactors: List[str] = Field(default_factory=list, alias="optional_factors")
    observedFactors: List[str] = Field(default_factory=list, alias="observed_factors")
    missingRequired: List[str] = Field(default_factory=list, alias="missing_required")
    missingOptional: List[str] = Field(default_factory=list, alias="missing_optional")
    reweightApplied: bool = Field(False, alias="reweight_applied")
    offsettingAllowed: bool = Field(False, alias="offsetting_allowed")
    factorTraces: List[FactorTraceV13] = Field(default_factory=list, alias="factor_traces")
    ruleVersion: Optional[str] = Field(None, alias="rule_version")


class ScreeningTraceV13(BaseModel):
    """Pre-survey screening signal trace (benchmark / regulation / KCGS / KIS)."""

    model_config = ConfigDict(populate_by_name=True)

    channel: str
    scorePurpose: ScorePurposeV13 = Field(ScorePurposeV13.PRESURVEY_SCREENING, alias="score_purpose")
    impactSignal: Optional[float] = Field(None, alias="impact_signal")
    financialSignal: Optional[float] = Field(None, alias="financial_signal")
    status: str
    capability: Optional[str] = None
    rawInputs: Dict[str, Any] = Field(default_factory=dict, alias="raw_inputs")


class RegulationApplicabilityInputV13(BaseModel):
    """Company/year-specific manual regulation applicability input."""

    model_config = ConfigDict(extra="forbid")

    companyId: int = Field(..., strict=True, gt=0)
    reportingYear: int
    regime: str
    applicability: str
    inputMethod: str = "MANUAL"
    sourceDocumentRef: Optional[str] = None
    reviewStatus: str = "DRAFT"
    reviewerComment: Optional[str] = None


class RegulationSubIssueMappingSeedV13(BaseModel):
    """Draft mapping seed proposal from regulation regime to a sub-issue."""

    model_config = ConfigDict(extra="forbid")

    regime: str
    subIssueCode: str
    mappingReason: str
    activeYn: bool = False
    reviewStatus: str = "DRAFT"


class AggregationTraceV13(BaseModel):
    """Sub-issue axis aggregation trace. MAX over sources; offsetting forbidden."""

    model_config = ConfigDict(populate_by_name=True)

    subIssueCode: str = Field(..., alias="sub_issue_code")
    impactMethod: str = Field("MAX", alias="impact_method")
    financialMethod: str = Field("MAX", alias="financial_method")
    offsettingAllowed: bool = Field(False, alias="offsetting_allowed")
    impactScore: Optional[float] = Field(None, alias="impact_score")
    financialScore: Optional[float] = Field(None, alias="financial_score")
    impactSourceCount: int = Field(0, alias="impact_source_count")
    financialSourceCount: int = Field(0, alias="financial_source_count")


class LegacyCompatibilityV13(BaseModel):
    """
    Records how the v1.3 payload coexists with legacy data. The v1.3 path never
    migrates, reuses, or overwrites legacy scores.
    """

    model_config = ConfigDict(populate_by_name=True)

    legacyScoringPayloadPresentYn: bool = Field(False, alias="legacy_scoring_payload_present_yn")
    legacyMigratedYn: bool = Field(False, alias="legacy_migrated_yn")
    legacyScoreReusedYn: bool = Field(False, alias="legacy_score_reused_yn")
    legacyUpdatedYn: bool = Field(False, alias="legacy_updated_yn")
    legacyRuleVersion: Optional[str] = Field(None, alias="legacy_rule_version")


class MediaNewsResolvedAxisCandidateV13(BaseModel):
    """Resolver-level axis factor candidate before Canonical scoring."""

    model_config = ConfigDict(populate_by_name=True)

    polarity: Optional[str] = None
    scale: Optional[float] = None
    scope: Optional[float] = None
    likelihood: Optional[float] = None
    irremediability: Optional[float] = None
    magnitude: Optional[float] = None
    timeHorizon: Optional[str] = Field(None, alias="time_horizon")
    explicitNoUrgencyYn: Optional[TriState] = Field(None, alias="explicit_no_urgency_yn")
    ruleTrace: List[Dict[str, Any]] = Field(default_factory=list, alias="rule_trace")


class MediaNewsDedupTraceV13(BaseModel):
    """Event dedup status for a single media news observation."""

    model_config = ConfigDict(populate_by_name=True)

    eventGroupCandidateId: Optional[str] = Field(None, alias="event_group_candidate_id")
    confirmedEventGroupKey: Optional[str] = Field(None, alias="confirmed_event_group_key")
    dedupStatus: Literal["UNRESOLVED", "UNIQUE", "MERGED", "CONFLICTED", "REJECTED"] = Field(
        "UNRESOLVED", alias="dedup_status"
    )
    ruleTrace: List[Dict[str, Any]] = Field(default_factory=list, alias="rule_trace")


class MediaNewsEventResolutionTraceV13(BaseModel):
    """Full event resolution result for one media news fact."""

    model_config = ConfigDict(populate_by_name=True)

    resolverStatus: Literal["RESOLVED", "PARTIAL", "UNOBSERVED", "CONFLICTED", "REJECTED"] = Field(
        ..., alias="resolver_status"
    )
    subIssueCode: str = Field(..., alias="sub_issue_code")
    normalizedEventType: Optional[str] = Field(None, alias="normalized_event_type")
    eventDateBucket: Optional[str] = Field(None, alias="event_date_bucket")
    impact: Optional[MediaNewsResolvedAxisCandidateV13] = None
    financial: Optional[MediaNewsResolvedAxisCandidateV13] = None
    dedup: MediaNewsDedupTraceV13 = Field(default_factory=MediaNewsDedupTraceV13)


class ScoringPayloadV13(BaseModel):
    """
    The v1.3 canonical payload persisted (in Phase B/C) inside the existing
    ``ESG_DMA_SIGNAL_DETAIL.scoring_payload_json`` column. No new table/column.
    """

    model_config = ConfigDict(populate_by_name=True)

    factorPayloadSchemaVersion: str = Field("1.3", alias="factor_payload_schema_version")
    ruleVersion: str = Field(..., alias="rule_version")
    configHash: Optional[str] = Field(None, alias="config_hash")
    scorePurpose: ScorePurposeV13 = Field(..., alias="score_purpose")
    sourceChannel: Optional[str] = Field(None, alias="source_channel")
    subIssueCode: Optional[str] = Field(None, alias="sub_issue_code")
    extractedFacts: Optional[ExtractedFactsV13] = Field(None, alias="extracted_facts")
    factorTrace: List[FactorTraceV13] = Field(default_factory=list, alias="factor_trace")
    axisScores: List[AxisScoreTraceV13] = Field(default_factory=list, alias="axis_scores")
    screeningTrace: List[ScreeningTraceV13] = Field(default_factory=list, alias="screening_trace")
    aggregationTrace: Optional[AggregationTraceV13] = Field(None, alias="aggregation_trace")
    legacyCompatibility: LegacyCompatibilityV13 = Field(
        default_factory=LegacyCompatibilityV13, alias="legacy_compatibility"
    )
    evaluatedAt: Optional[str] = Field(None, alias="evaluated_at")
    eventResolutionTrace: Optional[MediaNewsEventResolutionTraceV13] = Field(
        None, alias="event_resolution_trace"
    )
