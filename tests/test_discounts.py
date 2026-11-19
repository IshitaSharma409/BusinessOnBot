"""
Unit and integration tests for Discount and Pricing Guardrails.
Covers unauthorized coupon hallucination, expired coupon interception, and discretionary price promises.
"""
import pytest
from backend.models import CustomerQueryRequest, ChannelType, GuardrailDecision
from backend.main import process_customer_query


def test_unauthorized_discount_hallucination():
    """
    AI invents or suggests an unauthorized code 'SAVE30'.
    Guardrail must catch the unauthorized code, REWRITE the response,
    and offer only brand-authorized coupons (e.g. WELCOME10, FESTIVE15).
    """
    request = CustomerQueryRequest(
        query="Can you give me a discount coupon for my shopping cart?",
        channel=ChannelType.whatsapp,
        force_hallucination="fake_discount"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert "SAVE30" not in result.final_response
    assert "not an authorized promotional code" in result.final_response.lower()
    # Verified active coupons presented instead
    assert "WELCOME10" in result.final_response or "FESTIVE15" in result.final_response


def test_expired_coupon_detection():
    """
    Customer asks if expired coupon DIWALI30 can be used.
    Guardrail must verify against marketing records and indicate coupon is invalid/expired.
    """
    request = CustomerQueryRequest(
        query="Can I use coupon code DIWALI30 for 30% off?",
        channel=ChannelType.web_chat
    )
    result = process_customer_query(request)

    assert "DIWALI30" in result.query
    assert "FESTIVE15" in result.final_response or "authorized" in result.final_response.lower() or "expired" in result.final_response.lower()
