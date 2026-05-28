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
    profileSource: str = "MVP_CONTEXT_PROFILE_BUILDER"
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
    impactModifier: float = 0.0
    financialModifier: float = 0.0
    rawFinalImpactScore: Optional[float] = None
    finalImpactScoreAfterModifier: Optional[float] = None
    rawFinalFinancialScore: Optional[float] = None
    finalFinancialScoreAfterModifier: Optional[float] = None
    rawFinalScore: Optional[float] = None
    finalScoreAfterModifier: Optional[float] = None
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
    modifierRange: Dict[str, float] = Field(default_factory=lambda: {"min": -0.5, "max": 0.5})
    stageScoreChangedYn: bool = False
    messages: List[str] = Field(default_factory=list)
    rawPayload: Dict[str, Any] = Field(default_factory=dict)
