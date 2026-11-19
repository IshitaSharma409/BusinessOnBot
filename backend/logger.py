"""
Audit Logging and Analytics Module for BusinessOnBot.
Logs every decision to JSON and SQLite, and provides Pandas-based metrics and analytics.
"""
import os
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd

from backend.models import PipelineResult, GuardrailDecision, RiskLevel, ChannelType


class AuditLogger:
    """Manages structured persistence and Pandas analytics for guardrail executions."""

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            self.log_dir = Path(__file__).resolve().parent.parent / "logs"
        else:
            self.log_dir = Path(log_dir)

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.json_log_path = self.log_dir / "audit_log.json"
        self.db_path = self.log_dir / "audit.db"
        self._init_sqlite()

    def _init_sqlite(self):
        """Initializes SQLite schema for robust historical audit tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT,
                channel TEXT,
                customer_id TEXT,
                order_id TEXT,
                sku TEXT,
                query TEXT,
                initial_draft TEXT,
                final_response TEXT,
                intent TEXT,
                risk_level TEXT,
                decision TEXT,
                decision_rationale TEXT,
                unsupported_commitments_count INTEGER,
                latency_ms REAL,
                escalation_ticket_id TEXT,
                raw_json TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_result(self, result: PipelineResult):
        """Persists a pipeline execution to both JSON and SQLite."""
        record = {
            "request_id": result.request_id,
            "timestamp": result.timestamp,
            "channel": result.channel.value,
            "customer_id": result.customer_id,
            "order_id": result.order_id,
            "sku": result.sku,
            "query": result.query,
            "initial_draft": result.initial_draft,
            "final_response": result.final_response,
            "intent": result.guardrail.intent.value,
            "risk_level": result.guardrail.risk_level.value,
            "decision": result.guardrail.decision.value,
            "decision_rationale": result.guardrail.decision_rationale,
            "unsupported_commitments_count": result.guardrail.unsupported_commitments_count,
            "latency_ms": round(result.latency_ms, 2),
            "escalation_ticket_id": result.escalation_ticket_id,
            "claims_detected": [c.model_dump() for c in result.guardrail.claims_detected],
            "evidence_retrieved": [e.model_dump() for e in result.guardrail.evidence_retrieved],
            "validation_results": [v.model_dump() for v in result.guardrail.validation_results]
        }

        # 1. Append to JSON file
        logs = []
        if self.json_log_path.exists():
            try:
                with open(self.json_log_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(record)
        with open(self.json_log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)

        # 2. Insert into SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audit_logs VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                record["request_id"],
                record["timestamp"],
                record["channel"],
                record["customer_id"],
                record["order_id"],
                record["sku"],
                record["query"],
                record["initial_draft"],
                record["final_response"],
                record["intent"],
                record["risk_level"],
                record["decision"],
                record["decision_rationale"],
                record["unsupported_commitments_count"],
                record["latency_ms"],
                record["escalation_ticket_id"],
                json.dumps(record)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            pass

    def get_all_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves historical audit records ordered by most recent."""
        if not self.json_log_path.exists():
            return []
        try:
            with open(self.json_log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
                return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        except Exception:
            return []

    def get_analytics_metrics(self) -> Dict[str, Any]:
        """Calculates key operational and safety metrics using Pandas."""
        logs = self.get_all_logs(limit=1000)
        if not logs:
            return {
                "total_queries": 0,
                "allowed_count": 0,
                "rewritten_count": 0,
                "blocked_count": 0,
                "escalated_count": 0,
                "unsupported_commitment_rate": 0.0,
                "avg_latency_ms": 0.0,
                "decisions_breakdown": {},
                "risk_distribution": {},
                "channel_distribution": {},
                "intent_distribution": {}
            }

        df = pd.DataFrame(logs)
        total = len(df)

        decision_counts = df["decision"].value_counts().to_dict()
        allowed = decision_counts.get("ALLOW", 0)
        rewritten = decision_counts.get("REWRITE", 0)
        blocked = decision_counts.get("BLOCK", 0)
        escalated = decision_counts.get("ESCALATE", 0)

        # Unsupported commitment rate: percentage of audited agent replies containing
        # an unsupported commitment intercepted by guardrails
        unsupported_mask = (df["unsupported_commitments_count"] > 0) | (df["decision"].isin(["REWRITE", "BLOCK", "ESCALATE"]))
        unsupported_count = int(unsupported_mask.sum())
        unsupported_rate = round((unsupported_count / total) * 100, 2) if total > 0 else 0.0

        avg_latency = round(float(df["latency_ms"].mean()), 2) if "latency_ms" in df.columns else 0.0

        risk_dist = df["risk_level"].value_counts().to_dict() if "risk_level" in df.columns else {}
        channel_dist = df["channel"].value_counts().to_dict() if "channel" in df.columns else {}
        intent_dist = df["intent"].value_counts().to_dict() if "intent" in df.columns else {}

        return {
            "total_queries": total,
            "allowed_count": allowed,
            "rewritten_count": rewritten,
            "blocked_count": blocked,
            "escalated_count": escalated,
            "unsupported_commitment_rate": unsupported_rate,
            "avg_latency_ms": avg_latency,
            "decisions_breakdown": decision_counts,
            "risk_distribution": risk_dist,
            "channel_distribution": channel_dist,
            "intent_distribution": intent_dist
        }
