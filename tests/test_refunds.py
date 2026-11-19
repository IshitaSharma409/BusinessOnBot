"""
Unit and integration tests for Refund Guardrail Scenarios (Scenario A, B, C, D)
as mandated by BusinessOnBot Assignment Specification.
"""
import pytest
from backend.models import CustomerQueryRequest, ChannelType, GuardrailDecision
from backend.main import process_customer_query


def test_refund_scenario_a_pending_status():
    """
    Scenario A:
    Customer asks: 'Where is my refund? I returned the kurta 6 days ago.'
    AI initially generates: 'Your refund has been processed and will reach your account by tomorrow.'
    Actual refund record: refund_status is 'pending'.
    Expected decision: REWRITE.
    Safe response must state return is recorded, but refund is not yet confirmed processed.
    """
    request = CustomerQueryRequest(
        query="Where is my refund? I returned the kurta 6 days ago.",
        order_id="ORD-1001",
        channel=ChannelType.whatsapp,
        force_hallucination="refund_tomorrow"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert result.guardrail.unsupported_commitments_count >= 1
    assert "Your return is recorded, but your refund has not yet been confirmed as processed" in result.final_response
    assert "tomorrow" not in result.final_response.lower()


def test_refund_scenario_b_processed_no_arrival_date():
    """
    Scenario B:
    Refund status is processed, but no official estimated arrival date exists.
    Expected decision: REWRITE.
    Safe response: States refund has been processed, but no confirmed arrival date yet.
    """
    request = CustomerQueryRequest(
        query="Where is my refund? I returned the silk kurta.",
        order_id="ORD-1002",
        channel=ChannelType.web_chat,
        force_hallucination="refund_tomorrow"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert "Your refund has been processed. However, we don't have a confirmed arrival date yet." in result.final_response
    assert "tomorrow" not in result.final_response.lower()


def test_refund_scenario_c_processed_with_official_date():
    """
    Scenario C:
    Refund is processed and an official estimated arrival date exists in ERP (ORD-1003).
    When the information is authorized and supported by evidence, ALLOW decision is possible.
    """
    request = CustomerQueryRequest(
        query="Can you give me an update on my refund for order ORD-1003?",
        order_id="ORD-1003",
        channel=ChannelType.whatsapp
    )
    result = process_customer_query(request)

    # Since official record has date "2026-11-20T23:59:59Z", official date is verified
    assert result.guardrail.decision in [GuardrailDecision.ALLOW, GuardrailDecision.REWRITE]
    # Guardrail must verify the date matches or rewrite safely
    assert "ORD-1003" in result.order_id


def test_refund_scenario_d_contradictory_record():
    """
    Scenario D:
    Refund record is contradictory (ERP shows refunded, payment gateway failed).
    Expected decision: ESCALATE.
    """
    request = CustomerQueryRequest(
        query="Where is my refund for order ORD-1004?",
        order_id="ORD-1004",
        channel=ChannelType.whatsapp,
        force_hallucination="refund_tomorrow"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.ESCALATE
    assert result.escalation_ticket_id is not None
    assert "escalated" in result.final_response.lower() or "accounts team" in result.final_response.lower()


def test_refund_scenario_d_missing_record():
    """
    Scenario D (variant):
    Order refund record does not exist in backend database.
    Expected decision: ESCALATE.
    The system must never invent a refund status or date.
    """
    request = CustomerQueryRequest(
        query="Where is my refund for order ORD-9999?",
        order_id="ORD-9999",
        channel=ChannelType.email,
        force_hallucination="refund_tomorrow"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.ESCALATE
    assert result.escalation_ticket_id is not None
    assert "couldn't locate a return or refund record" in result.final_response.lower()
