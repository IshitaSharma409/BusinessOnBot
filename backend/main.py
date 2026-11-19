"""
Main Application & FastAPI REST API for BusinessOnBot AI Customer Support Agent with Commitment Guardrails.
Orchestrates the entire guardrail pipeline from customer query to final safe response.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.models import (
    CustomerQueryRequest,
    PipelineResult,
    GuardrailAnalysis,
    GuardrailDecision,
    ChannelType,
    RiskLevel
)
from backend.channel_adapter import ChannelAdapter
from backend.intent_detection import IntentDetector
from backend.risk_classifier import RiskClassifier
from backend.knowledge_base import KnowledgeBase
from backend.llm_generator import LLMGenerator
from backend.commitment_detector import CommitmentDetector
from backend.evidence_validator import EvidenceValidator
from backend.decision_engine import DecisionEngine
from backend.response_rewriter import ResponseRewriter
from backend.logger import AuditLogger

# Initialize core services
kb = KnowledgeBase()
llm = LLMGenerator()
logger_service = AuditLogger()

app = FastAPI(
    title="BusinessOnBot - AI Customer Support Agent with Commitment Guardrails",
    description="Prevents AI from making unsupported promises, false claims, or unauthorized commitments.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_customer_query(request: CustomerQueryRequest) -> PipelineResult:
    """
    Executes the full 10-stage Commitment Guardrail pipeline:
    1. Channel Adapter (Normalize)
    2. Intent Detection
    3. Risk Classification
    4. Retrieve Business Evidence
    5. Generate AI Draft Response
    6. Independent Commitment Detection
    7. Evidence & Policy Validation (5-point check)
    8. Decision Engine (ALLOW / REWRITE / BLOCK / ESCALATE)
    9. Response Rewriting & Final Channel Formatting
    10. Audit Logging & Analytics
    """
    start_time = time.time()
    req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Step 1: Channel Adapter (Input normalization)
    normalized = ChannelAdapter.normalize_request(request)
    raw_query = normalized["raw_query"]
    channel = normalized["channel"]
    cust_id = normalized["customer_id"]
    order_id = normalized["order_id"]
    sku = normalized["sku"]
    force_hallucination = normalized["force_hallucination"]

    # Step 2: Intent Detection and Entity Extraction
    intent, entities = IntentDetector.detect_intent_and_entities(
        raw_query,
        provided_order_id=order_id,
        provided_sku=sku
    )
    eff_order_id = entities.get("order_id") or order_id
    eff_sku = entities.get("sku") or sku

    # Step 3: Risk Classification
    risk_level = RiskClassifier.classify_risk(intent, raw_query)

    # Step 4: Retrieve Business Evidence
    evidence_list = kb.retrieve_evidence_for_query(
        intent=intent,
        entities=entities,
        customer_id=cust_id,
        order_id=eff_order_id,
        sku=eff_sku
    )

    # Step 5: LLM Draft Generation (Structured JSON with draft response)
    draft_dto = llm.generate_draft(
        query=raw_query,
        intent=intent,
        risk_level=risk_level,
        retrieved_facts=[e.model_dump() for e in evidence_list],
        force_hallucination=force_hallucination
    )
    raw_draft_text = draft_dto.draft_response

    # Step 6: Independent Commitment Detection (NEVER blindly trust LLM)
    detected_commitments = CommitmentDetector.detect_commitments(raw_draft_text)

    # Step 7: Evidence & Policy Validation (5 criteria checks)
    validation_results = EvidenceValidator.validate_claims(
        claims=detected_commitments,
        evidence_list=evidence_list,
        context={
            "customer_id": cust_id,
            "order_id": eff_order_id,
            "sku": eff_sku,
            "query": raw_query
        }
    )

    # Step 8: Decision Engine
    decision, rationale = DecisionEngine.determine_decision(
        intent=intent,
        risk_level=risk_level,
        validations=validation_results,
        evidence_list=evidence_list
    )

    # Step 9: Final Customer Response Generation & Channel Adapter Delivery
    escalation_ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}" if decision == GuardrailDecision.ESCALATE else None
    
    if decision == GuardrailDecision.ALLOW:
        final_text = raw_draft_text
    else:
        final_text = ResponseRewriter.generate_safe_response(
            intent=intent,
            decision=decision,
            validations=validation_results,
            evidence_list=evidence_list,
            context={
                "escalation_ticket_id": escalation_ticket_id,
                "order_id": eff_order_id,
                "sku": eff_sku
            }
        )

    # Format text for specific channel (e.g. voice TTS vs WhatsApp markdown vs Email)
    channel_formatted_response = ChannelAdapter.format_response_for_channel(final_text, channel)

    unsupported_count = sum(1 for v in validation_results if not v.is_supported)

    guardrail_analysis = GuardrailAnalysis(
        intent=intent,
        risk_level=risk_level,
        claims_detected=detected_commitments,
        evidence_retrieved=evidence_list,
        validation_results=validation_results,
        decision=decision,
        decision_rationale=rationale,
        unsupported_commitments_count=unsupported_count
    )

    latency_ms = (time.time() - start_time) * 1000

    result = PipelineResult(
        request_id=req_id,
        query=raw_query,
        channel=channel,
        customer_id=cust_id,
        order_id=eff_order_id,
        sku=eff_sku,
        initial_draft=raw_draft_text,
        final_response=channel_formatted_response,
        guardrail=guardrail_analysis,
        latency_ms=round(latency_ms, 2),
        timestamp=timestamp,
        escalation_ticket_id=escalation_ticket_id
    )

    # Step 10: Logging & Audit Persistence
    logger_service.log_result(result)

    return result


@app.post("/api/process", response_model=PipelineResult)
def process_query_endpoint(request: CustomerQueryRequest):
    """Processes customer query through the complete Commitment Guardrail pipeline."""
    try:
        return process_customer_query(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/api/analytics")
def get_analytics():
    """Retrieves computed analytics and metrics from past audited interactions."""
    return logger_service.get_analytics_metrics()


@app.get("/api/audit-logs")
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    decision: Optional[str] = None,
    channel: Optional[str] = None
):
    """Retrieves historical audit entries with optional filtering."""
    logs = logger_service.get_all_logs(limit=limit)
    if decision:
        logs = [l for l in logs if l.get("decision") == decision.upper()]
    if channel:
        logs = [l for l in logs if l.get("channel") == channel.lower()]
    return logs


@app.get("/api/knowledge")
def get_knowledge_summary():
    """Inspects all retrieved mock business records."""
    return {
        "refunds": kb.refunds_data,
        "products": kb.products_data,
        "discounts": kb.discounts_data,
        "return_policies": kb.return_policies_data,
        "safety_data": kb.safety_data
    }


@app.get("/api/health")
def health_check():
    """System health check and operational status."""
    return {
        "status": "healthy",
        "service": "BusinessOnBot Commitment Guardrail Gateway",
        "llm_mode": llm.provider,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
