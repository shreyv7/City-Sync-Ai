"""
Extracts text from PDF files.
Primary: pdfplumber (for PDFs with selectable text).
Fallback: pytesseract OCR (for PDFs with custom/embedded fonts).
"""

import pdfplumber


def extract_text_from_pdf(file_obj):
    """
    Extracts text from all pages of a PDF file using pdfplumber.

    Returns:
        str: Concatenated text from all pages, or empty string if none found.
    """
    try:
        with pdfplumber.open(file_obj) as pdf:
            if not pdf.pages:
                return ""

            all_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    all_text.append(f"--- Page {i + 1} ---\n{text}")

            return "\n\n".join(all_text) if all_text else ""
    except Exception:
        return ""


def is_garbled_text(text):
    """Check if pdfplumber text is garbled (CID font encoding)."""
    if not text:
        return True
    return text.count("(cid:") > 5


def extract_text_via_ocr(image):
    """
    Extract text from a PIL Image using Tesseract OCR.

    Args:
        image: A PIL Image object (e.g. from pdf2image).

    Returns:
        str: OCR-extracted text, or empty string on failure.
    """
    try:
        import pytesseract
        return pytesseract.image_to_string(image)
    except Exception:
        return ""
