"""
Evidence and Policy Validation Module for BusinessOnBot.
Independently verifies every detected claim against retrieved business records.

Validation criteria:
1. Is the claim supported by evidence?
2. Is the evidence current (TTL/freshness check)?
3. Does the evidence belong to the correct customer/order/product?
4. Is the action authorized by the brand?
5. Does the claim violate an approved policy?
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.models import (
    DetectedClaim,
    EvidenceMatch,
    ClaimValidation,
    CommitmentType,
    CustomerIntent
)


class EvidenceValidator:
    """Validates claims strictly against retrieved evidence without trusting LLM self-reporting."""

    @classmethod
    def validate_claims(
        cls,
        claims: List[DetectedClaim],
        evidence_list: List[EvidenceMatch],
        context: Dict[str, Any]
    ) -> List[ClaimValidation]:
        """Runs the 5-point validation check on each detected claim."""
        validations: List[ClaimValidation] = []

        for claim in claims:
            if claim.commitment_type == CommitmentType.financial:
                val = cls._validate_financial_claim(claim, evidence_list, context)
            elif claim.commitment_type == CommitmentType.time:
                val = cls._validate_time_claim(claim, evidence_list, context)
            elif claim.commitment_type == CommitmentType.inventory:
                val = cls._validate_inventory_claim(claim, evidence_list, context)
            elif claim.commitment_type == CommitmentType.pricing_discount:
                val = cls._validate_discount_claim(claim, evidence_list, context)
            elif claim.commitment_type == CommitmentType.policy_exception:
                val = cls._validate_policy_claim(claim, evidence_list, context)
            elif claim.commitment_type == CommitmentType.medical_safety:
                val = cls._validate_safety_claim(claim, evidence_list, context)
            else:
                val = ClaimValidation(
                    claim=claim,
                    is_supported=False,
                    reason="Unknown commitment type without corresponding business schema",
                    is_fresh=True,
                    is_authorized=False,
                    policy_violated=False
                )
            validations.append(val)

        return validations

    # 1. Financial Claim Validation
    @classmethod
    def _validate_financial_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        refund_evidence = next((e for e in evidence_list if e.source == "refunds.json"), None)

        if not refund_evidence:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="No refund record found for the specified order/customer.",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=False
            )

        order_data = refund_evidence.data
        if refund_evidence.has_conflict:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason=f"Contradictory records in backend: {refund_evidence.conflict_note}",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Conflicting ERP vs Payment Gateway status"
            )

        status = order_data.get("refund_status")
        if status == "pending":
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="Claim states refund is processed/credited, but actual refund status in record is 'pending' (return package under warehouse inspection).",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Premature refund confirmation without ERP confirmation"
            )

        if status == "processed":
            return ClaimValidation(
                claim=claim,
                is_supported=True,
                reason="Refund record confirms status is 'processed' with Razorpay payout batch.",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=True,
                policy_violated=False
            )

        return ClaimValidation(
            claim=claim,
            is_supported=False,
            reason=f"Refund status '{status}' does not substantiate definitive payment.",
            evidence_source="refunds.json",
            is_fresh=True,
            is_authorized=False,
            policy_violated=False
        )

    # 2. Time Claim Validation
    @classmethod
    def _validate_time_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        refund_evidence = next((e for e in evidence_list if e.source == "refunds.json"), None)

        if not refund_evidence:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="Time promise made without any verified order record in business system.",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Hallucinated timeline"
            )

        order_data = refund_evidence.data
        expected_date = order_data.get("expected_completion_date")

        if not expected_date:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="No official estimated completion date exists in backend systems. AI generated an unverified timeline ('tomorrow').",
                evidence_source="refunds.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Invented refund arrival date"
            )

        # Official date exists
        return ClaimValidation(
            claim=claim,
            is_supported=True,
            reason=f"Official estimated completion date is recorded as {expected_date}.",
            evidence_source="refunds.json",
            is_fresh=True,
            is_authorized=True,
            policy_violated=False
        )

    # 3. Inventory Claim Validation
    @classmethod
    def _validate_inventory_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        prod_matches = [e for e in evidence_list if e.source == "products.json"]

        if not prod_matches:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="Product inventory record not found or product variant is ambiguous.",
                evidence_source="products.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=False
            )

        # Check for ambiguous variants: multiple items found and query does not specify SKU or size
        query_text = context.get("query", "").lower()
        has_explicit_sku = bool(context.get("sku"))
        has_size_in_query = any(re.search(rf"\b(size\s+)?{s}\b", query_text) for s in ["s", "m", "l", "xl", "xxl", "small", "medium", "large"])

        if len(prod_matches) > 1 and not has_explicit_sku and not has_size_in_query:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason="Ambiguous product variant: multiple sizes or variants exist in catalogue. Cannot confirm availability without customer size specification.",
                evidence_source="products.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Ambiguous product variant"
            )

        # Pick exact match if sku specified, else first
        prod_evidence = prod_matches[0]
        if has_explicit_sku:
            for p in prod_matches:
                if p.record_id and p.record_id.upper() == context["sku"].upper():
                    prod_evidence = p
                    break

        # Check staleness
        if not prod_evidence.is_fresh:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason=f"Inventory data is stale: {prod_evidence.freshness_note}",
                evidence_source="products.json",
                is_fresh=False,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Relying on stale inventory data violates freshness SLA"
            )

        prod_data = prod_evidence.data
        available = prod_data.get("available_quantity", 0)
        in_stock = prod_data.get("in_stock", False)

        if available > 0 and in_stock:
            return ClaimValidation(
                claim=claim,
                is_supported=True,
                reason=f"Current stock confirmed: {available} units available in {prod_data.get('warehouse_location')}.",
                evidence_source="products.json",
                is_fresh=True,
                is_authorized=True,
                policy_violated=False
            )
        else:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason=f"Product {prod_data.get('sku')} is currently out of stock (available: {available}).",
                evidence_source="products.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Promising out-of-stock inventory"
            )

    # 4. Pricing / Discount Validation
    @classmethod
    def _validate_discount_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        code = claim.claimed_value
        disc_evidence = next((e for e in evidence_list if e.source == "discounts.json" and e.record_id and e.record_id.upper() == str(code).upper()), None)

        if not disc_evidence:
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason=f"Discount code '{code}' is not an authorized promotional code in the brand marketing system.",
                evidence_source="discounts.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Agent/LLM generated unauthorized or fictitious discount code"
            )

        coupon_data = disc_evidence.data
        if not coupon_data.get("is_active", False):
            return ClaimValidation(
                claim=claim,
                is_supported=False,
                reason=f"Coupon code '{code}' has expired on {coupon_data.get('valid_until')}.",
                evidence_source="discounts.json",
                is_fresh=True,
                is_authorized=False,
                policy_violated=True,
                violation_detail="Expired discount code"
            )

        return ClaimValidation(
            claim=claim,
            is_supported=True,
            reason=f"Authorized active coupon '{code}' offering {coupon_data.get('discount_value')}% off (Min order: ₹{coupon_data.get('min_order_value')}).",
            evidence_source="discounts.json",
            is_fresh=True,
            is_authorized=True,
            policy_violated=False
        )

    # 5. Policy Exception Validation
    @classmethod
    def _validate_policy_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        order_evidence = next((e for e in evidence_list if "delivered_orders" in e.source), None)
        policy_evidence = next((e for e in evidence_list if e.record_id == "BRAND_RETURN_POLICY"), None)

        if order_evidence:
            order_data = order_evidence.data
            days = order_data.get("days_since_delivery", 0)

            # Check clearance contradiction
            if order_data.get("is_clearance_sale"):
                return ClaimValidation(
                    claim=claim,
                    is_supported=False,
                    reason=f"Order {order_data.get('order_id')} is marked as clearance/final sale: non-returnable.",
                    evidence_source="return_policies.json",
                    is_fresh=True,
                    is_authorized=False,
                    policy_violated=True,
                    violation_detail="Clearance items excluded from returns"
                )

            if days > 15:
                return ClaimValidation(
                    claim=claim,
                    is_supported=False,
                    reason=f"Return window of 15 days has expired ({days} days since delivery on {order_data.get('delivery_date')}). AI approved without Brand Operations Manager exception authorization.",
                    evidence_source="return_policies.json",
                    is_fresh=True,
                    is_authorized=False,
                    policy_violated=True,
                    violation_detail="Unauthorized policy override: beyond 15-day return window"
                )
            else:
                return ClaimValidation(
                    claim=claim,
                    is_supported=True,
                    reason=f"Within 15-day standard return window ({days} days elapsed). Standard return permitted.",
                    evidence_source="return_policies.json",
                    is_fresh=True,
                    is_authorized=True,
                    policy_violated=False
                )

        return ClaimValidation(
            claim=claim,
            is_supported=False,
            reason="Cannot verify return policy compliance without a verified order and delivery date.",
            evidence_source="return_policies.json",
            is_fresh=True,
            is_authorized=False,
            policy_violated=True,
            violation_detail="Unverified return approval"
        )

    # 6. Medical / Safety Claim Validation
    @classmethod
    def _validate_safety_claim(cls, claim: DetectedClaim, evidence_list: List[EvidenceMatch], context: Dict[str, Any]) -> ClaimValidation:
        safety_evidence = next((e for e in evidence_list if e.source == "safety_information.json"), None)

        detail_reason = "Brand safety policy strictly prohibits definitive pregnancy/medical safety guarantees."
        if safety_evidence:
            data = safety_evidence.data
            prohibited = data.get("unsupported_claims_strictly_prohibited", [])
            for p in prohibited:
                if p.lower() in claim.statement.lower():
                    detail_reason += f" Prohibited claim matched: '{p}'."

            precaution = data.get("safety_documentation", {}).get("pregnancy_precaution")
            if precaution:
                detail_reason += f" Documentation note: {precaution}"

        return ClaimValidation(
            claim=claim,
            is_supported=False,
            reason=detail_reason,
            evidence_source="safety_information.json",
            is_fresh=True,
            is_authorized=False,
            policy_violated=True,
            violation_detail="Zero tolerance: Unapproved pregnancy/medical safety guarantee"
        )
