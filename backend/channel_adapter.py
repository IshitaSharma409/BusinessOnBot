"""
Channel Adapter Module for BusinessOnBot.
Normalizes incoming messages across WhatsApp, Instagram, Messenger, Email, Voice, and Web Chat,
and formats responses according to channel-specific constraints.
"""
from typing import Dict, Any
from backend.models import ChannelType, CustomerQueryRequest


class ChannelAdapter:
    """Adapts queries and responses across multiple simulated communication channels."""

    @staticmethod
    def normalize_request(request: CustomerQueryRequest) -> Dict[str, Any]:
        """Cleans and prepares input query for downstream pipeline processing."""
        normalized_query = request.query.strip()
        return {
            "channel": request.channel,
            "raw_query": normalized_query,
            "customer_id": request.customer_id.strip() if request.customer_id else None,
            "order_id": request.order_id.strip() if request.order_id else None,
            "sku": request.sku.strip() if request.sku else None,
            "force_hallucination": request.force_hallucination
        }

    @staticmethod
    def format_response_for_channel(text: str, channel: ChannelType) -> str:
        """Adapts final vetted response text to channel-appropriate delivery style."""
        if not text:
            return ""

        if channel == ChannelType.voice:
            # Voice / TTS: Remove asterisks, hashtags, bullets, emojis for clean spoken synthesis
            clean_text = text.replace("*", "").replace("#", "").replace("- ", "").replace("_", "")
            return clean_text.strip()

        elif channel == ChannelType.email:
            # Email: Formal greeting and professional signoff
            if not text.lower().startswith("dear") and not text.lower().startswith("hello") and not text.lower().startswith("hi"):
                text = f"Hello,\n\n{text}"
            if "regards" not in text.lower() and "support team" not in text.lower():
                text = f"{text}\n\nBest regards,\nCustomer Care Team\nBusinessOnBot Demo Brand"
            return text

        elif channel == ChannelType.whatsapp:
            # WhatsApp: Clean markdown bolding
            return text

        elif channel in (ChannelType.instagram, ChannelType.messenger):
            # Social channels: concise, conversational
            return text

        # Default web_chat
        return text
