from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CompanyContextFactDto(BaseModel):
    sourceTable: str
    metricId: Optional[str] = None
    atomicMetricId: Optional[str] = None
    metricName: Optional[str] = None
    atomicName: Optional[str] = None
    valueNumeric: Optional[float] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None


class CompanyContextProfileDto(BaseModel):
    runId: int
    companyId: int
    reportingYear: int
    profileSource: str = "DETERMINISTIC_FALLBACK"
    confidence: Optional[float] = None
    industryProfile: Optional[str] = None
    businessModel: Optional[str] = None
    industryExposure: str = "unknown"
    valueChainExposure: str = "unknown"
    globalCustomerExposure: str = "unknown"
    euRegulationExposure: str = "unknown"
    transitionExposure: str = "unknown"
    supplyChainDependency: str = "unknown"
    productSafetyExposure: str = "unknown"
    businessScaleExposure: str = "unknown"
    evidenceMetricIds: List[str] = Field(default_factory=list)
    evidenceAtomicMetricIds: List[str] = Field(default_factory=list)
    evidenceText: List[str] = Field(default_factory=list)
    profileSummary: Optional[str] = None
    facts: List[CompanyContextFactDto] = Field(default_factory=list)


class ContextRuleHitDto(BaseModel):
    ruleId: str
    subIssueCode: str
    impactModifier: float = 0.0
    financialModifier: float = 0.0
    reason: str


class SubIssueContextModifierDto(BaseModel):
    subIssueCode: str
    profileSource: Optional[str] = None
    profileConfidence: Optional[float] = None
    impactModifier: float = 0.0
    financialModifier: float = 0.0
    contextModifier: Optional[float] = None
    rawFinalImpactScore: Optional[float] = None
    finalImpactScoreAfterModifier: Optional[float] = None
    rawFinalFinancialScore: Optional[float] = None
    finalFinancialScoreAfterModifier: Optional[float] = None
    rawFinalScore: Optional[float] = None
    finalScoreAfterModifier: Optional[float] = None
    adjustedFinalScore: Optional[float] = None
    rawRank: Optional[int] = None
    adjustedRank: Optional[int] = None
    rankChangedYn: bool = False
    rankDelta: Optional[int] = None
    guardAppliedYn: bool = False
    guardReason: Optional[str] = None
    appliedRules: List[ContextRuleHitDto] = Field(default_factory=list)


class CompanyContextModifierResponseDto(BaseModel):
    runId: int
    contextProfileId: Optional[int] = None
    companyId: Optional[int] = None
    reportingYear: Optional[int] = None
    implementationStatus: str = "READY"
    profile: Optional[CompanyContextProfileDto] = None
    modifiers: List[SubIssueContextModifierDto] = Field(default_factory=list)
    updatedModifierCount: int = 0
    recalculatedFinalCount: int = 0
    modifierRange: Dict[str, float] = Field(default_factory=lambda: {"min": -0.3, "max": 0.3})
    systemModifierRange: Dict[str, float] = Field(default_factory=lambda: {"min": -0.5, "max": 0.5})
    stageScoreChangedYn: bool = False
    messages: List[str] = Field(default_factory=list)
    rawPayload: Dict[str, Any] = Field(default_factory=dict)


class CompanyContextProfileResponseDto(BaseModel):
    runId: int
    contextProfileId: Optional[int] = None
    companyId: Optional[int] = None
    reportingYear: Optional[int] = None
    profile: Optional[CompanyContextProfileDto] = None
    profileSource: Optional[str] = None
    profileConfidence: Optional[float] = None
    modifierRange: Dict[str, float] = Field(default_factory=lambda: {"min": -0.3, "max": 0.3})
    systemModifierRange: Dict[str, float] = Field(default_factory=lambda: {"min": -0.5, "max": 0.5})
    graphTrace: List[Dict[str, Any]] = Field(default_factory=list)
    modifiers: List[SubIssueContextModifierDto] = Field(default_factory=list)
    messages: List[str] = Field(default_factory=list)
    implementationStatus: str = "READY"
