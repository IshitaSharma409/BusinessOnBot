"""
Streamlit Web Dashboard for BusinessOnBot
AI Customer Support Agent with Commitment Guardrails
"""
import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime

# Set Streamlit page config
st.set_page_config(
    page_title="BusinessOnBot | Commitment Guardrails",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished enterprise look
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .badge-allow {
        background-color: #DCFCE7;
        color: #166534;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        border: 1px solid #86EFAC;
    }
    .badge-rewrite {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        border: 1px solid #FCD34D;
    }
    .badge-block {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        border: 1px solid #FCA5A5;
    }
    .badge-escalate {
        background-color: #EDE9FE;
        color: #5B21B6;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        border: 1px solid #C4B5FD;
    }
    .badge-critical {
        background-color: #FFE4E6;
        color: #9F1239;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-high {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-medium {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-low {
        background-color: #F1F5F9;
        color: #475569;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .response-box-draft {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 14px;
        border-radius: 4px;
        margin-bottom: 12px;
        font-size: 0.95rem;
    }
    .response-box-final {
        background-color: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 14px;
        border-radius: 4px;
        margin-bottom: 12px;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# Import backend modules directly in-process for speed and reliability
from backend.models import (
    CustomerQueryRequest,
    ChannelType,
    GuardrailDecision,
    RiskLevel
)
from backend.main import process_customer_query, kb, logger_service

# Sidebar Navigation and Configuration
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=64)
st.sidebar.title("BusinessOnBot")
st.sidebar.caption("AI Customer Support with Commitment Guardrails")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Navigation",
    [
        "💬 Live Agent Playground",
        "📊 Guardrail Analytics",
        "📜 Audit & Compliance Logs",
        "🗄️ Business Knowledge Base",
        "📘 Architecture & Specs"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("System Mode")
st.sidebar.success("🟢 Guardrail Engine: ACTIVE")
st.sidebar.info("🤖 LLM Mode: Mock Simulator (API key optional)")


# Helper function to render decision badge
def render_decision_badge(decision: GuardrailDecision) -> str:
    if decision == GuardrailDecision.ALLOW:
        return '<span class="badge-allow">✅ ALLOW</span>'
    elif decision == GuardrailDecision.REWRITE:
        return '<span class="badge-rewrite">⚠️ REWRITE</span>'
    elif decision == GuardrailDecision.BLOCK:
        return '<span class="badge-block">🛑 BLOCK</span>'
    elif decision == GuardrailDecision.ESCALATE:
        return '<span class="badge-escalate">🔄 ESCALATE</span>'
    return str(decision)


# Helper function to render risk badge
def render_risk_badge(risk: RiskLevel) -> str:
    if risk == RiskLevel.critical:
        return '<span class="badge-critical">CRITICAL</span>'
    elif risk == RiskLevel.high:
        return '<span class="badge-high">HIGH</span>'
    elif risk == RiskLevel.medium:
        return '<span class="badge-medium">MEDIUM</span>'
    return '<span class="badge-low">LOW</span>'


# ==============================================================================
# TAB 1: LIVE AGENT PLAYGROUND
# ==============================================================================
if app_mode == "💬 Live Agent Playground":
    st.markdown('<div class="main-header">Customer Support Commitment Guardrails</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Independent verification layer preventing AI from making unsupported promises or false commitments.</div>',
        unsafe_allow_html=True
    )

    # Preset Quick Demo Scenarios
    st.markdown("#### ⚡ 1-Click Evaluation Presets")
    st.caption("Click any preset below to load the assignment test scenarios immediately:")

    preset_col1, preset_col2, preset_col3, preset_col4, preset_col5 = st.columns(5)

    preset_query = ""
    preset_channel = ChannelType.whatsapp
    preset_order_id = ""
    preset_sku = ""
    preset_force = None

    with preset_col1:
        if st.button("1. Refund Pending (Scenario A)", use_container_width=True):
            preset_query = "Where is my refund? I returned the kurta 6 days ago."
            preset_order_id = "ORD-1001"
            preset_channel = ChannelType.whatsapp
            preset_force = "refund_tomorrow"

    with preset_col2:
        if st.button("2. Refund Processed No Date (B)", use_container_width=True):
            preset_query = "Where is my refund? I returned the kurta 6 days ago."
            preset_order_id = "ORD-1002"
            preset_channel = ChannelType.whatsapp
            preset_force = "refund_tomorrow"

    with preset_col3:
        if st.button("3. Inventory Out of Stock", use_container_width=True):
            preset_query = "Is the blue kurta in size L available in stock?"
            preset_sku = "KURTA-BLU-L"
            preset_channel = ChannelType.whatsapp
            preset_force = "in_stock_guarantee"

    with preset_col4:
        if st.button("4. Fake Discount (SAVE30)", use_container_width=True):
            preset_query = "Can you give me a discount coupon for my cart?"
            preset_channel = ChannelType.whatsapp
            preset_force = "fake_discount"

    with preset_col5:
        if st.button("5. Pregnancy Safety", use_container_width=True):
            preset_query = "Is your Retinol Night Serum completely safe to use during pregnancy?"
            preset_sku = "SERUM-RET-30ML"
            preset_channel = ChannelType.whatsapp
            preset_force = "safe_pregnancy"

    preset_extra1, preset_extra2, preset_extra3, preset_extra4 = st.columns(4)
    with preset_extra1:
        if st.button("6. Return Beyond 15 Days (22d)", use_container_width=True):
            preset_query = "Can I return this leather jacket? It was delivered 22 days ago."
            preset_order_id = "ORD-2001"
            preset_channel = ChannelType.email
            preset_force = "approve_22d_return"

    with preset_extra2:
        if st.button("7. Contradictory Refund (D)", use_container_width=True):
            preset_query = "Where is my refund for order ORD-1004?"
            preset_order_id = "ORD-1004"
            preset_channel = ChannelType.whatsapp
            preset_force = "refund_tomorrow"

    with preset_extra3:
        if st.button("8. Missing Refund Record", use_container_width=True):
            preset_query = "Where is my refund for order ORD-9999?"
            preset_order_id = "ORD-9999"
            preset_channel = ChannelType.email
            preset_force = "refund_tomorrow"

    with preset_extra4:
        if st.button("9. Stale Inventory Data", use_container_width=True):
            preset_query = "Is the Emerald Evening Silk Gown in stock right now?"
            preset_sku = "DRSS-SLK-EMR-S"
            preset_channel = ChannelType.web_chat
            preset_force = "in_stock_guarantee"

    st.markdown("---")

    # Main Input Form
    with st.form("query_form"):
        col_q, col_meta = st.columns([2.5, 1.2])

        with col_q:
            query_input = st.text_area(
                "Customer Message",
                value=preset_query if preset_query else "Where is my refund? I returned the kurta 6 days ago.",
                height=90,
                placeholder="Type customer question here..."
            )

        with col_meta:
            channels = [c.value for c in ChannelType]
            default_ch_idx = channels.index(preset_channel.value) if preset_channel else 0
            channel_input = st.selectbox("Channel Adapter", channels, index=default_ch_idx)

            order_id_input = st.text_input("Order ID (optional)", value=preset_order_id)
            sku_input = st.text_input("Product SKU (optional)", value=preset_sku)

        force_h = preset_force

        submit_btn = st.form_submit_button("🛡️ Execute Guardrail Pipeline", type="primary", use_container_width=True)

    if submit_btn or preset_query:
        req = CustomerQueryRequest(
            query=query_input,
            channel=ChannelType(channel_input),
            order_id=order_id_input if order_id_input.strip() else None,
            sku=sku_input if sku_input.strip() else None,
            force_hallucination=force_h
        )

        with st.spinner("Processing through 10-stage Commitment Guardrail pipeline..."):
            result = process_customer_query(req)

        # Top Summary Bar: Decision, Intent, Risk Level, Latency
        st.markdown("### Guardrail Pipeline Execution Result")
        mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
        with mcol1:
            st.markdown(f"**Decision Status:**<br>{render_decision_badge(result.guardrail.decision)}", unsafe_allow_html=True)
        with mcol2:
            st.markdown(f"**Detected Intent:**<br>`{result.guardrail.intent.value}`", unsafe_allow_html=True)
        with mcol3:
            st.markdown(f"**Risk Classification:**<br>{render_risk_badge(result.guardrail.risk_level)}", unsafe_allow_html=True)
        with mcol4:
            st.metric("Latency", f"{result.latency_ms} ms")
        with mcol5:
            if result.escalation_ticket_id:
                st.metric("Escalation Ticket", result.escalation_ticket_id)
            else:
                st.metric("Unsupported Commitments", result.guardrail.unsupported_commitments_count)

        st.markdown("---")

        # Side-by-side Response Comparison
        col_draft, col_final = st.columns(2)

        with col_draft:
            st.markdown("#### 1. Initial AI Draft (Unverified)")
            st.caption("Generated by LLM prior to guardrail validation:")
            st.markdown(
                f'<div class="response-box-draft">{result.initial_draft}</div>',
                unsafe_allow_html=True
            )
            if result.guardrail.claims_detected:
                st.markdown("**Detected Commitments in Draft:**")
                for c in result.guardrail.claims_detected:
                    st.warning(f"• **[{c.commitment_type.value.upper()}]** {c.statement}")
            else:
                st.info("No specific commitments detected in raw draft.")

        with col_final:
            st.markdown(f"#### 2. Guardrail-Vetted Delivery ({channel_input.capitalize()})")
            st.caption("Final safe output delivered to the customer:")
            st.markdown(
                f'<div class="response-box-final">{result.final_response}</div>',
                unsafe_allow_html=True
            )
            st.markdown(f"**Decision Rationale:** {result.guardrail.decision_rationale}")

        st.markdown("---")

        # Deep Guardrail Analysis Section
        with st.expander("🔍 Deep Guardrail Evidence & Policy Verification Details", expanded=True):
            st.markdown("##### 5-Point Claim Validation Ledger")
            if result.guardrail.validation_results:
                val_data = []
                for v in result.guardrail.validation_results:
                    val_data.append({
                        "Claim Statement": v.claim.statement,
                        "Type": v.claim.commitment_type.value,
                        "Supported by Evidence?": "✅ Supported" if v.is_supported else "❌ UNSUPPORTED",
                        "Evidence Source": v.evidence_source,
                        "Fresh Data (TTL)?": "✅ Fresh" if v.is_fresh else "⚠️ STALE",
                        "Policy Violated?": "⚠️ Violation" if v.policy_violated else "✅ Compliant",
                        "Verification Details": v.reason
                    })
                st.table(pd.DataFrame(val_data))
            else:
                st.write("No actionable commitments required validation.")

            st.markdown("##### Retrieved Business Evidence Records")
            if result.guardrail.evidence_retrieved:
                for idx, ev in enumerate(result.guardrail.evidence_retrieved):
                    st.markdown(f"**Source {idx+1}:** `{ev.source}` (Record: `{ev.record_id}`) | Fresh: `{ev.is_fresh}` | Conflict: `{ev.has_conflict}`")
                    st.json(ev.data)
            else:
                st.info("No corresponding records found in business databases.")


# ==============================================================================
# TAB 2: MONITORING & ANALYTICS
# ==============================================================================
elif app_mode == "📊 Guardrail Analytics":
    st.markdown('<div class="main-header">Operational Safety & Guardrail Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Continuous monitoring of unsupported commitment rates, decision distributions, and risk categories.</div>',
        unsafe_allow_html=True
    )

    metrics = logger_service.get_analytics_metrics()

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.metric("Total Queries Audited", metrics["total_queries"])
    with kpi2:
        st.metric("Unsupported Rate", f"{metrics['unsupported_commitment_rate']}%")
    with kpi3:
        st.metric("Rewritten Responses", metrics["rewritten_count"])
    with kpi4:
        st.metric("Escalated / Blocked", metrics["escalated_count"] + metrics["blocked_count"])
    with kpi5:
        st.metric("Avg Guardrail Latency", f"{metrics['avg_latency_ms']} ms")

    st.markdown("---")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Decision Breakdown")
        if metrics["decisions_breakdown"]:
            df_dec = pd.DataFrame(list(metrics["decisions_breakdown"].items()), columns=["Decision", "Count"])
            st.bar_chart(df_dec.set_index("Decision"))
        else:
            st.info("No data yet. Execute test queries from the Playground!")

    with chart_col2:
        st.subheader("Risk Category Distribution")
        if metrics["risk_distribution"]:
            df_risk = pd.DataFrame(list(metrics["risk_distribution"].items()), columns=["Risk Level", "Count"])
            st.bar_chart(df_risk.set_index("Risk Level"))
        else:
            st.info("No data yet.")

    st.markdown("---")
    ch_col1, ch_col2 = st.columns(2)
    with ch_col1:
        st.subheader("Channel Volume")
        if metrics["channel_distribution"]:
            df_chan = pd.DataFrame(list(metrics["channel_distribution"].items()), columns=["Channel", "Count"])
            st.bar_chart(df_chan.set_index("Channel"))
    with ch_col2:
        st.subheader("Intent Breakdown")
        if metrics["intent_distribution"]:
            df_int = pd.DataFrame(list(metrics["intent_distribution"].items()), columns=["Intent", "Count"])
            st.bar_chart(df_int.set_index("Intent"))


# ==============================================================================
# TAB 3: AUDIT & COMPLIANCE LOGS
# ==============================================================================
elif app_mode == "📜 Audit & Compliance Logs":
    st.markdown('<div class="main-header">Audit & Compliance Logs</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Full historical record of customer queries, initial drafts, guardrail decisions, and verified deliveries.</div>',
        unsafe_allow_html=True
    )

    logs = logger_service.get_all_logs(limit=200)

    if not logs:
        st.warning("No audit logs recorded yet. Run a few queries in the Playground to populate logs.")
    else:
        df_logs = pd.DataFrame(logs)

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            decision_filter = st.selectbox("Filter by Decision", ["All"] + list(df_logs["decision"].unique()))
        with fcol2:
            channel_filter = st.selectbox("Filter by Channel", ["All"] + list(df_logs["channel"].unique()))
        with fcol3:
            risk_filter = st.selectbox("Filter by Risk Level", ["All"] + list(df_logs["risk_level"].unique()))

        filtered_df = df_logs.copy()
        if decision_filter != "All":
            filtered_df = filtered_df[filtered_df["decision"] == decision_filter]
        if channel_filter != "All":
            filtered_df = filtered_df[filtered_df["channel"] == channel_filter]
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["risk_level"] == risk_filter]

        st.dataframe(
            filtered_df[["timestamp", "channel", "intent", "risk_level", "decision", "latency_ms", "query"]],
            use_container_width=True
        )

        st.markdown("#### Detailed Interaction Inspector")
        selected_req_id = st.selectbox("Select Request ID to Inspect", filtered_df["request_id"].tolist())

        selected_record = next((l for l in logs if l.get("request_id") == selected_req_id), None)
        if selected_record:
            st.json(selected_record)


# ==============================================================================
# TAB 4: KNOWLEDGE BASE EXPLORER
# ==============================================================================
elif app_mode == "🗄️ Business Knowledge Base":
    st.markdown('<div class="main-header">Business Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Authoritative business datasets used as ground truth for evidence verification.</div>',
        unsafe_allow_html=True
    )

    kb_tabs = st.tabs(["Refund Records", "Product Catalogue", "Discount Policies", "Return Policies", "Safety Information"])

    with kb_tabs[0]:
        st.subheader("Refund Records (`refunds.json`)")
        st.dataframe(pd.DataFrame(kb.refunds_data), use_container_width=True)

    with kb_tabs[1]:
        st.subheader("Product Catalogue & Stock (`products.json`)")
        st.dataframe(pd.DataFrame(kb.products_data), use_container_width=True)

    with kb_tabs[2]:
        st.subheader("Authorized Discount Policies (`discounts.json`)")
        st.json(kb.discounts_data)

    with kb_tabs[3]:
        st.subheader("Return Policies & Order Eligibility (`return_policies.json`)")
        st.json(kb.return_policies_data)

    with kb_tabs[4]:
        st.subheader("Product Safety & Medical Contraindications (`safety_information.json`)")
        st.json(kb.safety_data)


# ==============================================================================
# TAB 5: ARCHITECTURE & SPECS
# ==============================================================================
elif app_mode == "📘 Architecture & Specs":
    st.markdown('<div class="main-header">System Architecture & Design</div>', unsafe_allow_html=True)
    st.markdown(
        """
### The Commitment Guardrail Principle
LLMs cannot be trusted blindly with factual customer commitments. The guardrail layer functions as an independent, deterministic arbiter between LLM generation and customer delivery.

```
Customer Query
      ↓
Channel Adapter (WhatsApp, Instagram, Messenger, Email, Voice, Web)
      ↓
Intent Detection & Risk Classification (Low, Medium, High, Critical)
      ↓
Retrieve Approved Business Evidence (Refunds, Products, Discounts, Policies, Safety)
      ↓
LLM Response Generation (Draft Response)
      ↓
Commitment Detection (Independent Claim Extraction)
      ↓
Evidence & Policy Validation (5-Point Check: Evidence, Freshness, Entity Match, Authority, Policy)
      ↓
Decision Engine (ALLOW / REWRITE / BLOCK / ESCALATE)
      ↓
Response Rewriter & Delivery Gateway
      ↓
Logging, Audit & Metrics (Pandas Analytics)
```

### The 5 Core Handled Archetypes:
1. **Refund**: Prevents unverified promises ("tomorrow") when refund is pending or date is unconfirmed.
2. **Inventory**: Prevents affirmative stock confirmations for out-of-stock, stale, or ambiguous items.
3. **Discount**: Strips hallucinated/unauthorized coupons and replaces them with active marketing codes.
4. **Medical / Safety**: Zero tolerance for absolute pregnancy safety guarantees; enforces ingredients and physician consultation disclaimers.
5. **Return Policy**: Prevents approval of returns beyond standard 15-day window without managerial exception.
        """
    )
