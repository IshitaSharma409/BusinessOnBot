"""
Comprehensive Guardrail and Decision Engine Tests.
Covers return policy window exceptions, clearance conflicts, commitment detector units, and channel adapters.
"""
import pytest
from backend.models import (
    CustomerQueryRequest,
    ChannelType,
    GuardrailDecision,
    CommitmentType
)
from backend.commitment_detector import CommitmentDetector
from backend.channel_adapter import ChannelAdapter
from backend.main import process_customer_query


def test_return_policy_past_15_days():
    """
    Customer asks to return a jacket delivered 22 days ago (ORD-2001).
    AI initially approves return: 'We can accept your return even after 15 days.'
    Guardrail checks return policy: 15-day window has expired.
    Expected decision: REWRITE (uphold 15-day policy, require manager authorization).
    """
    request = CustomerQueryRequest(
        query="Can I return this leather jacket? It was delivered 22 days ago.",
        order_id="ORD-2001",
        channel=ChannelType.email,
        force_hallucination="approve_22d_return"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert "15 days" in result.final_response
    assert "22 days ago" in result.final_response or "outside the standard return window" in result.final_response
    # Email channel adapter format check
    assert "Hello," in result.final_response
    assert "Best regards," in result.final_response


def test_clearance_sale_conflicting_policy():
    """
    Customer attempts return on a clearance sale item (ORD-2003).
    Clearance items are marked FINAL SALE / non-returnable despite being within 4 days.
    Expected decision: ESCALATE (to Brand Manager).
    """
    request = CustomerQueryRequest(
        query="I want to return my clearance silk kurta order ORD-2003.",
        order_id="ORD-2003",
        channel=ChannelType.web_chat,
        force_hallucination="approve_22d_return"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.ESCALATE
    assert result.escalation_ticket_id is not None
    assert "clearance" in result.final_response.lower() or "final" in result.final_response.lower()


def test_commitment_detector_unit():
    """
    Unit test for CommitmentDetector ensuring regex patterns detect various commitment archetypes.
    """
    sample_text = (
        "Your refund has been processed and will reach your account by tomorrow. "
        "The item is in stock right now. Use code SAVE30 to get 20% off. "
        "It is completely safe during pregnancy."
    )
    claims = CommitmentDetector.detect_commitments(sample_text)
    types_detected = {c.commitment_type for c in claims}

    assert CommitmentType.financial in types_detected
    assert CommitmentType.time in types_detected
    assert CommitmentType.inventory in types_detected
    assert CommitmentType.pricing_discount in types_detected
    assert CommitmentType.medical_safety in types_detected


def test_channel_adapter_voice():
    """
    Voice channel adapter strips formatting characters (*, #, _) for clean speech synthesis.
    """
    input_text = "*Hello!* Your order #123 is _confirmed_. Please visit http://example.com."
    formatted = ChannelAdapter.format_response_for_channel(input_text, ChannelType.voice)

    assert "*" not in formatted
    assert "_" not in formatted
    assert "#" not in formatted
