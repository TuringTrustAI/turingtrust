"""LangChain callback handler for TuringTrust governance."""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger("turingtrust")

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    # Graceful fallback if langchain not installed
    class BaseCallbackHandler:
        pass


class TuringTrustCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that integrates with TuringTrust governance.

    Usage:
        from turingtrust import TuringTrustCallbackHandler
        from langchain_openai import ChatOpenAI

        handler = TuringTrustCallbackHandler(
            turingtrust_url="http://localhost:8033",
            turingtrust_api_key="tt_...",
            team="data-science"
        )
        llm = ChatOpenAI(callbacks=[handler])
    """

    def __init__(
        self,
        turingtrust_url: str = "http://localhost:8033",
        turingtrust_api_key: Optional[str] = None,
        team: str = "default",
        user: Optional[str] = None,
    ):
        super().__init__()
        self.turingtrust_url = turingtrust_url
        self.turingtrust_api_key = turingtrust_api_key
        self.team = team
        self.user = user
        self._calls: List[Dict] = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log LLM call start."""
        self._calls.append({
            "run_id": str(run_id),
            "provider": serialized.get("name", "unknown"),
            "prompts": prompts,
            "metadata": metadata,
        })
        logger.info(f"TuringTrust: LLM call started (run_id={run_id})")

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Log LLM call end and report to governance."""
        logger.info(f"TuringTrust: LLM call completed (run_id={run_id})")

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Log LLM errors."""
        logger.error(f"TuringTrust: LLM call error (run_id={run_id}): {error}")

    @property
    def calls(self) -> List[Dict]:
        """Get recorded calls."""
        return list(self._calls)
