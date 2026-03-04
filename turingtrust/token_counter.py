"""
TuringTrust — Token Counter

Count tokens using tiktoken (cl100k_base) with a word-count fallback.
"""

from typing import Optional


class TokenCounter:
    """
    Count tokens in text.

    Uses tiktoken's cl100k_base encoding when available, falls back to
    a word-count heuristic (len(words) * 4/3) when tiktoken is not installed.
    """

    def __init__(self):
        self._encoding = None
        try:
            import tiktoken
            self._encoding = tiktoken.get_encoding("cl100k_base")
        except (ImportError, Exception):
            pass

    def count(self, text: str) -> int:
        """
        Count the number of tokens in text.

        Args:
            text: The string to tokenize.

        Returns:
            Token count (exact with tiktoken, estimated without).
        """
        if not text:
            return 0
        if self._encoding:
            try:
                return len(self._encoding.encode(text))
            except Exception:
                pass
        # Fallback: rough word-based estimate
        return len(text.split()) * 4 // 3

    def count_messages(self, messages: list[dict]) -> int:
        """
        Count tokens across a list of chat messages.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.

        Returns:
            Total token count across all messages (+ overhead per message).
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count(content)
            elif isinstance(content, list):
                # Handle multi-part messages (vision, etc.)
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count(part["text"])
            total += 4  # per-message overhead (role, separators)
        total += 2  # reply priming
        return total
