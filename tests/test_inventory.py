"""
Unit and integration tests for Product Inventory and Catalogue Guardrails.
Covers in-stock, out-of-stock, stale data TTL failures, and ambiguous product variants.
"""
import pytest
from backend.models import CustomerQueryRequest, ChannelType, GuardrailDecision
from backend.main import process_customer_query


def test_inventory_out_of_stock_interception():
    """
    AI claims product is in stock, but real inventory is 0 (KURTA-BLU-L).
    Guardrail must intercept and REWRITE with out-of-stock notification.
    """
    request = CustomerQueryRequest(
        query="Is the blue kurta in size L available in stock?",
        sku="KURTA-BLU-L",
        channel=ChannelType.whatsapp,
        force_hallucination="in_stock_guarantee"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert "out of stock" in result.final_response.lower()
    assert result.guardrail.unsupported_commitments_count >= 1


def test_inventory_stale_data_mitigation():
    """
    Product DRSS-SLK-EMR-S has stale inventory sync (TTL expired > 8 days).
    Guardrail must recognize stale data and prevent unverified stock promises.
    """
    request = CustomerQueryRequest(
        query="Is the Emerald Evening Silk Gown in stock right now?",
        sku="DRSS-SLK-EMR-S",
        channel=ChannelType.web_chat,
        force_hallucination="in_stock_guarantee"
    )
    result = process_customer_query(request)

    assert result.guardrail.decision == GuardrailDecision.REWRITE
    assert "updating" in result.final_response.lower() or "cannot guarantee" in result.final_response.lower()


def test_inventory_ambiguous_variant():
    """
    Customer asks generally about 'kurta' without specifying size or SKU.
    System must ask clarifying questions rather than confirming wrong variant.
    """
    request = CustomerQueryRequest(
        query="Is the Cotton Kurta in stock?",
        channel=ChannelType.whatsapp
    )
    result = process_customer_query(request)

    # Should guide customer or ask for variant size/color
    assert "size" in result.final_response.lower() or "color" in result.final_response.lower() or "variant" in result.final_response.lower()
