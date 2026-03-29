"""
Compliance Agent — Checks rooms against city-specific building regulations.

Wraps `core/rule_engine.py` and enhances each pass/fail decision with:
  - LLM-generated step-by-step reasoning chains (via Gemini)
  - Deterministic fallback if LLM is unavailable
  - Cross-room validation (total area, room count)
  - Full audit trail logging
"""

from __future__ import annotations

import core.rule_engine as rule_engine
from core.audit_logger import AuditTrail
from core.llm_client import get_rotator


class ComplianceAgent:
    """Checks room compliance and generates explainable reasoning."""

    NAME = "compliance_agent"

    def __init__(self, audit: AuditTrail):
        self.audit = audit
        self.rotator = get_rotator()

    # ── Public API ───────────────────────────────────────────────────

    def check(
        self,
        rooms: list[dict],
        city: str = "New Delhi",
    ) -> dict:
        """
        Run compliance checks with LLM reasoning on each room.

        Args:
            rooms: Room dicts with room_name, width_ft, length_ft.
            city: City whose regulations to apply.

        Returns:
            dict with keys:
                results (list[dict]): Enriched compliance results with reasoning.
                compliance_score (float): 0–100 percentage.
                total_area (float): Sum of all room areas.
                approval_status (str): APPROVED / CONDITIONAL / REJECTED.
                cross_room_flags (list[str]): Cross-room validation warnings.
                status_updates (list[dict]): UI messages.
        """
        status_updates: list[dict] = []
        status_updates.append(self._status(f"Checking {len(rooms)} rooms against {city} bylaws…"))

        # ── Step 1: Deterministic compliance ─────────────────────────
        results = rule_engine.calculate_compliance(rooms, city=city)

        # ── Step 2: Add LLM reasoning per room ──────────────────────
        status_updates.append(self._status("Generating reasoning chains…"))

        for result in results:
            reasoning = self._generate_reasoning(result, city)
            result["reasoning_chain"] = reasoning

            self.audit.log(
                agent=self.NAME,
                action="check_room",
                input_data={
                    "room": result["room_name"],
                    "width": result["width_ft"],
                    "length": result["length_ft"],
                },
                reasoning=reasoning,
                result=result["status"],
                confidence=self._result_confidence(result),
            )

        # ── Step 3: Cross-room validation ────────────────────────────
        cross_flags = self._cross_room_validation(results, city)

        # ── Step 4: Calculate metrics ────────────────────────────────
        total_area = sum(r["area_sqft"] for r in results)
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = sum(1 for r in results if r["status"] == "FAIL")
        applicable = pass_count + fail_count
        score = (pass_count / applicable * 100) if applicable > 0 else 0

        # ── Step 5: Approval decision ────────────────────────────────
        if score >= 100:
            approval = "APPROVED"
        elif score >= 70:
            approval = "CONDITIONAL"
        else:
            approval = "REJECTED"

        self.audit.log(
            agent=self.NAME,
            action="compliance_complete",
            input_data={"city": city, "room_count": len(results)},
            reasoning=[
                f"Total rooms checked: {len(results)}.",
                f"Pass: {pass_count}, Fail: {fail_count}.",
                f"Compliance score: {score:.1f}%.",
                f"Approval status: {approval}.",
                *[f"⚠️ {f}" for f in cross_flags],
            ],
            result={
                "score": round(score, 1),
                "approval": approval,
                "pass": pass_count,
                "fail": fail_count,
            },
            confidence=0.95,
        )

        status_updates.append(
            self._status(
                f"✅ Compliance check complete — {approval} ({score:.0f}%)",
                ok=True,
            )
        )

        return {
            "results": results,
            "compliance_score": round(score, 1),
            "total_area": round(total_area, 1),
            "approval_status": approval,
            "cross_room_flags": cross_flags,
            "status_updates": status_updates,
        }

    # ── LLM Reasoning ────────────────────────────────────────────────

    def _generate_reasoning(self, result: dict, city: str) -> list[str]:
        """
        Generate a step-by-step reasoning chain for a compliance decision.
        Uses Gemini LLM with deterministic fallback.
        """
        # Try LLM first
        llm_reasoning = self._llm_reasoning(result, city)
        if llm_reasoning:
            return llm_reasoning

        # Deterministic fallback
        return self._deterministic_reasoning(result, city)

    def _llm_reasoning(self, result: dict, city: str) -> list[str] | None:
        """Call Gemini to generate an explainable reasoning chain."""
        if self.rotator.all_exhausted:
            return None

        prompt = self._build_prompt(result, city)

        try:
            response = self.rotator.generate(prompt)
            if not response:
                return None

            # Parse the response into steps
            lines = []
            for line in response.strip().splitlines():
                line = line.strip()
                if line and not line.startswith("```"):
                    # Remove markdown step numbering if present
                    if line[:3].replace(".", "").replace(" ", "").isdigit():
                        line = line.split(".", 1)[-1].strip()
                        line = line.split(")", 1)[-1].strip()
                    if line.startswith("- "):
                        line = line[2:]
                    if line.startswith("Step"):
                        # Keep "Step N:" prefix
                        pass
                    if line:
                        lines.append(line)

            if len(lines) >= 2:
                # Validate: LLM result must agree with rule engine
                llm_says_pass = any(
                    kw in " ".join(lines).lower()
                    for kw in ["compliant", "pass", "meets", "satisfies"]
                )
                llm_says_fail = any(
                    kw in " ".join(lines).lower()
                    for kw in ["violation", "fail", "does not meet", "below minimum", "non-compliant"]
                )
                engine_pass = result["status"] == "PASS"

                # Guardrail: if LLM contradicts rule engine, discard LLM
                if engine_pass and llm_says_fail:
                    self.audit.log(
                        agent=self.NAME,
                        action="guardrail_override",
                        reasoning=[
                            "LLM reasoning contradicted the deterministic rule engine.",
                            f"Rule engine says PASS, LLM suggested FAIL.",
                            "Discarding LLM output and using deterministic reasoning.",
                        ],
                        result="LLM_OVERRIDDEN",
                        confidence=0.5,
                    )
                    return None

                if not engine_pass and llm_says_pass and not llm_says_fail:
                    self.audit.log(
                        agent=self.NAME,
                        action="guardrail_override",
                        reasoning=[
                            "LLM reasoning contradicted the deterministic rule engine.",
                            f"Rule engine says FAIL, LLM suggested PASS.",
                            "Discarding LLM output and using deterministic reasoning.",
                        ],
                        result="LLM_OVERRIDDEN",
                        confidence=0.5,
                    )
                    return None

                return lines

        except Exception:
            pass

        return None

    def _build_prompt(self, result: dict, city: str) -> str:
        """Build the Gemini prompt for reasoning generation."""
        room = result["room_name"]
        w = result["width_ft"]
        l = result["length_ft"]
        area = result["area_sqft"]
        status = result["status"]
        reason = result.get("reason", "")
        code_ref = result.get("code_reference", "")
        req_area = result.get("required_area_sqft", "N/A")
        fix = result.get("suggested_fix", "")

        return f"""You are a building compliance auditor for {city}. 
Generate a step-by-step reasoning chain (4-6 numbered steps) for the following room compliance check.
Be concise. Each step should be one sentence. Use actual numbers.

Room: {room}
Dimensions: {w} ft × {l} ft
Calculated Area: {area} sq ft
Required Minimum Area: {req_area} sq ft
Applicable Regulation: {code_ref if code_ref else 'General residential building standards'}
Rule Engine Verdict: {status}
{f'Violation Reason: {reason}' if reason and status == 'FAIL' else ''}
{f'Suggested Fix: {fix}' if fix else ''}

Output ONLY the numbered steps, nothing else. Example format:
Step 1: Identified room "Kitchen" with dimensions 7.4 × 6.4 ft.
Step 2: Calculated area = 7.4 × 6.4 = 47.4 sq ft.
Step 3: Applied Delhi Building Bye-Laws 2016 — Kitchen minimum = 50 sq ft.
Step 4: 47.4 sq ft < 50 sq ft → VIOLATION detected.
Step 5: Recommended fix: Increase length by 0.4 ft to achieve 50 sq ft."""

    @staticmethod
    def _deterministic_reasoning(result: dict, city: str) -> list[str]:
        """Generate a template-based reasoning chain (no LLM needed)."""
        room = result["room_name"]
        w = result["width_ft"]
        l = result["length_ft"]
        area = result["area_sqft"]
        status = result["status"]
        req_area = result.get("required_area_sqft")
        code_ref = result.get("code_reference", "")
        fix = result.get("suggested_fix", "")

        steps = [
            f'Step 1: Identified room "{room}" with dimensions {w} × {l} ft.',
            f"Step 2: Calculated area = {w} × {l} = {area} sq ft.",
        ]

        if code_ref:
            steps.append(f"Step 3: Applied regulation — {code_ref[:80]}…")

        if status == "PASS":
            if req_area:
                steps.append(
                    f"Step {len(steps)+1}: Area {area} sq ft ≥ required {req_area} sq ft — COMPLIANT."
                )
            else:
                steps.append(f"Step {len(steps)+1}: No specific area requirement — COMPLIANT.")
        elif status == "FAIL":
            steps.append(f"Step {len(steps)+1}: {result.get('reason', 'Violation detected')}.")
            if fix:
                steps.append(f"Step {len(steps)+1}: Recommended fix — {fix}")
        elif status == "INSUFFICIENT_DATA":
            steps.append(f"Step {len(steps)+1}: Dimensions missing — cannot determine compliance.")
        else:
            steps.append(f"Step {len(steps)+1}: No matching regulation found for this room type.")

        return steps

    # ── Cross-room validation ────────────────────────────────────────

    def _cross_room_validation(self, results: list[dict], city: str) -> list[str]:
        """
        Validate across rooms (not just individual compliance).
        Catches issues a single-room check would miss.
        """
        flags = []

        # Check: at least one bedroom
        bedrooms = [r for r in results if "bedroom" in r["room_name"].lower() or "guest" in r["room_name"].lower()]
        if not bedrooms:
            flags.append("No bedroom detected — is this a studio apartment or commercial space?")

        # Check: at least one toilet/bathroom
        toilets = [r for r in results if any(kw in r["room_name"].lower() for kw in ["toilet", "bath", "wash", "wc"])]
        if not toilets:
            flags.append("No toilet/bathroom detected — this may be a compliance issue.")

        # Check: at least one kitchen
        kitchens = [r for r in results if "kitchen" in r["room_name"].lower()]
        if not kitchens:
            flags.append("No kitchen detected — residential units typically require one.")

        # Log cross-room validation
        if flags:
            self.audit.log(
                agent=self.NAME,
                action="cross_room_validation",
                reasoning=[
                    f"Cross-room analysis found {len(flags)} warning(s).",
                    *flags,
                ],
                result={"warnings": flags},
                confidence=0.8,
            )

        return flags

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _result_confidence(result: dict) -> float:
        """Confidence in a compliance result based on data quality."""
        w = result.get("width_ft", 0) or 0
        l = result.get("length_ft", 0) or 0
        if w > 0 and l > 0 and result["status"] in ("PASS", "FAIL"):
            return 0.95
        if result["status"] == "INSUFFICIENT_DATA":
            return 0.3
        return 0.6

    @staticmethod
    def _status(message: str, ok: bool = False) -> dict:
        status = "ok" if ok else "running"
        return {"agent": ComplianceAgent.NAME, "message": message, "status": status}
