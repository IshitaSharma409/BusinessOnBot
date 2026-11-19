"""
Response Rewriter Module for BusinessOnBot.
Generates safe, policy-compliant, and grounded customer responses when the initial AI draft
is REWRITTEN, BLOCKED, or ESCALATED.
"""
from typing import List, Dict, Any, Optional
import uuid
from backend.models import (
    CustomerIntent,
    GuardrailDecision,
    ClaimValidation,
    EvidenceMatch
)


class ResponseRewriter:
    """Produces brand-approved, truthful responses removing unsupported commitments."""

    @classmethod
    def generate_safe_response(
        cls,
        intent: CustomerIntent,
        decision: GuardrailDecision,
        validations: List[ClaimValidation],
        evidence_list: List[EvidenceMatch],
        context: Dict[str, Any]
    ) -> str:
        """Constructs a grounded, safe alternative response."""

        # 1. ESCALATION RESPONSES
        if decision == GuardrailDecision.ESCALATE:
            ticket_id = context.get("escalation_ticket_id") or f"ESC-{uuid.uuid4().hex[:6].upper()}"
            if intent == CustomerIntent.refund_status:
                has_rec = any(e.source == "refunds.json" for e in evidence_list)
                if not has_rec:
                    return (
                        f"We couldn't locate a return or refund record for this order in our system. "
                        f"We have created priority support ticket #{ticket_id}. "
                        f"Our customer operations team will verify your courier receipt and update you shortly."
                    )
                else:
                    return (
                        f"We noticed a record discrepancy regarding your refund in our billing system. "
                        f"To protect your transaction, this has been escalated to our senior accounts team under ticket #{ticket_id}. "
                        f"A representative will contact you with verified details."
                    )
            elif intent == CustomerIntent.return_policy:
                return (
                    f"Your order has a specific clearance or policy exception flag that requires manual authorization. "
                    f"We have forwarded your request to our Brand Operations Manager (Ticket #{ticket_id}) for review."
                )
            return (
                f"We are connecting you with a human support specialist to ensure this is resolved accurately (Ticket #{ticket_id}). "
                f"Our team will follow up with you shortly."
            )

        # 2. BLOCK RESPONSES
        if decision == GuardrailDecision.BLOCK:
            return (
                "We cannot safely complete this automated response because the required business authorization "
                "or verified documentation is unavailable. Our human support team has been notified to assist you."
            )

        # 3. REWRITE RESPONSES - Tailored by Intent and Ground Truth Evidence
        if intent == CustomerIntent.refund_status:
            return cls._rewrite_refund_response(evidence_list)

        elif intent == CustomerIntent.medical_safety:
            return cls._rewrite_safety_response(evidence_list)

        elif intent == CustomerIntent.discount_request:
            return cls._rewrite_discount_response(validations, evidence_list)

        elif intent == CustomerIntent.return_policy:
            return cls._rewrite_return_response(evidence_list)

        elif intent == CustomerIntent.product_availability:
            return cls._rewrite_inventory_response(validations, evidence_list, context)

        # Fallback safe rewrite
        return (
            "We have received your query. Based on our latest records, we are verifying the details "
            "and will provide confirmed information shortly."
        )

    # Specific Rewrite Helpers
    @staticmethod
    def _rewrite_refund_response(evidence_list: List[EvidenceMatch]) -> str:
        refund_evidence = next((e for e in evidence_list if e.source == "refunds.json"), None)
        if not refund_evidence:
            return "Your return is recorded, but your refund has not yet been confirmed as processed. Our support team can help you check the latest status."

        data = refund_evidence.data
        status = data.get("refund_status")
        expected_date = data.get("expected_completion_date")

        # Scenario A: Refund status is pending
        if status == "pending":
            return (
                "Your return is recorded, but your refund has not yet been confirmed as processed. "
                "Our support team can help you check the latest status."
            )

        # Scenario B: Refund is processed, but no official arrival date exists
        if status == "processed" and not expected_date:
            return (
                "Your refund has been processed. However, we don't have a confirmed arrival date yet."
            )

        # Scenario C: Processed with official date
        if status == "processed" and expected_date:
            return f"Your refund has been processed. According to our payment partner, the estimated completion date is {expected_date}."

        return "Your return is recorded, but your refund has not yet been confirmed as processed. Our support team can help you check the latest status."

    @staticmethod
    def _rewrite_safety_response(evidence_list: List[EvidenceMatch]) -> str:
        safety_evidence = next((e for e in evidence_list if e.source == "safety_information.json"), None)
        if safety_evidence:
            data = safety_evidence.data
            prod_name = data.get("product_name", "this product")
            ingredients = ", ".join(data.get("active_ingredients", []))
            guidance = data.get("mandatory_medical_guidance", "")
            return (
                f"{prod_name} is formulated with {ingredients}. "
                f"However, we strictly avoid making definitive medical or pregnancy safety guarantees. {guidance}"
            )
        return (
            "We provide factual ingredient information for all our products, but we do not make medical "
            "or safety guarantees during pregnancy. Please consult with your obstetrician or dermatologist before using any active skincare formulations."
        )

    @staticmethod
    def _rewrite_discount_response(validations: List[ClaimValidation], evidence_list: List[EvidenceMatch]) -> str:
        # Check if an expired code was detected
        expired_val = next((v for v in validations if "expired" in v.reason.lower()), None)
        
        active_coupons = [e.data for e in evidence_list if e.source == "discounts.json" and e.data.get("is_active") is True]
        active_list_str = ""
        if active_coupons:
            offers = [f"**{c.get('code')}** ({c.get('discount_value')}% off on orders above ₹{c.get('min_order_value')})" for c in active_coupons]
            active_list_str = " Here are our current authorized promotions: " + ", ".join(offers) + "."

        if expired_val and expired_val.claim.claimed_value:
            code = expired_val.claim.claimed_value
            return (
                f"The promotional code {code} has expired.{active_list_str} "
                f"Please feel free to apply an active code at checkout!"
            )

        return (
            f"The discount code you requested is not an authorized promotional code.{active_list_str} "
            f"Please feel free to apply an active code at checkout!"
        )

    @staticmethod
    def _rewrite_return_response(evidence_list: List[EvidenceMatch]) -> str:
        order_evidence = next((e for e in evidence_list if "delivered_orders" in e.source), None)
        if order_evidence:
            data = order_evidence.data
            days = data.get("days_since_delivery", 0)
            if data.get("is_clearance_sale"):
                return (
                    f"Order {data.get('order_id')} was purchased during our Clearance Final Sale. "
                    f"Under our brand policy, clearance items are non-returnable and non-exchangeable."
                )
            if days > 15:
                return (
                    f"Our standard brand return policy allows returns within 15 days of delivery. "
                    f"Since this item was delivered {days} days ago, it is outside the standard return window. "
                    f"Any exception requires approval from our Brand Operations Manager. "
                    f"Would you like us to submit an exception request on your behalf?"
                )

        return (
            "Our brand policy allows returns within 15 days of delivery for unused items with original tags intact. "
            "Items beyond 15 days or marked as final clearance require special management review."
        )

    @staticmethod
    def _rewrite_inventory_response(validations: List[ClaimValidation], evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> str:
        # Check if validation specifically failed due to ambiguous variant
        ambiguous_val = next((v for v in validations if "ambiguous" in v.reason.lower()), None)
        if ambiguous_val:
            return (
                "This product comes in multiple sizes (e.g. M, L). "
                "Please specify your preferred size and color so we can verify exact real-time availability in our warehouse."
            )

        stale_evidence = next((e for e in evidence_list if not e.is_fresh), None)
        if stale_evidence:
            return (
                "Our warehouse synchronization is currently updating for this item. "
                "Because the latest inventory count cannot be confirmed in real time, "
                "we cannot guarantee stock availability right now. Would you like us to notify you once confirmed?"
            )

        prod_evidence = next((e for e in evidence_list if e.source == "products.json"), None)
        if prod_evidence:
            data = prod_evidence.data
            if not data.get("in_stock"):
                return (
                    f"{data.get('product_name')} ({data.get('color')}, Size {data.get('size')}) is currently out of stock. "
                    f"Would you like to join the waitlist or check availability in another size or color?"
                )

        return (
            "This product comes in multiple sizes and colors. "
            "Please specify your preferred size and color so we can verify exact real-time availability in our warehouse."
        )
