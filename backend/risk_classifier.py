"""
Risk Classification Module for BusinessOnBot.
Assigns risk levels (Low, Medium, High, Critical) based on intent and query risk markers.
"""
from backend.models import CustomerIntent, RiskLevel


class RiskClassifier:
    """Evaluates business risk associated with a customer query."""

    INTENT_RISK_MAP = {
        CustomerIntent.medical_safety: RiskLevel.critical,
        CustomerIntent.refund_status: RiskLevel.high,
        CustomerIntent.discount_request: RiskLevel.high,
        CustomerIntent.return_policy: RiskLevel.medium,
        CustomerIntent.product_availability: RiskLevel.medium,
        CustomerIntent.general_product: RiskLevel.low
    }

    @classmethod
    def classify_risk(cls, intent: CustomerIntent, query: str) -> RiskLevel:
        """
        Assigns risk level based on intent and specific risk markers in the query.
        """
        base_risk = cls.INTENT_RISK_MAP.get(intent, RiskLevel.low)
        query_lower = query.lower()

        # Pregnancy or health harm triggers CRITICAL risk immediately
        if any(w in query_lower for w in ["pregnant", "pregnancy", "nursing", "breastfeeding", "allergic reaction", "hospital"]):
            return RiskLevel.critical

        # Large amounts, legal threats, or chargebacks elevate refund to HIGH/CRITICAL
        if intent == CustomerIntent.refund_status:
            if any(w in query_lower for w in ["fraud", "police", "consumer court", "lawyer", "chargeback"]):
                return RiskLevel.critical
            return RiskLevel.high

        # Claims about policy override or manager escalation
        if intent == CustomerIntent.return_policy:
            if "manager" in query_lower or "exception" in query_lower:
                return RiskLevel.high

        return base_risk
