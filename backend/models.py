"""
Data models and schemas for BusinessOnBot Commitment Guardrail System.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    whatsapp = "whatsapp"
    instagram = "instagram"
    messenger = "messenger"
    email = "email"
    voice = "voice"
    web_chat = "web_chat"


class CustomerIntent(str, Enum):
    refund_status = "refund_status"
    product_availability = "product_availability"
    discount_request = "discount_request"
    medical_safety = "medical_safety"
    return_policy = "return_policy"
    general_product = "general_product"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CommitmentType(str, Enum):
    financial = "financial"
    time = "time"
    inventory = "inventory"
    pricing_discount = "pricing_discount"
    policy_exception = "policy_exception"
    medical_safety = "medical_safety"


class GuardrailDecision(str, Enum):
    ALLOW = "ALLOW"
    REWRITE = "REWRITE"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class DetectedClaim(BaseModel):
    statement: str = Field(..., description="The exact or parsed claim made in the draft")
    commitment_type: CommitmentType = Field(..., description="Type of commitment")
    claimed_value: Optional[str] = Field(None, description="Extracted entity or promise value")
    severity: RiskLevel = Field(default=RiskLevel.medium, description="Risk severity of this commitment")


class CustomerQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Raw customer query text")
    channel: ChannelType = Field(default=ChannelType.whatsapp, description="Incoming communication channel")
    customer_id: Optional[str] = Field(default=None, description="Customer identifier if verified")
    order_id: Optional[str] = Field(default=None, description="Relevant order identifier")
    sku: Optional[str] = Field(default=None, description="Relevant product SKU")
    force_hallucination: Optional[str] = Field(
        default=None, 
        description="Demo/testing flag to force specific AI hallucinations (e.g. 'refund_tomorrow', 'fake_discount', 'safe_pregnancy', 'approve_22d_return')"
    )


class LLMDraftResponse(BaseModel):
    customer_intent: CustomerIntent
    risk_category: RiskLevel
    draft_response: str
    claims_made: List[DetectedClaim] = Field(default_factory=list)
    evidence_required: List[str] = Field(default_factory=list)


class EvidenceMatch(BaseModel):
    source: str
    record_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    is_fresh: bool = True
    freshness_note: Optional[str] = None
    has_conflict: bool = False
    conflict_note: Optional[str] = None


class ClaimValidation(BaseModel):
    claim: DetectedClaim
    is_supported: bool
    reason: str
    evidence_source: Optional[str] = None
    is_fresh: bool = True
    is_authorized: bool = True
    policy_violated: bool = False
    violation_detail: Optional[str] = None


class GuardrailAnalysis(BaseModel):
    intent: CustomerIntent
    risk_level: RiskLevel
    claims_detected: List[DetectedClaim] = Field(default_factory=list)
    evidence_retrieved: List[EvidenceMatch] = Field(default_factory=list)
    validation_results: List[ClaimValidation] = Field(default_factory=list)
    decision: GuardrailDecision
    decision_rationale: str
    unsupported_commitments_count: int = 0


class PipelineResult(BaseModel):
    request_id: str
    query: str
    channel: ChannelType
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    sku: Optional[str] = None
    initial_draft: str
    final_response: str
    guardrail: GuardrailAnalysis
    latency_ms: float
    timestamp: str
    escalation_ticket_id: Optional[str] = None
