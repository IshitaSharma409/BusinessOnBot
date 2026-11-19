"""
Decision Engine Module for BusinessOnBot.
Applies rigorous decision logic to classify actions into:
ALLOW / REWRITE / BLOCK / ESCALATE.

Principles:
- A warning or log alone must never allow an unsafe commitment to reach the customer.
- Medical safety guarantees and false financial promises must be neutralized.
- Missing or contradictory records trigger ESCALATE.
"""
from typing import List, Tuple
from backend.models import (
    CustomerIntent,
    RiskLevel,
    GuardrailDecision,
    ClaimValidation,
    EvidenceMatch
)


class DecisionEngine:
    """Evaluates validation results and determines appropriate guardrail action."""

    @classmethod
    def determine_decision(
        cls,
        intent: CustomerIntent,
        risk_level: RiskLevel,
        validations: List[ClaimValidation],
        evidence_list: List[EvidenceMatch]
    ) -> Tuple[GuardrailDecision, str]:
        """
        Computes final GuardrailDecision and explanatory rationale.
        """
        # 1. Check for missing or contradictory records -> ESCALATE
        # If refund intent but no refund record exists
        if intent == CustomerIntent.refund_status:
            has_refund_rec = any(e.source == "refunds.json" for e in evidence_list)
            if not has_refund_rec:
                return GuardrailDecision.ESCALATE, "Refund record is missing in backend ERP. Human support must investigate."

            conflicting_rec = next((e for e in evidence_list if e.has_conflict), None)
            if conflicting_rec:
                return GuardrailDecision.ESCALATE, f"Contradictory records detected ({conflicting_rec.conflict_note}). Manual escalation required."

        # If return policy with policy conflict (e.g. clearance conflict)
        if intent == CustomerIntent.return_policy:
            conflicting_return = next((e for e in evidence_list if e.has_conflict), None)
            if conflicting_return:
                return GuardrailDecision.ESCALATE, f"Order-specific policy conflict: {conflicting_return.conflict_note}. Escalating to Brand Manager."

        # If stale inventory data on high-intent item -> ESCALATE or REWRITE
        stale_evidence = next((e for e in evidence_list if not e.is_fresh), None)
        if stale_evidence:
            return GuardrailDecision.REWRITE, f"Inventory data is stale ({stale_evidence.freshness_note}). Cannot confirm availability definitively."

        # If no commitments were detected in the draft
        if not validations:
            # Low risk queries without commitments are safe
            if risk_level == RiskLevel.low:
                return GuardrailDecision.ALLOW, "No commitments detected in response. Information complies with brand policies."
            elif intent == CustomerIntent.medical_safety:
                # Medical queries must always have approved guidance
                return GuardrailDecision.REWRITE, "Medical/safety query requires standard factual ingredient disclosures and physician consultation guidance."
            return GuardrailDecision.ALLOW, "Draft contains factual information without unsupported commitments."

        # Analyze validation outcomes
        unsupported = [v for v in validations if not v.is_supported]
        policy_violations = [v for v in validations if v.policy_violated]
        stale_validations = [v for v in validations if not v.is_fresh]

        # Case: All claims are supported by verified current evidence
        if not unsupported and not policy_violations and not stale_validations:
            return GuardrailDecision.ALLOW, "All factual claims and commitments are verified by current, authorized business records."

        # Critical / Unsafe medical claims
        has_critical_safety_claim = any(
            v.claim.commitment_type.value == "medical_safety" for v in unsupported
        )
        if has_critical_safety_claim:
            # We REWRITE to remove the safety guarantee and enforce mandatory physician guidance
            return GuardrailDecision.REWRITE, "Unsupported medical/pregnancy safety assurance detected. Rewriting to strip guarantee and provide verified ingredient facts with physician disclaimer."

        # Time or financial hallucination in refunds (Scenario A, Scenario B)
        has_unsupported_time = any(v.claim.commitment_type.value == "time" for v in unsupported)
        has_unsupported_financial = any(v.claim.commitment_type.value == "financial" for v in unsupported)

        if has_unsupported_time or has_unsupported_financial:
            return GuardrailDecision.REWRITE, "Draft contains unsupported financial or time promises. Rewriting to verified record status without false arrival guarantees."

        # Unauthorized discount
        has_unauthorized_discount = any(v.claim.commitment_type.value == "pricing_discount" for v in unsupported)
        if has_unauthorized_discount:
            return GuardrailDecision.REWRITE, "Draft offered unauthorized or expired discount. Rewriting to provide only brand-authorized promotional codes."

        # Return policy exception (e.g. 22 days)
        has_policy_exception = any(v.claim.commitment_type.value == "policy_exception" for v in unsupported)
        if has_policy_exception:
            return GuardrailDecision.REWRITE, "Draft approved a return beyond the standard 15-day window. Rewriting to uphold brand return policy and outline official escalation steps."

        # Inventory out of stock
        has_inventory_claim = any(v.claim.commitment_type.value == "inventory" for v in unsupported)
        if has_inventory_claim:
            return GuardrailDecision.REWRITE, "Draft claimed product is available, but inventory records show it is out of stock. Rewriting to notify customer and offer alternatives."

        # Default fallback if severe violations cannot be salvaged
        return GuardrailDecision.BLOCK, f"Draft contains {len(unsupported)} unsupported commitments and violates brand policies. System cannot safely deliver this response."
