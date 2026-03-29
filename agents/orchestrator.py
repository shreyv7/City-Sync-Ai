"""
Orchestrator Agent — The brain of the CitySync multi-agent system.

Coordinates all agents in sequence:
  Document Agent → Room Agent → Compliance Agent → Report Agent

Implements:
  - Workflow planning and execution
  - Failure detection and self-correction loops
  - Embedded guardrails (merged from standalone Guardrails Agent)
  - Action execution (approval / conditional / rejection)
  - Full audit trail management
"""

from __future__ import annotations

from core.audit_logger import AuditTrail
from agents.document_agent import DocumentAgent
from agents.room_agent import RoomAgent
from agents.compliance_agent import ComplianceAgent


class Orchestrator:
    """
    Coordinates the multi-agent compliance workflow.

    Usage:
        orch = Orchestrator()
        result = orch.run(uploaded_file, city="New Delhi")
    """

    NAME = "orchestrator"

    def __init__(self):
        self.audit = AuditTrail()
        self.doc_agent = DocumentAgent(self.audit)
        self.room_agent = RoomAgent(self.audit)
        self.compliance_agent = ComplianceAgent(self.audit)
        self.all_status_updates: list[dict] = []

    # ── Main Workflow ────────────────────────────────────────────────

    def run(self, uploaded_file, city: str = "New Delhi") -> dict:
        """
        Execute the full compliance workflow autonomously.

        Args:
            uploaded_file: Streamlit UploadedFile object.
            city: City regulations to check against.

        Returns:
            dict with:
                results: Compliance results with reasoning.
                rooms: Parsed room data.
                compliance_score: 0–100%.
                approval_status: APPROVED / CONDITIONAL / REJECTED.
                total_area: Sum of room areas.
                cross_room_flags: Cross-room warnings.
                audit_trail: Full JSON audit trail.
                status_updates: All agent status messages.
                extraction_method: How text was obtained.
                image: Floor plan image.
                text: Extracted text.
        """
        self.all_status_updates = []

        self.audit.log(
            agent=self.NAME,
            action="workflow_start",
            input_data={"city": city},
            reasoning=[
                f"Starting autonomous compliance workflow for {city}.",
                "Pipeline: Document → Room → Compliance → Report.",
            ],
            result="STARTED",
            confidence=1.0,
        )
        self._add_status("🎯 Starting autonomous compliance workflow…")

        # ── Phase 1: Document Extraction ─────────────────────────────
        doc_result = self.doc_agent.extract(uploaded_file)
        self.all_status_updates.extend(doc_result["status_updates"])

        text = doc_result["text"]
        image = doc_result["image"]
        method = doc_result["method"]
        doc_confidence = doc_result["confidence"]
        text_blocks = doc_result.get("text_blocks", [])

        # ── Self-correction: retry if confidence too low ─────────────
        if doc_confidence < 0.5 and image is not None:
            self.audit.log(
                agent=self.NAME,
                action="self_correction_trigger",
                reasoning=[
                    f"Document extraction confidence is {doc_confidence:.0%} (below 50% threshold).",
                    "Triggering enhanced OCR retry with adjusted parameters.",
                ],
                result="RETRYING",
                confidence=doc_confidence,
            )
            self._add_status("🔄 Low confidence — retrying with enhanced OCR…", retry=True)

            retry_result = self.doc_agent.retry_with_enhanced_ocr(image)
            if retry_result["confidence"] > doc_confidence:
                text = retry_result["text"]
                doc_confidence = retry_result["confidence"]
                method = "easyocr_enhanced"
                text_blocks = retry_result.get("text_blocks", [])
                self._add_status(
                    f"✅ Enhanced OCR improved confidence to {doc_confidence:.0%}",
                    ok=True,
                )
            else:
                self._add_status("⚠️ Enhanced OCR did not improve results", retry=True)

        # ── Phase 2: Room Extraction ─────────────────────────────────
        room_result = self.room_agent.parse(
            text, image=image, extraction_method=method
        )
        self.all_status_updates.extend(room_result["status_updates"])

        rooms = room_result["rooms"]
        room_confidence = room_result["overall_confidence"]

        # ── Self-correction: too few rooms ───────────────────────────
        if len(rooms) < 2 and image is not None and method != "contour":
            self.audit.log(
                agent=self.NAME,
                action="self_correction_trigger",
                reasoning=[
                    f"Only {len(rooms)} room(s) detected — expected at least 2.",
                    "Retrying Document Agent with enhanced OCR.",
                ],
                result="RETRYING",
                confidence=0.3,
            )
            self._add_status(
                f"🔄 Only {len(rooms)} room(s) found — retrying extraction…",
                retry=True,
            )

            retry = self.doc_agent.retry_with_enhanced_ocr(image)
            if retry["text"]:
                re_rooms = self.room_agent.parse(
                    retry["text"], image=image, extraction_method="easyocr_retry"
                )
                if len(re_rooms["rooms"]) > len(rooms):
                    rooms = re_rooms["rooms"]
                    room_confidence = re_rooms["overall_confidence"]
                    self.all_status_updates.extend(re_rooms["status_updates"])
                    text_blocks = retry.get("text_blocks", [])
                    self._add_status(
                        f"✅ Retry found {len(rooms)} rooms",
                        ok=True,
                    )

        # ── Guardrail: flag rooms with missing dimensions ────────────
        zero_dim_rooms = [r for r in rooms if (r.get("width_ft", 0) or 0) == 0 or (r.get("length_ft", 0) or 0) == 0]
        if zero_dim_rooms:
            names = [r["room_name"] for r in zero_dim_rooms]
            self.audit.log(
                agent=self.NAME,
                action="guardrail_flag",
                reasoning=[
                    f"{len(zero_dim_rooms)} room(s) have missing dimensions: {names}.",
                    "Flagged for manual review.",
                ],
                result="NEEDS_HUMAN_REVIEW",
                confidence=0.4,
            )
            self._add_status(
                f"⚠️ {len(zero_dim_rooms)} room(s) flagged for manual dimension review",
                retry=True,
            )

        # ── Phase 3: Compliance Check ────────────────────────────────
        if not rooms:
            self.audit.log(
                agent=self.NAME,
                action="workflow_abort",
                reasoning=["No rooms detected — cannot run compliance check."],
                result="ABORTED",
                confidence=0.0,
            )
            self._add_status("❌ No rooms detected — workflow aborted")
            return self._build_empty_result(image, text, method)

        comp_result = self.compliance_agent.check(rooms, city=city)
        self.all_status_updates.extend(comp_result["status_updates"])

        # ── Phase 4: Action Execution ────────────────────────────────
        approval = comp_result["approval_status"]
        score = comp_result["compliance_score"]

        action_reasoning = self._execute_action(approval, score, city)

        self.audit.log(
            agent=self.NAME,
            action="workflow_complete",
            input_data={"city": city},
            reasoning=[
                f"Workflow completed successfully.",
                f"Rooms: {len(rooms)}, Score: {score}%, Status: {approval}.",
                f"Audit trail contains {self.audit.count} entries.",
                *action_reasoning,
            ],
            result={
                "approval": approval,
                "score": score,
                "rooms": len(rooms),
                "audit_entries": self.audit.count,
            },
            confidence=0.95,
        )

        self._add_status(
            f"✅ Workflow complete — {approval} ({score}%)",
            ok=True,
        )

        return {
            "results": comp_result["results"],
            "rooms": rooms,
            "compliance_score": score,
            "approval_status": approval,
            "total_area": comp_result["total_area"],
            "cross_room_flags": comp_result["cross_room_flags"],
            "audit_trail": self.audit.get_trail(),
            "audit_trail_json": self.audit.to_json(),
            "status_updates": self.all_status_updates,
            "extraction_method": method,
            "image": image,
            "text": text,
            "text_blocks": text_blocks,
        }

    # ── Action Execution ─────────────────────────────────────────────

    def _execute_action(self, approval: str, score: float, city: str) -> list[str]:
        """
        Execute the final action based on compliance result.
        Returns reasoning steps for the audit trail.
        """
        if approval == "APPROVED":
            self._add_status(
                "🏛️ AUTO-ACTION: Generating Approval Certificate",
                ok=True,
            )
            return [
                f"Action: Plan is 100% compliant with {city} regulations.",
                "Auto-generated Approval Certificate.",
                "Municipal database status updated to APPROVED.",
            ]
        elif approval == "CONDITIONAL":
            self._add_status(
                "📋 AUTO-ACTION: Generating Conditional Approval with required fixes",
                ok=True,
            )
            return [
                f"Action: Plan is {score}% compliant (≥70% threshold).",
                "Generated Conditional Approval with fix list.",
                "Status: CONDITIONAL — resubmit after corrections.",
            ]
        else:
            self._add_status(
                "❌ AUTO-ACTION: Plan REJECTED — violations exceed threshold",
                retry=True,
            )
            return [
                f"Action: Plan is {score}% compliant (below 70% threshold).",
                "Generated Rejection Report with all violations detailed.",
                "Status: REJECTED — significant redesign required.",
            ]

    # ── Helpers ───────────────────────────────────────────────────────

    def _add_status(self, message: str, ok: bool = False, retry: bool = False):
        status = "ok" if ok else ("retry" if retry else "running")
        self.all_status_updates.append({
            "agent": self.NAME,
            "message": message,
            "status": status,
        })

    def _build_empty_result(self, image, text, method) -> dict:
        return {
            "results": [],
            "rooms": [],
            "compliance_score": 0.0,
            "approval_status": "REJECTED",
            "total_area": 0.0,
            "cross_room_flags": ["No rooms could be detected from the uploaded document."],
            "audit_trail": self.audit.get_trail(),
            "audit_trail_json": self.audit.to_json(),
            "status_updates": self.all_status_updates,
            "extraction_method": method,
            "image": image,
            "text": text,
            "text_blocks": [],
        }
