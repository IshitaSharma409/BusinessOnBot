"""
Intent Detection Module for BusinessOnBot.
Identifies customer query intent and extracts relevant business entities (Order ID, SKU, Coupon Codes).
"""
import re
from typing import Tuple, Dict, Any, Optional
from backend.models import CustomerIntent


class IntentDetector:
    """Classifies customer query into one of six core intents and extracts entities."""

    INTENT_PATTERNS = {
        CustomerIntent.refund_status: [
            r"\brefund\b", r"\bmoney back\b", r"\breturned\b", r"\bpayout\b",
            r"\brefund status\b", r"\bwhere is my refund\b", r"\breverse payment\b"
        ],
        CustomerIntent.medical_safety: [
            r"\bpregnan(t|cy)\b", r"\bmedica(l|tion)\b", r"\bsafe(ty)?\b",
            r"\ballerg(y|ic)\b", r"\bside effect\b", r"\brash\b", r"\beczema\b",
            r"\bdermatolog\w*\b", r"\bingredient\b", r"\bnursing\b", r"\bbreastfeed\w*\b",
            r"\bchemical\b", r"\birritation\b"
        ],
        CustomerIntent.discount_request: [
            r"\bdiscount\b", r"\bcoupon\b", r"\bpromo\b", r"\bvoucher\b",
            r"\boffer\b", r"\bcode\b", r"\bdeal\b", r"\bcheaper\b", r"\bpercent(age)? off\b"
        ],
        CustomerIntent.return_policy: [
            r"\breturn\b", r"\breturn policy\b", r"\breturn window\b",
            r"\bcan i return\b", r"\bexchange\b", r"\bdays? to return\b",
            r"\baccept return\b"
        ],
        CustomerIntent.product_availability: [
            r"\bin stock\b", r"\bavailable\b", r"\bstock\b", r"\bquantity\b",
            r"\bout of stock\b", r"\bsold out\b", r"\bcan i buy\b", r"\bsize\b"
        ]
    }

    @classmethod
    def detect_intent_and_entities(cls, query: str, provided_order_id: Optional[str] = None, provided_sku: Optional[str] = None) -> Tuple[CustomerIntent, Dict[str, Any]]:
        """
        Detects primary intent and parses any inline entities like order ID, SKU, coupon codes.
        """
        query_lower = query.lower()
        matched_intent = CustomerIntent.general_product

        # Priority 1: Medical / Safety questions take immediate precedence
        for pattern in cls.INTENT_PATTERNS[CustomerIntent.medical_safety]:
            if re.search(pattern, query_lower):
                matched_intent = CustomerIntent.medical_safety
                break

        # Priority 2: Refund inquiries
        if matched_intent == CustomerIntent.general_product:
            for pattern in cls.INTENT_PATTERNS[CustomerIntent.refund_status]:
                if re.search(pattern, query_lower):
                    matched_intent = CustomerIntent.refund_status
                    break

        # Priority 3: Return policy inquiries (if not already refund)
        if matched_intent == CustomerIntent.general_product:
            for pattern in cls.INTENT_PATTERNS[CustomerIntent.return_policy]:
                if re.search(pattern, query_lower):
                    matched_intent = CustomerIntent.return_policy
                    break

        # Priority 4: Discount requests
        if matched_intent == CustomerIntent.general_product:
            for pattern in cls.INTENT_PATTERNS[CustomerIntent.discount_request]:
                if re.search(pattern, query_lower):
                    matched_intent = CustomerIntent.discount_request
                    break

        # Priority 5: Inventory / product availability
        if matched_intent == CustomerIntent.general_product:
            for pattern in cls.INTENT_PATTERNS[CustomerIntent.product_availability]:
                if re.search(pattern, query_lower):
                    matched_intent = CustomerIntent.product_availability
                    break

        # Extract entities
        entities: Dict[str, Any] = {}
        
        # Order ID pattern (e.g. ORD-1001 or #1001)
        order_match = re.search(r"\b(ORD-\d{4}|\#\d{4})\b", query, re.IGNORECASE)
        if order_match:
            entities["order_id"] = order_match.group(1).upper().replace("#", "ORD-")
        elif provided_order_id:
            entities["order_id"] = provided_order_id

        # SKU or product mentions
        sku_match = re.search(r"\b([A-Z]{3,5}-[A-Z0-9]+-[A-Z0-9]+)\b", query, re.IGNORECASE)
        if sku_match:
            entities["sku"] = sku_match.group(1).upper()
        elif provided_sku:
            entities["sku"] = provided_sku

        # Product name keywords
        if "kurta" in query_lower:
            entities["product_hint"] = "kurta"
        elif "serum" in query_lower or "retinol" in query_lower:
            entities["product_hint"] = "retinol"
            if "sku" not in entities:
                entities["sku"] = "SERUM-RET-30ML"
        elif "jacket" in query_lower or "leather" in query_lower:
            entities["product_hint"] = "jacket"
            if "sku" not in entities:
                entities["sku"] = "JKT-LTHR-BLK-M"
        elif "gown" in query_lower or "silk gown" in query_lower:
            entities["product_hint"] = "gown"
            if "sku" not in entities:
                entities["sku"] = "DRSS-SLK-EMR-S"

        # Coupon code mentions (e.g. SAVE20, WELCOME10, FESTIVE15)
        code_match = re.search(r"\b([A-Z0-9]{4,10})\b", query)
        if code_match and matched_intent == CustomerIntent.discount_request:
            candidate = code_match.group(1)
            if candidate not in ["WHAT", "COULD", "GIVE", "CODE", "NEED", "WITH"]:
                entities["discount_code"] = candidate

        return matched_intent, entities
