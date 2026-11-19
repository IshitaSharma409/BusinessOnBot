"""
Knowledge Base Module for BusinessOnBot.
Loads, indexes, and queries mock business databases (refunds, products, discounts, return policies, safety data)
with freshness checks, conflict detection, and entity isolation.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.models import EvidenceMatch, CustomerIntent


class KnowledgeBase:
    """Manages business data lookup and checks for staleness or contradictory records."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to ../data relative to this file
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        self.refunds_data: List[Dict[str, Any]] = []
        self.products_data: List[Dict[str, Any]] = []
        self.discounts_data: Dict[str, Any] = {}
        self.return_policies_data: Dict[str, Any] = {}
        self.safety_data: Dict[str, Any] = {}

        self.load_all_data()

    def load_all_data(self):
        """Loads all mock JSON business datasets into memory."""
        refunds_path = self.data_dir / "refunds.json"
        if refunds_path.exists():
            with open(refunds_path, "r", encoding="utf-8") as f:
                self.refunds_data = json.load(f).get("orders", [])

        products_path = self.data_dir / "products.json"
        if products_path.exists():
            with open(products_path, "r", encoding="utf-8") as f:
                self.products_data = json.load(f).get("products", [])

        discounts_path = self.data_dir / "discounts.json"
        if discounts_path.exists():
            with open(discounts_path, "r", encoding="utf-8") as f:
                self.discounts_data = json.load(f).get("discount_policies", {})

        returns_path = self.data_dir / "return_policies.json"
        if returns_path.exists():
            with open(returns_path, "r", encoding="utf-8") as f:
                self.return_policies_data = json.load(f)

        safety_path = self.data_dir / "safety_information.json"
        if safety_path.exists():
            with open(safety_path, "r", encoding="utf-8") as f:
                self.safety_data = json.load(f)

    # 1. Refund Retrieval
    def get_refund_record(self, order_id: Optional[str] = None, customer_id: Optional[str] = None) -> Optional[EvidenceMatch]:
        """Finds refund record by order_id or customer_id."""
        if not order_id and not customer_id:
            return None

        for order in self.refunds_data:
            if (order_id and order.get("order_id", "").upper() == order_id.upper()) or \
               (customer_id and order.get("customer_id", "").upper() == customer_id.upper()):
                
                # Check for contradictory records
                has_conflict = order.get("refund_status") == "conflicting"
                conflict_note = order.get("notes") if has_conflict else None

                return EvidenceMatch(
                    source="refunds.json",
                    record_id=order.get("order_id"),
                    data=order,
                    is_fresh=True,
                    has_conflict=has_conflict,
                    conflict_note=conflict_note
                )
        return None

    # 2. Product & Inventory Retrieval
    def get_product_by_sku(self, sku: str) -> Optional[EvidenceMatch]:
        """Finds product by exact SKU and validates data freshness."""
        sku_clean = sku.strip().upper()
        for prod in self.products_data:
            if prod.get("sku", "").upper() == sku_clean:
                is_stale = prod.get("is_stale_data", False)
                stale_note = prod.get("stale_reason") if is_stale else None

                return EvidenceMatch(
                    source="products.json",
                    record_id=prod.get("sku"),
                    data=prod,
                    is_fresh=not is_stale,
                    freshness_note=stale_note
                )
        return None

    def search_products(self, query: str) -> List[EvidenceMatch]:
        """Searches products by keyword in name, category, or color."""
        query_lower = query.lower()
        matches = []
        for prod in self.products_data:
            name = prod.get("product_name", "").lower()
            color = prod.get("color", "").lower()
            category = prod.get("category", "").lower()

            if any(term in name or term in color or term in category for term in query_lower.split()):
                is_stale = prod.get("is_stale_data", False)
                matches.append(EvidenceMatch(
                    source="products.json",
                    record_id=prod.get("sku"),
                    data=prod,
                    is_fresh=not is_stale,
                    freshness_note=prod.get("stale_reason") if is_stale else None
                ))
        return matches

    # 3. Discount Retrieval
    def get_discount_code_info(self, code: str) -> Optional[EvidenceMatch]:
        """Validates coupon code against authorized coupons."""
        code_clean = code.strip().upper()
        coupons = self.discounts_data.get("authorized_coupons", [])
        for coupon in coupons:
            if coupon.get("code", "").upper() == code_clean:
                return EvidenceMatch(
                    source="discounts.json",
                    record_id=coupon.get("code"),
                    data=coupon,
                    is_fresh=True
                )
        return None

    def get_active_promotions(self) -> List[EvidenceMatch]:
        """Returns all currently active discount codes."""
        coupons = self.discounts_data.get("authorized_coupons", [])
        active = [c for c in coupons if c.get("is_active") is True]
        return [
            EvidenceMatch(
                source="discounts.json",
                record_id=c.get("code"),
                data=c,
                is_fresh=True
            )
            for c in active
        ]

    # 4. Return Policy & Delivered Order Retrieval
    def get_return_policy(self) -> EvidenceMatch:
        """Returns the brand's master return policy."""
        return EvidenceMatch(
            source="return_policies.json",
            record_id="BRAND_RETURN_POLICY",
            data=self.return_policies_data.get("return_policy", {}),
            is_fresh=True
        )

    def get_delivered_order(self, order_id: str) -> Optional[EvidenceMatch]:
        """Finds delivered order record to check delivery date and return eligibility."""
        order_id_clean = order_id.strip().upper()
        orders = self.return_policies_data.get("delivered_orders", [])
        for o in orders:
            if o.get("order_id", "").upper() == order_id_clean:
                has_conflict = bool(o.get("conflict_note"))
                return EvidenceMatch(
                    source="return_policies.json (delivered_orders)",
                    record_id=o.get("order_id"),
                    data=o,
                    is_fresh=True,
                    has_conflict=has_conflict,
                    conflict_note=o.get("conflict_note")
                )
        return None

    # 5. Product Safety Information Retrieval
    def get_safety_information(self, sku_or_hint: Optional[str] = None) -> Optional[EvidenceMatch]:
        """Retrieves safety documentation and prohibited claims for skincare/cosmetics."""
        products = self.safety_data.get("products_safety", [])
        if sku_or_hint:
            sku_clean = sku_or_hint.upper()
            for prod in products:
                if prod.get("sku", "").upper() == sku_clean or sku_clean in prod.get("product_name", "").upper():
                    return EvidenceMatch(
                        source="safety_information.json",
                        record_id=prod.get("sku"),
                        data=prod,
                        is_fresh=True
                    )

        # If not specific, return first matching skincare or brand policy
        if products:
            return EvidenceMatch(
                source="safety_information.json",
                record_id=products[0].get("sku"),
                data=products[0],
                is_fresh=True
            )
        return None

    # Contextual retrieval based on intent & extracted entities
    def retrieve_evidence_for_query(
        self,
        intent: CustomerIntent,
        entities: Dict[str, Any],
        customer_id: Optional[str] = None,
        order_id: Optional[str] = None,
        sku: Optional[str] = None
    ) -> List[EvidenceMatch]:
        """Gathers all relevant verified business evidence for the given intent and context."""
        matches: List[EvidenceMatch] = []

        eff_order_id = entities.get("order_id") or order_id
        eff_sku = entities.get("sku") or sku

        if intent == CustomerIntent.refund_status:
            rec = self.get_refund_record(order_id=eff_order_id, customer_id=customer_id)
            if rec:
                matches.append(rec)

        elif intent == CustomerIntent.product_availability:
            if eff_sku:
                prod = self.get_product_by_sku(eff_sku)
                if prod:
                    matches.append(prod)
            else:
                hint = entities.get("product_hint", "")
                if hint:
                    search_results = self.search_products(hint)
                    matches.extend(search_results)

        elif intent == CustomerIntent.discount_request:
            code = entities.get("discount_code")
            if code:
                disc = self.get_discount_code_info(code)
                if disc:
                    matches.append(disc)
            matches.extend(self.get_active_promotions())

        elif intent == CustomerIntent.return_policy:
            matches.append(self.get_return_policy())
            if eff_order_id:
                order_rec = self.get_delivered_order(eff_order_id)
                if order_rec:
                    matches.append(order_rec)

        elif intent == CustomerIntent.medical_safety:
            safety_rec = self.get_safety_information(sku_or_hint=eff_sku or entities.get("product_hint"))
            if safety_rec:
                matches.append(safety_rec)

        elif intent == CustomerIntent.general_product:
            if eff_sku:
                prod = self.get_product_by_sku(eff_sku)
                if prod:
                    matches.append(prod)

        return matches
