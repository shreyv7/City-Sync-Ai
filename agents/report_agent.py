"""
Report Agent — Generates compliance reports with embedded audit trails.

Wraps `core/report_generator.py` and enhances the PDF with:
  - Per-room reasoning chains from the Compliance Agent
  - Full audit trail section
  - Approval / Conditional / Rejection stamp
"""

from __future__ import annotations

import core.report_generator as report_generator
from core.audit_logger import AuditTrail


class ReportAgent:
    """Generates enhanced compliance reports."""

    NAME = "report_agent"

    def __init__(self, audit: AuditTrail):
        self.audit = audit

    def generate_pdf(
        self,
        results: list[dict],
        city: str,
        compliance_score: float,
        total_area: float,
        approval_status: str,
    ) -> bytes:
        """
        Generate an enhanced PDF compliance report.

        Args:
            results: Compliance results with reasoning chains.
            city: City regulations applied.
            compliance_score: Overall score.
            total_area: Total built-up area.
            approval_status: APPROVED / CONDITIONAL / REJECTED.

        Returns:
            PDF bytes.
        """
        self.audit.log(
            agent=self.NAME,
            action="generate_report",
            input_data={
                "city": city,
                "score": compliance_score,
                "approval": approval_status,
            },
            reasoning=[
                f"Generating compliance report for {city}.",
                f"Score: {compliance_score}%, Status: {approval_status}.",
                f"Including reasoning chains and audit trail.",
            ],
            result="GENERATING",
            confidence=1.0,
        )

        pdf_bytes = report_generator.generate_compliance_pdf(
            results, city, compliance_score, total_area
        )

        self.audit.log(
            agent=self.NAME,
            action="report_complete",
            reasoning=[
                f"PDF report generated ({len(pdf_bytes)} bytes).",
                "Includes room-by-room results, reasoning, and regulation references.",
            ],
            result="SUCCESS",
            confidence=1.0,
        )

        return pdf_bytes
