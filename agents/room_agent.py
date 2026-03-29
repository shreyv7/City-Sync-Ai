"""
Room Agent — Responsible for parsing room names and dimensions from extracted text.

Wraps `core/text_parser.py` and adds:
  - Per-room confidence scoring
  - Ambiguous room flagging
  - Audit trail logging for every parsing decision
  - Status updates for the UI self-correction panel
"""

from __future__ import annotations

import re

import core.text_parser as text_parser
import core.vision_reader as vision_reader
from core.audit_logger import AuditTrail


class RoomAgent:
    """Parses room names and dimensions from floor plan text."""

    NAME = "room_agent"

    def __init__(self, audit: AuditTrail):
        self.audit = audit

    # ── Public API ───────────────────────────────────────────────────

    def parse(
        self,
        text: str,
        image=None,
        extraction_method: str = "pdfplumber",
    ) -> dict:
        """
        Parse rooms from extracted text with confidence scoring.

        Args:
            text: The extracted text from Document Agent.
            image: Optional floor plan image (for contour fallback).
            extraction_method: How the text was obtained.

        Returns:
            dict with keys:
                rooms (list[dict]): Parsed room data with confidence.
                overall_confidence (float): 0.0–1.0.
                flags (list[str]): Human-readable warnings.
                status_updates (list[dict]): UI messages.
        """
        status_updates: list[dict] = []
        flags: list[str] = []

        status_updates.append(self._status("Parsing room names and dimensions…"))

        # ── Step 1: Text-based parsing ───────────────────────────────
        rooms = []
        if text and len(text.strip()) > 10:
            rooms = text_parser.parse_rooms_from_text(text)

            self.audit.log(
                agent=self.NAME,
                action="parse_text",
                input_data={
                    "text_length": len(text),
                    "source": extraction_method,
                },
                reasoning=[
                    f"Parsed {len(rooms)} rooms from {extraction_method} text.",
                    f"Text had {len(text)} characters.",
                ],
                result={"room_count": len(rooms)},
                confidence=0.8 if len(rooms) >= 3 else 0.4,
            )

        # ── Step 2: Contour fallback ─────────────────────────────────
        if len(rooms) < 2 and image is not None:
            status_updates.append(
                self._status(
                    "⚠️ Too few rooms from text — trying contour detection…",
                    retry=True,
                )
            )

            try:
                detected = vision_reader.detect_rooms(image)
                contour_rooms = [
                    {
                        "room_name": r["room_name"],
                        "width_ft": r["width_ft"],
                        "length_ft": r["length_ft"],
                    }
                    for r in detected
                ]
            except Exception:
                contour_rooms = []

            if len(contour_rooms) > len(rooms):
                rooms = contour_rooms
                self.audit.log(
                    agent=self.NAME,
                    action="contour_fallback",
                    reasoning=[
                        "Self-correction: text parsing found too few rooms.",
                        f"Contour detection found {len(contour_rooms)} regions.",
                        "WARNING: Room names and dimensions may be generic.",
                    ],
                    result={"room_count": len(contour_rooms)},
                    confidence=0.2,
                )
                flags.append(
                    "Rooms detected via contour analysis — names and dimensions may be inaccurate."
                )

        # ── Step 3: Score each room ──────────────────────────────────
        scored_rooms = []
        for room in rooms:
            room_conf = self._score_room(room)
            room["confidence"] = room_conf

            # Flag issues
            if room_conf < 0.5:
                room_flag = self._describe_issue(room)
                if room_flag:
                    flags.append(room_flag)

            scored_rooms.append(room)

        # ── Step 4: Overall confidence ───────────────────────────────
        if scored_rooms:
            overall = sum(r["confidence"] for r in scored_rooms) / len(scored_rooms)
        else:
            overall = 0.0

        # Log summary
        room_summary = [
            f"  {r['room_name']}: {r['width_ft']}×{r['length_ft']} ft "
            f"(conf: {r['confidence']:.0%})"
            for r in scored_rooms
        ]
        self.audit.log(
            agent=self.NAME,
            action="parsing_complete",
            input_data={"source": extraction_method},
            reasoning=[
                f"Parsed {len(scored_rooms)} rooms total.",
                f"Overall confidence: {overall:.2f}.",
                *room_summary,
            ],
            result={
                "room_count": len(scored_rooms),
                "rooms": [r["room_name"] for r in scored_rooms],
                "flags": flags,
            },
            confidence=overall,
        )

        if scored_rooms:
            status_updates.append(
                self._status(
                    f"✅ Detected {len(scored_rooms)} rooms (confidence: {overall:.0%})",
                    ok=True,
                )
            )
        else:
            status_updates.append(
                self._status("❌ No rooms detected", retry=False)
            )

        return {
            "rooms": scored_rooms,
            "overall_confidence": round(overall, 2),
            "flags": flags,
            "status_updates": status_updates,
        }

    # ── Confidence scoring ───────────────────────────────────────────

    @staticmethod
    def _score_room(room: dict) -> float:
        """
        Assign a confidence score to a single room.

        - 1.0: Known room name + both dimensions > 0
        - 0.7: Known name but one dimension is zero
        - 0.5: Has dimensions but name looks generic/unknown
        - 0.3: Known name but both dimensions are zero
        - 0.1: Generic name + no dimensions
        """
        name = room.get("room_name", "")
        w = room.get("width_ft", 0) or 0
        l = room.get("length_ft", 0) or 0

        has_both_dims = w > 0 and l > 0
        has_one_dim = (w > 0) != (l > 0)  # XOR
        is_known = RoomAgent._is_known_room(name)
        is_generic = name.lower().startswith("room") or name.lower().startswith("suggested")

        if is_known and has_both_dims:
            return 1.0
        if is_known and has_one_dim:
            return 0.7
        if not is_known and has_both_dims:
            return 0.5
        if is_known and not has_both_dims:
            return 0.3
        if is_generic:
            return 0.1
        return 0.2

    @staticmethod
    def _is_known_room(name: str) -> bool:
        """Check if a room name matches any recognized floor plan room type."""
        known = [
            "bedroom", "kitchen", "toilet", "living", "dining", "drawing",
            "hall", "bath", "balcony", "porch", "dress", "wash", "puja",
            "pooja", "study", "store", "utility", "servant", "garage",
            "foyer", "passage", "veranda", "sit out", "terrace", "guest",
            "lobby", "lift", "stair", "canopy", "car park",
        ]
        lower = name.lower()
        return any(kw in lower for kw in known)

    @staticmethod
    def _describe_issue(room: dict) -> str:
        """Generate a human-readable flag for a low-confidence room."""
        name = room.get("room_name", "Unknown")
        w = room.get("width_ft", 0) or 0
        l = room.get("length_ft", 0) or 0

        issues = []
        if w == 0 and l == 0:
            issues.append("dimensions missing")
        elif w == 0 or l == 0:
            issues.append("one dimension missing")

        if not RoomAgent._is_known_room(name):
            issues.append("unrecognized room type")

        if issues:
            return f"{name}: {', '.join(issues)} — please verify manually"
        return ""

    # ── Status helper ────────────────────────────────────────────────

    @staticmethod
    def _status(message: str, ok: bool = False, retry: bool = False) -> dict:
        status = "ok" if ok else ("retry" if retry else "running")
        return {"agent": RoomAgent.NAME, "message": message, "status": status}
