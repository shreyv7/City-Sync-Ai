"""
Structured JSON audit logger for the CitySync multi-agent system.

Every agent decision is logged with:
  - timestamp
  - agent name
  - action performed
  - input data
  - reasoning chain (list of steps)
  - result
  - confidence score (0.0 – 1.0)

The trail is session-scoped (lives in memory) and can be exported
as JSON or displayed in the Streamlit UI.
"""

import json
from datetime import datetime, timezone, timedelta


# IST offset for timestamps
_IST = timedelta(hours=5, minutes=30)


class AuditTrail:
    """Session-scoped audit logger used by all agents."""

    def __init__(self):
        self._entries: list[dict] = []

    # ── Core API ─────────────────────────────────────────────────────

    def log(
        self,
        agent: str,
        action: str,
        input_data: dict | str | None = None,
        reasoning: list[str] | None = None,
        result: str | dict | None = None,
        confidence: float = 1.0,
    ) -> dict:
        """
        Append a decision entry to the audit trail.

        Args:
            agent: Name of the agent (e.g. "document_agent").
            action: What the agent did (e.g. "extract_text").
            input_data: The input the agent received.
            reasoning: Step-by-step reasoning chain.
            result: The output / decision.
            confidence: 0.0–1.0 confidence in the result.

        Returns:
            The logged entry dict (for convenience).
        """
        entry = {
            "id": len(self._entries) + 1,
            "timestamp": datetime.now(
                tz=timezone(_IST)
            ).isoformat(timespec="seconds"),
            "agent": agent,
            "action": action,
            "input": input_data,
            "reasoning": reasoning or [],
            "result": result,
            "confidence": round(confidence, 2),
        }
        self._entries.append(entry)
        return entry

    # ── Retrieval ────────────────────────────────────────────────────

    def get_trail(self) -> list[dict]:
        """Return a copy of all logged entries."""
        return list(self._entries)

    def get_entries_by_agent(self, agent: str) -> list[dict]:
        """Filter entries by agent name."""
        return [e for e in self._entries if e["agent"] == agent]

    def get_latest(self, n: int = 5) -> list[dict]:
        """Return the *n* most recent entries."""
        return list(self._entries[-n:])

    # ── Export ───────────────────────────────────────────────────────

    def to_json(self, indent: int = 2) -> str:
        """Serialize the entire trail as a JSON string."""
        return json.dumps(self._entries, indent=indent, default=str)

    def to_dict_list(self) -> list[dict]:
        """Return the raw list of dicts (for DataFrame conversion)."""
        return list(self._entries)

    # ── Utility ──────────────────────────────────────────────────────

    def clear(self) -> None:
        """Reset the trail (useful between sessions)."""
        self._entries.clear()

    @property
    def count(self) -> int:
        return len(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"AuditTrail(entries={len(self._entries)})"
