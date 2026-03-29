"""
Gemini LLM client with automatic API key rotation.

Loads multiple Gemini API keys from .env and rotates through them
seamlessly when one hits rate limits or quota exhaustion.
Falls back to deterministic templates if ALL keys are exhausted.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

# Load .env file manually (avoid requiring python-dotenv)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_env() -> None:
    """Load key=value pairs from .env into os.environ."""
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()


class GeminiKeyRotator:
    """
    Manages multiple Gemini API keys with automatic rotation.

    On a rate-limit or quota error, silently switches to the next key.
    If all keys are exhausted, sets `all_exhausted = True` so callers
    can fall back to deterministic templates.
    """

    def __init__(self):
        self.keys = self._collect_keys()
        self.current_index = 0
        self.all_exhausted = False
        self._failed_keys: set[int] = set()
        self._client = None

    # ── Key management ───────────────────────────────────────────────

    @staticmethod
    def _collect_keys() -> list[str]:
        """Collect all GEMINI_API_KEY_* values from environment."""
        keys = []
        for i in range(1, 10):
            key = os.environ.get(f"GEMINI_API_KEY_{i}", "")
            if key:
                keys.append(key)
        # Also check a single GEMINI_API_KEY
        single = os.environ.get("GEMINI_API_KEY", "")
        if single and single not in keys:
            keys.insert(0, single)
        return keys

    @property
    def current_key(self) -> str | None:
        if not self.keys or self.all_exhausted:
            return None
        return self.keys[self.current_index]

    def rotate(self) -> bool:
        """
        Switch to the next available key.

        Returns:
            True if a new key is available, False if all are exhausted.
        """
        self._failed_keys.add(self.current_index)

        # Find the next non-failed key
        for _ in range(len(self.keys)):
            self.current_index = (self.current_index + 1) % len(self.keys)
            if self.current_index not in self._failed_keys:
                self._client = None  # Force re-init
                return True

        self.all_exhausted = True
        return False

    # ── LLM call ─────────────────────────────────────────────────────

    def generate(self, prompt: str, max_retries: int = 3) -> str | None:
        """
        Call Gemini with automatic key rotation on failure.

        Args:
            prompt: The text prompt to send.
            max_retries: Max rotation attempts.

        Returns:
            The generated text, or None if all keys failed.
        """
        if not self.keys:
            return None

        try:
            from google import genai as google_genai
        except ImportError:
            return None

        for attempt in range(max_retries):
            if self.all_exhausted:
                return None

            key = self.current_key
            if not key:
                return None

            try:
                client = google_genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                return response.text

            except Exception as e:
                err = str(e).lower()
                # Rate limit / quota errors → rotate
                if any(kw in err for kw in [
                    "429", "quota", "rate", "resource_exhausted",
                    "limit", "too many", "exceeded"
                ]):
                    if not self.rotate():
                        return None
                    time.sleep(0.5)  # Brief pause before retry
                else:
                    # Non-rate-limit error → still try rotating
                    if attempt < max_retries - 1:
                        if not self.rotate():
                            return None
                    else:
                        return None

        return None

    def reset(self) -> None:
        """Reset all failed keys (e.g., between sessions)."""
        self._failed_keys.clear()
        self.all_exhausted = False
        self.current_index = 0
        self._client = None


# Module-level singleton
_rotator: GeminiKeyRotator | None = None


def get_rotator() -> GeminiKeyRotator:
    """Get or create the global key rotator singleton."""
    global _rotator
    if _rotator is None:
        _rotator = GeminiKeyRotator()
    return _rotator
