"""
TuringTrust — Governance Hooks

Abstract base class for governance hooks.
Hooks let you add custom pre-request and post-response logic
to the gateway without modifying gateway internals.

Example:
    from turingtrust.hooks import GovernanceHook
    from turingtrust.pii_detector import detect_pii

    class PIIHook(GovernanceHook):
        def pre_request(self, provider, model, messages, metadata):
            text = " ".join(m.get("content", "") for m in messages)
            result = detect_pii(text)
            if result.total_findings > 0:
                metadata["pii_detected"] = True
                metadata["pii_counts"] = result.entity_counts
            return messages, metadata  # pass-through (no blocking)

        def post_response(self, provider, model, response, metadata):
            return response  # pass-through
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class GovernanceHook(ABC):
    """
    Abstract base class for gateway governance hooks.

    Subclass this and pass instances to GatewayService to intercept
    requests and responses flowing through the gateway.
    """

    @abstractmethod
    def pre_request(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        metadata: dict,
    ) -> tuple[list[dict], dict]:
        """
        Called before a request is sent to the LLM provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic").
            model: Model name (e.g., "gpt-4o").
            messages: The chat messages to be sent.
            metadata: Mutable dict for passing data to post_response.

        Returns:
            Tuple of (messages, metadata) — modify messages if needed.

        Raises:
            Exception: Raise to abort the request. The gateway will return
                       the exception message as an error response.
        """
        ...

    @abstractmethod
    def post_response(
        self,
        provider: str,
        model: str,
        response: dict,
        metadata: dict,
    ) -> dict:
        """
        Called after receiving a response from the LLM provider.

        Args:
            provider: Provider name.
            model: Model name.
            response: The raw JSON response from the provider.
            metadata: Same dict from pre_request (carry data between phases).

        Returns:
            The response dict (modify if needed, e.g., add governance metadata).
        """
        ...


class PIIDetectionHook(GovernanceHook):
    """
    Built-in hook: scans prompts for PII using Tier 1 regex detection.

    Attaches findings to the response under response["governance"]["pii"].
    Does NOT block requests — detection only. For enforcement (BLOCK/REDACT),
    use TuringTrust Cloud (turingtrust.ai).
    """

    def pre_request(self, provider, model, messages, metadata):
        from turingtrust.pii_detector import detect_pii

        text = " ".join(
            m.get("content", "") for m in messages
            if isinstance(m.get("content"), str)
        )
        result = detect_pii(text)
        metadata["pii_result"] = {
            "detected": result.total_findings > 0,
            "total_findings": result.total_findings,
            "entity_counts": result.entity_counts,
            "scan_time_ms": result.scan_time_ms,
        }
        return messages, metadata

    def post_response(self, provider, model, response, metadata):
        pii = metadata.get("pii_result")
        if pii and isinstance(response, dict):
            response.setdefault("governance", {})
            response["governance"]["pii"] = pii
        return response


class LoggingHook(GovernanceHook):
    """
    Built-in hook: logs request/response metadata to stdout.
    Useful for debugging.
    """

    def pre_request(self, provider, model, messages, metadata):
        import sys
        msg_count = len(messages)
        print(f"[TuringTrust] → {provider}/{model} ({msg_count} messages)", file=sys.stderr)
        return messages, metadata

    def post_response(self, provider, model, response, metadata):
        import sys
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        tokens = usage.get("total_tokens", "?")
        print(f"[TuringTrust] ← {provider}/{model} ({tokens} tokens)", file=sys.stderr)
        return response
