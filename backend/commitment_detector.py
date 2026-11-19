"""
Commitment Detection Module for BusinessOnBot.
INDEPENDENT guardrail module that parses AI drafts to detect unsupported promises:
- Financial commitments (refund guarantees, money back)
- Time commitments (arrival dates, "tomorrow", "within 24 hours")
- Inventory commitments ("in stock", "available right now")
- Pricing & discount commitments (unauthorized codes, custom % discounts)
- Policy exceptions (approving returns past window, waiving fees)
- Medical & safety assurances ("completely safe", "100% safe during pregnancy")

Crucial rule: Never accepts the LLM's self-reported claim list as evidence.
"""
import re
from typing import List
from backend.models import DetectedClaim, CommitmentType, RiskLevel


class CommitmentDetector:
    """Independent analyzer that extracts actionable commitments from any text."""

    # 1. Financial Commitment Patterns
    FINANCIAL_PATTERNS = [
        (r"\b(refund|money)\s+(has been|will be|is)\s+(processed|credited|sent|returned|initiated)\b", "Refund processing/credit guarantee"),
        (r"\bwe\s+(will|can|have)\s+refund\b", "Refund promise"),
        (r"\b(amount of|₹|\$)\s*\d+(\.\d{2})?\s+(will be|has been)\s+(refunded|credited)\b", "Explicit refund amount guarantee"),
        (r"\bcompensation\s+(will be|has been)\s+provided\b", "Financial compensation promise")
    ]

    # 2. Time Commitment Patterns
    TIME_PATTERNS = [
        (r"\b(by\s+tomorrow|reach\s+(your\s+account\s+)?(by\s+)?tomorrow|tomorrow|by\s+tonight)\b", "Arrival timeline: tomorrow"),
        (r"\bwithin\s+(\d+|one|two|three|twenty[- ]four|48|72)\s*(hours|hrs|days|business days)\b", "Explicit duration window"),
        (r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "Specific day promise"),
        (r"\bby\s+\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b", "Specific date promise"),
        (r"\bin\s+(\d+|one|two|three)\s+days\b", "Relative day timeline commitment")
    ]

    # 3. Inventory Commitment Patterns
    INVENTORY_PATTERNS = [
        (r"\b(is|are)\s+(currently\s+)?(in stock|available|in our warehouse)\b", "Affirmative stock confirmation"),
        (r"\bwe have\s+\d+\s+(units|pieces|items)?\s*(left|available|in stock)\b", "Specific quantity commitment"),
        (r"\bready to (ship|dispatch) immediately\b", "Immediate fulfillment promise"),
        (r"\byes,?\s+(you can buy it|it is available|we have it in stock)\b", "Affirmative availability assurance")
    ]

    # 4. Pricing & Discount Commitment Patterns
    DISCOUNT_PATTERNS = [
        (r"\b(?:use\s+)?(?:coupon\s+code|discount\s+code|promo\s+code|code|coupon)\s+([A-Za-z0-9]{4,12})\b", "Discount coupon code offer"),
        (r"\b(giving|offering|apply|give you)\s+(\d{1,2}%|\d{1,2}\s*percent)\s*(discount|off)?\b", "Direct percentage discount promise"),
        (r"\b(\d{1,2}%|\d{1,2}\s*percent)\s*(discount|off)\b", "Percentage discount offer"),
        (r"\bspecial\s+discount\s+of\s+(₹|\$)?\d+\b", "Custom monetary discount offer")
    ]

    # 5. Policy Exception Patterns
    POLICY_EXCEPTION_PATTERNS = [
        (r"\b(can|will)\s+accept\s+(your\s+)?return\s+(even after|after)\s+\d+\s*days\b", "Override return window exception"),
        (r"\b(approved|approving)\s+(your\s+)?return\b", "Definitive return approval"),
        (r"\b(making|make)\s+an\s+exception\s+for\s+you\b", "Unauthorized policy exception"),
        (r"\breturn\s+label\s+(has been|will be)\s+(created|generated|sent)\b", "Return label issuance commitment"),
        (r"\bwaiv(e|ing)\s+(the\s+)?(fee|policy|charges)\b", "Fee or policy waiver promise")
    ]

    # 6. Medical & Safety Assurance Patterns
    SAFETY_PATTERNS = [
        (r"\b(completely|100%|totally|absolutely|entirely)\s+safe(\s+during\s+pregnancy|\s+for\s+pregnant\s+women)?\b", "Absolute safety claim"),
        (r"\bsafe\s+(during|throughout)\s+pregnancy\b", "Pregnancy safety assurance"),
        (r"\b(no|zero)\s+side\s+effects\b", "Zero side-effects guarantee"),
        (r"\b(cures|heals)\s+(eczema|acne|dermatitis|psoriasis)\b", "Medical curative claim"),
        (r"\bguaranteed\s+(safe|not to cause)\b", "Guaranteed safety assurance")
    ]

    @classmethod
    def detect_commitments(cls, text: str) -> List[DetectedClaim]:
        """
        Parses the draft response to independently discover all commitments made.
        Case-insensitive regex analysis across all 6 commitment archetypes.
        """
        claims: List[DetectedClaim] = []

        # 1. Financial commitments
        for pattern, desc in cls.FINANCIAL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.financial,
                    claimed_value=match.group(0),
                    severity=RiskLevel.high
                ))
                break

        # 2. Time commitments
        for pattern, desc in cls.TIME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.time,
                    claimed_value=match.group(0),
                    severity=RiskLevel.high
                ))
                break

        # 3. Inventory commitments
        for pattern, desc in cls.INVENTORY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.inventory,
                    claimed_value=match.group(0),
                    severity=RiskLevel.medium
                ))
                break

        # 4. Pricing / Discount commitments
        for pattern, desc in cls.DISCOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract code if present
                code_match = re.search(r"\b([A-Za-z0-9]{4,12})\b", match.group(0))
                code_val = code_match.group(1).upper() if code_match else match.group(0)
                # Filter out common english words
                if code_val not in ["WITH", "YOUR", "CODE", "COUPON", "SAVE", "OFFER", "THAT", "THIS"]:
                    pass
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.pricing_discount,
                    claimed_value=code_val,
                    severity=RiskLevel.high
                ))
                break

        # 5. Policy exceptions
        for pattern, desc in cls.POLICY_EXCEPTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.policy_exception,
                    claimed_value=match.group(0),
                    severity=RiskLevel.medium
                ))
                break

        # 6. Medical / Safety assurances
        for pattern, desc in cls.SAFETY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                claims.append(DetectedClaim(
                    statement=match.group(0),
                    commitment_type=CommitmentType.medical_safety,
                    claimed_value=match.group(0),
                    severity=RiskLevel.critical
                ))
                break

        return claims
