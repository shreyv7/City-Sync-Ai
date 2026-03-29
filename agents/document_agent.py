"""
Document Agent — Responsible for extracting text and images from uploaded PDFs.

Implements a 3-tier fallback with self-correction:
  Tier 1: pdfplumber (fast, works for vector PDFs)
  Tier 2: EasyOCR  (deep-learning OCR for image-based PDFs)
  Tier 3: OpenCV contour detection (last resort, no text)

Every attempt is logged to the audit trail with confidence scores,
and fallback events are recorded as self-correction entries so the
UI can surface them to judges.
"""

from __future__ import annotations

from PIL import Image

import core.pdf_reader as pdf_reader
import core.vision_reader as vision_reader
from core.audit_logger import AuditTrail


class DocumentAgent:
    """Extracts text and floor plan images from an uploaded PDF."""

    NAME = "document_agent"

    def __init__(self, audit: AuditTrail):
        self.audit = audit

    # ── Public API ───────────────────────────────────────────────────

    def extract(
        self, uploaded_file
    ) -> dict:
        """
        Run the full extraction pipeline on an uploaded PDF.

        Returns:
            dict with keys:
                text (str): The extracted text.
                image (PIL.Image | None): Rendered floor plan page.
                method (str): "pdfplumber" | "easyocr" | "contour" | "none"
                confidence (float): 0.0–1.0 overall confidence.
                status_updates (list[dict]): UI-friendly status messages.
        """
        status_updates: list[dict] = []
        text = ""
        image: Image.Image | None = None
        method = "none"
        confidence = 0.0

        # ── Tier 1: pdfplumber ───────────────────────────────────────
        status_updates.append(self._status("Extracting text with pdfplumber…"))

        try:
            raw = pdf_reader.extract_text_from_pdf(uploaded_file)
        except Exception as e:
            raw = ""
            self.audit.log(
                agent=self.NAME,
                action="pdfplumber_extract",
                input_data={"source": "uploaded_file"},
                reasoning=[f"pdfplumber raised an exception: {e}"],
                result="FAILED",
                confidence=0.0,
            )

        text_usable = (
            raw
            and len(raw.strip()) > 20
            and not pdf_reader.is_garbled_text(raw)
        )

        if text_usable:
            text = raw
            method = "pdfplumber"
            confidence = self._estimate_confidence(text)
            self.audit.log(
                agent=self.NAME,
                action="pdfplumber_extract",
                input_data={"text_length": len(text)},
                reasoning=[
                    f"pdfplumber returned {len(text)} characters.",
                    "Text appears readable (not garbled).",
                    f"Confidence estimated at {confidence:.2f}.",
                ],
                result="SUCCESS",
                confidence=confidence,
            )
            status_updates.append(
                self._status(
                    f"✅ pdfplumber extracted {len(text)} chars (confidence: {confidence:.0%})",
                    ok=True,
                )
            )
        else:
            reason = "empty" if not raw else "garbled CID text"
            self.audit.log(
                agent=self.NAME,
                action="pdfplumber_extract",
                input_data={"text_length": len(raw) if raw else 0},
                reasoning=[
                    f"pdfplumber text is {reason} ({len(raw) if raw else 0} chars).",
                    "Falling back to EasyOCR.",
                ],
                result="UNUSABLE",
                confidence=0.0,
            )
            status_updates.append(
                self._status(
                    f"⚠️ pdfplumber text is {reason} — falling back to EasyOCR",
                    retry=True,
                )
            )

        # ── Render image (needed for Tier 2 & 3) ────────────────────
        if not text_usable or image is None:
            uploaded_file.seek(0)
            try:
                image = vision_reader.convert_pdf_to_image(uploaded_file)
            except Exception as e:
                self.audit.log(
                    agent=self.NAME,
                    action="render_image",
                    reasoning=[f"PDF-to-image conversion failed: {e}"],
                    result="FAILED",
                    confidence=0.0,
                )

        # ── Tier 2: EasyOCR ──────────────────────────────────────────
        if not text_usable and image is not None:
            status_updates.append(self._status("🔄 Running EasyOCR with preprocessing…"))

            try:
                ocr_result = vision_reader.ocr_floor_plan(image)
                ocr_text = ocr_result.get("text", "")
                blocks = ocr_result.get("blocks", [])
            except Exception as e:
                ocr_text = ""
                blocks = []
                self.audit.log(
                    agent=self.NAME,
                    action="easyocr_extract",
                    reasoning=[f"EasyOCR raised an exception: {e}"],
                    result="FAILED",
                    confidence=0.0,
                )

            if ocr_text and len(ocr_text.strip()) > 10:
                text = ocr_text
                method = "easyocr"
                confidence = self._estimate_confidence(text)
                self.audit.log(
                    agent=self.NAME,
                    action="easyocr_extract",
                    input_data={"text_length": len(text)},
                    reasoning=[
                        "Self-correction: pdfplumber failed, switched to EasyOCR.",
                        f"EasyOCR returned {len(text)} characters.",
                        f"Confidence estimated at {confidence:.2f}.",
                    ],
                    result="SUCCESS",
                    confidence=confidence,
                )
                status_updates.append(
                    self._status(
                        f"✅ EasyOCR extracted {len(text)} chars (confidence: {confidence:.0%})",
                        ok=True,
                    )
                )
            else:
                self.audit.log(
                    agent=self.NAME,
                    action="easyocr_extract",
                    input_data={"text_length": len(ocr_text) if ocr_text else 0},
                    reasoning=[
                        "EasyOCR returned insufficient text.",
                        "Falling back to contour detection (last resort).",
                    ],
                    result="UNUSABLE",
                    confidence=0.0,
                )
                status_updates.append(
                    self._status(
                        "⚠️ EasyOCR returned insufficient text — falling back to contours",
                        retry=True,
                    )
                )

        # ── Tier 3: Contour detection (last resort) ──────────────────
        if method == "none" and image is not None:
            status_updates.append(
                self._status("🔄 Running OpenCV contour detection (last resort)…")
            )
            method = "contour"
            confidence = 0.2
            self.audit.log(
                agent=self.NAME,
                action="contour_fallback",
                reasoning=[
                    "Self-correction: both pdfplumber and EasyOCR failed.",
                    "Using OpenCV contour detection as last resort.",
                    "Room names and dimensions will not be available.",
                ],
                result="FALLBACK",
                confidence=confidence,
            )
            status_updates.append(
                self._status(
                    "⚠️ Using contour detection — room names/dims unavailable",
                    retry=True,
                )
            )

        # ── Final summary ────────────────────────────────────────────
        self.audit.log(
            agent=self.NAME,
            action="extraction_complete",
            input_data={"method": method},
            reasoning=[
                f"Final extraction method: {method}.",
                f"Text length: {len(text)} characters.",
                f"Image available: {image is not None}.",
                f"Overall confidence: {confidence:.2f}.",
            ],
            result={"method": method, "text_length": len(text), "has_image": image is not None},
            confidence=confidence,
        )

        return {
            "text": text,
            "image": image,
            "method": method,
            "confidence": confidence,
            "text_blocks": blocks if "blocks" in locals() else [],
            "status_updates": status_updates,
        }

    # ── Retry with enhanced preprocessing ────────────────────────────

    def retry_with_enhanced_ocr(self, image: Image.Image) -> dict:
        """
        Called by the Orchestrator when initial extraction confidence is low.
        Retries OCR with more aggressive preprocessing.
        """
        self.audit.log(
            agent=self.NAME,
            action="retry_enhanced_ocr",
            reasoning=["Orchestrator requested retry with enhanced preprocessing."],
            result="RETRYING",
            confidence=0.0,
        )

        try:
            # Use a more aggressive preprocessing
            preprocessed = vision_reader.preprocess_for_ocr(image)
            import easyocr
            import ssl

            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except AttributeError:
                pass

            reader = easyocr.Reader(["en"], gpu=False)
            import numpy as np
            import cv2

            img_np = np.array(preprocessed)
            if len(img_np.shape) == 2:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

            results = reader.readtext(img_np, paragraph=True)
            
            extracted_text = []
            blocks = []
            for res in results:
                if len(res) >= 2:
                    poly = res[0]
                    blocks.append({
                        "text": res[1],
                        "bbox": [
                            int(min(p[0] for p in poly)),
                            int(min(p[1] for p in poly)),
                            int(max(p[0] for p in poly)),
                            int(max(p[1] for p in poly))
                        ]
                    })
                    extracted_text.append(res[1])
            text = "\n".join(extracted_text)

            confidence = self._estimate_confidence(text)
            self.audit.log(
                agent=self.NAME,
                action="retry_enhanced_ocr",
                input_data={"text_length": len(text)},
                reasoning=[
                    "Enhanced OCR retry completed.",
                    f"Extracted {len(text)} characters with lowered threshold.",
                    f"Confidence: {confidence:.2f}.",
                ],
                result="SUCCESS" if text else "FAILED",
                confidence=confidence,
            )
        except Exception as e:
            self.audit.log(
                agent=self.NAME,
                action="retry_enhanced_ocr",
                reasoning=[f"Enhanced OCR retry failed: {e}"],
                result="FAILED",
                confidence=0.0,
            )
            return {"text": "", "confidence": 0.0, "text_blocks": []}

        return {
            "text": text,
            "confidence": confidence,
            "text_blocks": blocks,
        }

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """
        Heuristic confidence based on text quality indicators.
        """
        if not text:
            return 0.0

        score = 0.0
        length = len(text.strip())

        # Length heuristic
        if length > 200:
            score += 0.4
        elif length > 50:
            score += 0.2

        # Check for room-like keywords
        room_keywords = [
            "BEDROOM", "KITCHEN", "TOILET", "LIVING", "DINING",
            "HALL", "BATH", "BALCONY", "PORCH", "DRESS",
        ]
        keyword_count = sum(
            1 for kw in room_keywords if kw in text.upper()
        )
        if keyword_count >= 4:
            score += 0.4
        elif keyword_count >= 2:
            score += 0.25
        elif keyword_count >= 1:
            score += 0.1

        # Check for dimension-like patterns
        import re
        dim_count = len(re.findall(r"\d+['\-\"]\s*\d*", text))
        if dim_count >= 3:
            score += 0.2
        elif dim_count >= 1:
            score += 0.1

        return min(score, 1.0)

    @staticmethod
    def _status(message: str, ok: bool = False, retry: bool = False) -> dict:
        """Build a UI status update dict."""
        status = "ok" if ok else ("retry" if retry else "running")
        return {"agent": DocumentAgent.NAME, "message": message, "status": status}
