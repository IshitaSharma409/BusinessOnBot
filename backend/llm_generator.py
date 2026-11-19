"""
LLM Response Generator Module for BusinessOnBot.
Generates initial customer support drafts as structured Pydantic models.
Operates seamlessly in Mock LLM mode (default when no API key is provided)
or connects to live LLM providers (OpenAI / Gemini) when configured via environment variables.
"""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from backend.models import (
    CustomerIntent,
    RiskLevel,
    LLMDraftResponse,
    DetectedClaim,
    CommitmentType
)

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Generates initial draft responses using either a real LLM API or deterministic Mock mode."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "mock"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.provider = "api" if self.api_key else "mock"
        logger.info(f"Initialized LLMGenerator in {self.provider.upper()} mode.")

    def generate_draft(
        self,
        query: str,
        intent: CustomerIntent,
        risk_level: RiskLevel,
        retrieved_facts: List[Dict[str, Any]],
        force_hallucination: Optional[str] = None
    ) -> LLMDraftResponse:
        """
        Produces initial draft response with claimed commitments.
        If live API is unavailable or mock mode is active, uses high-fidelity simulation.
        """
        if self.provider == "api" and not force_hallucination:
            try:
                return self._call_live_llm(query, intent, risk_level, retrieved_facts)
            except Exception as e:
                logger.warning(f"Live LLM call failed ({str(e)}). Falling back to mock generator.")
                return self._generate_mock_draft(query, intent, risk_level, retrieved_facts, force_hallucination)
        else:
            return self._generate_mock_draft(query, intent, risk_level, retrieved_facts, force_hallucination)

    def _generate_mock_draft(
        self,
        query: str,
        intent: CustomerIntent,
        risk_level: RiskLevel,
        retrieved_facts: List[Dict[str, Any]],
        force_hallucination: Optional[str] = None
    ) -> LLMDraftResponse:
        """
        High-fidelity simulation of standard LLM tendencies (including overconfident promises)
        to demonstrate the guardrail system in action.
        """
        q_lower = query.lower()

        # 1. Refund Scenario (Default assignment scenario: "Where is my refund? I returned the kurta 6 days ago.")
        if intent == CustomerIntent.refund_status or force_hallucination == "refund_tomorrow":
            draft_text = "Your refund has been processed and will reach your account by tomorrow."
            claims = [
                DetectedClaim(
                    statement="Your refund has been processed",
                    commitment_type=CommitmentType.financial,
                    claimed_value="processed",
                    severity=RiskLevel.high
                ),
                DetectedClaim(
                    statement="will reach your account by tomorrow",
                    commitment_type=CommitmentType.time,
                    claimed_value="tomorrow",
                    severity=RiskLevel.high
                )
            ]
            return LLMDraftResponse(
                customer_intent=CustomerIntent.refund_status,
                risk_category=RiskLevel.high,
                draft_response=draft_text,
                claims_made=claims,
                evidence_required=["Order return record", "Payment gateway refund status", "Estimated bank credit date"]
            )

        # 2. Inventory Scenario
        elif intent == CustomerIntent.product_availability or force_hallucination == "in_stock_guarantee":
            draft_text = "Yes, absolutely! The item is in stock in our warehouse and ready to dispatch immediately."
            claims = [
                DetectedClaim(
                    statement="The item is in stock in our warehouse",
                    commitment_type=CommitmentType.inventory,
                    claimed_value="in stock",
                    severity=RiskLevel.medium
                )
            ]
            return LLMDraftResponse(
                customer_intent=CustomerIntent.product_availability,
                risk_category=RiskLevel.medium,
                draft_response=draft_text,
                claims_made=claims,
                evidence_required=["Warehouse inventory record", "SKU availability count", "Sync freshness"]
            )

        # 3. Discount Scenario
        elif intent == CustomerIntent.discount_request or force_hallucination == "fake_discount":
            # Check if query specifically mentioned a code like DIWALI30
            code_match = re.search(r"\b([A-Z0-9]{5,10})\b", query)
            code = code_match.group(1).upper() if code_match and code_match.group(1).upper() not in ["COULD", "GIVE", "CODE", "NEED", "WITH"] else "SAVE30"

            draft_text = f"Here's a special offer just for you! Use coupon code {code} to get 30% off your purchase."
            claims = [
                DetectedClaim(
                    statement=f"Use coupon code {code} to get 30% off",
                    commitment_type=CommitmentType.pricing_discount,
                    claimed_value=code,
                    severity=RiskLevel.high
                )
            ]
            return LLMDraftResponse(
                customer_intent=CustomerIntent.discount_request,
                risk_category=RiskLevel.high,
                draft_response=draft_text,
                claims_made=claims,
                evidence_required=["Authorized marketing campaign codes", "Coupon validity status"]
            )

        # 4. Medical / Pregnancy Safety Scenario
        elif intent == CustomerIntent.medical_safety or force_hallucination == "safe_pregnancy":
            draft_text = (
                "Yes, our Retinol Night Serum is completely safe during pregnancy! "
                "It is formulated with gentle ingredients and has zero side effects."
            )
            claims = [
                DetectedClaim(
                    statement="completely safe during pregnancy",
                    commitment_type=CommitmentType.medical_safety,
                    claimed_value="completely safe during pregnancy",
                    severity=RiskLevel.critical
                ),
                DetectedClaim(
                    statement="has zero side effects",
                    commitment_type=CommitmentType.medical_safety,
                    claimed_value="zero side effects",
                    severity=RiskLevel.critical
                )
            ]
            return LLMDraftResponse(
                customer_intent=CustomerIntent.medical_safety,
                risk_category=RiskLevel.critical,
                draft_response=draft_text,
                claims_made=claims,
                evidence_required=["Dermatological safety dossier", "Brand medical contraindications", "Regulatory compliance notes"]
            )

        # 5. Return Policy Scenario
        elif intent == CustomerIntent.return_policy or force_hallucination == "approve_22d_return":
            draft_text = (
                "Don't worry at all! Even though it's been 22 days, we can accept your return. "
                "Your return label has been generated and we will process your return smoothly."
            )
            claims = [
                DetectedClaim(
                    statement="we can accept your return even after 15 days",
                    commitment_type=CommitmentType.policy_exception,
                    claimed_value="approve return after 22 days",
                    severity=RiskLevel.medium
                ),
                DetectedClaim(
                    statement="return label has been generated",
                    commitment_type=CommitmentType.policy_exception,
                    claimed_value="return label generated",
                    severity=RiskLevel.medium
                )
            ]
            return LLMDraftResponse(
                customer_intent=CustomerIntent.return_policy,
                risk_category=RiskLevel.medium,
                draft_response=draft_text,
                claims_made=claims,
                evidence_required=["Brand standard return window", "Order delivery timestamp", "Manager override authorization"]
            )

        # 6. General Product / FAQ
        else:
            draft_text = (
                "Thank you for contacting us! We take pride in delivering quality products. "
                "Could you please share your order number or specific item name so I can assist you better?"
            )
            return LLMDraftResponse(
                customer_intent=CustomerIntent.general_product,
                risk_category=RiskLevel.low,
                draft_response=draft_text,
                claims_made=[],
                evidence_required=[]
            )

    def _call_live_llm(
        self,
        query: str,
        intent: CustomerIntent,
        risk_level: RiskLevel,
        retrieved_facts: List[Dict[str, Any]]
    ) -> LLMDraftResponse:
        """Optional OpenAI live integration if OPENAI_API_KEY is configured."""
        import urllib.request

        prompt = f"""
You are an e-commerce customer support assistant.
Customer query: "{query}"
Intent: {intent.value}
Risk: {risk_level.value}
Retrieved facts: {json.dumps(retrieved_facts)}

Respond in valid JSON with:
{{
  "customer_intent": "{intent.value}",
  "risk_category": "{risk_level.value}",
  "draft_response": "<friendly response>",
  "claims_made": [],
  "evidence_required": []
}}
"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return LLMDraftResponse(**parsed)
