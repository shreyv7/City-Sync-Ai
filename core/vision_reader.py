"""
Vision processing for floor plan PDFs.
- Converts PDF pages to images.
- Preprocesses images for better OCR accuracy.
- Detects potential room regions via contour detection.
- Annotates floor plan images with compliance results.
"""

from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2
import numpy as np
import io


def convert_pdf_to_image(file_obj, page: int = 1) -> Image.Image:
    """
    Converts a specific page of a PDF file to a PIL Image.

    Args:
        file_obj: The PDF file object (bytes-like).
        page: The 1-indexed page number to convert.

    Returns:
        Image.Image: The requested page as an image.
    """
    try:
        if hasattr(file_obj, 'getvalue'):
            file_bytes = file_obj.getvalue()
        else:
            file_bytes = file_obj.read()
            file_obj.seek(0)

        images = convert_from_bytes(file_bytes, first_page=page, last_page=page, dpi=300)

        if images:
            return images[0]
        else:
            raise Exception("No images converted from PDF.")
    except Exception as e:
        raise Exception(f"Failed to convert PDF to image: {str(e)}")


def convert_pdf_to_all_images(file_obj) -> list[Image.Image]:
    """Converts all pages of a PDF to a list of PIL Images."""
    try:
        if hasattr(file_obj, 'getvalue'):
            file_bytes = file_obj.getvalue()
        else:
            file_bytes = file_obj.read()
            file_obj.seek(0)

        images = convert_from_bytes(file_bytes, dpi=300)
        return images if images else []
    except Exception:
        return []


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocesses a floor plan image to maximise OCR accuracy.

    Steps:
    1. Convert to grayscale
    2. Upscale small images (helps Tesseract)
    3. Enhance contrast & sharpness
    4. Apply adaptive thresholding for clean black/white text

    Returns:
        A preprocessed PIL Image ready for Tesseract.
    """
    # Work with OpenCV for preprocessing
    cv_img = np.array(image)
    if len(cv_img.shape) == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
    else:
        gray = cv_img

    # Upscale if the image is small (below 2000px wide)
    h, w = gray.shape[:2]
    if w < 2000:
        scale = 2000 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold to get clean binary text
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
    )

    return Image.fromarray(binary)


def ocr_floor_plan(image: Image.Image) -> str:
    """
    Runs OCR on a floor plan image with preprocessing for best results.
    Uses EasyOCR for robust deep-learning-based text recognition.

    Args:
        image: The floor plan PIL Image.

    Returns:
        dict: containing 'text' (the full extracted string) and 'blocks' (list of dicts with text and bbox).
    """
    try:
        import easyocr
        import ssl
    except ImportError:
        return ""

    preprocessed = preprocess_for_ocr(image)

    try:
        # Fix macOS SSL issues where Python cannot download EasyOCR models
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        # Initialize EasyOCR reader (it downloads models on first run if needed)
        reader = easyocr.Reader(['en'], gpu=False)
        
        # EasyOCR works directly with numpy arrays
        img_np = np.array(preprocessed)
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

        # Extract text using paragraph mode to group spatially close words into blocks
        results = reader.readtext(img_np, paragraph=True)
        
        # Combine extracted lines and store blocks
        extracted_text = []
        text_blocks = []
        for res in results:
            if len(res) >= 2:
                # res[0] is [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                # We extract the bounding box [min_x, min_y, max_x, max_y]
                poly = res[0]
                min_x = min(p[0] for p in poly)
                min_y = min(p[1] for p in poly)
                max_x = max(p[0] for p in poly)
                max_y = max(p[1] for p in poly)
                
                text = res[1]
                extracted_text.append(text)
                text_blocks.append({
                    "text": text,
                    "bbox": [int(min_x), int(min_y), int(max_x), int(max_y)]
                })
                
        return {
            "text": "\n".join(extracted_text),
            "blocks": text_blocks
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"OCR Error: {e}")
        return {"text": "", "blocks": []}


def detect_rooms(image: Image.Image) -> list[dict]:
    """
    Detects potential rooms in a floor plan image using contour detection.

    Returns:
        list[dict]: Detected rooms with placeholder dimensions and bounding rects.
    """
    open_cv_image = np.array(image)
    open_cv_image = open_cv_image[:, :, ::-1].copy()

    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_proposals = []
    room_counter = 1

    total_img_area = open_cv_image.shape[0] * open_cv_image.shape[1]
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        # A room typically occupies at least 1.5% of the total floor plan image area
        min_area = total_img_area * 0.015

        if area > min_area:
            detected_proposals.append({
                "room_name": f"Suggested Room {room_counter}",
                "width_ft": 0,
                "length_ft": 0,
                "_bbox": (x, y, w, h)  # internal use for annotation
            })
            room_counter += 1

    if not detected_proposals:
        return [{"room_name": "Room 1", "width_ft": 0, "length_ft": 0}]

    return detected_proposals


# ─── Status → Color mapping ────────────────────────────────────────────
_STATUS_COLORS = {
    "PASS": (46, 204, 113),        # green
    "FAIL": (231, 76, 60),         # red
    "NOT_APPLICABLE": (149, 165, 166),  # grey
    "INSUFFICIENT_DATA": (241, 196, 15) # yellow
}


def annotate_floor_plan(image: Image.Image, compliance_results: list[dict]) -> Image.Image:
    """
    Draws a lightweight compliance legend overlay onto the floor plan image.
    Because room bounding boxes from contour detection rarely map 1-to-1
    to real rooms, we overlay a results legend instead of arbitrary boxes.

    Args:
        image: The original floor plan PIL Image.
        compliance_results: List of dicts from the rule engine.

    Returns:
        PIL Image with an annotation overlay.
    """
    img = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to get a reasonable font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    # Legend box in top-right corner
    padding = 12
    line_height = 22
    max_label_width = 300
    box_height = padding * 2 + line_height * (len(compliance_results) + 1)
    box_width = max_label_width + padding * 2

    x0 = img.width - box_width - 20
    y0 = 20

    # Semi-transparent background
    draw.rectangle(
        [x0, y0, x0 + box_width, y0 + box_height],
        fill=(30, 30, 30, 200)
    )

    # Title
    draw.text((x0 + padding, y0 + padding), "Compliance Summary", fill=(255, 255, 255, 255), font=font)

    # One line per room
    for i, room in enumerate(compliance_results):
        yy = y0 + padding + line_height * (i + 1)
        status = room.get("status", "NOT_APPLICABLE")
        color = _STATUS_COLORS.get(status, (149, 165, 166))

        # Status dot
        dot_x = x0 + padding
        dot_y = yy + 5
        draw.ellipse([dot_x, dot_y, dot_x + 10, dot_y + 10], fill=(*color, 255))

        # Room label
        label = f"{room['room_name']}: {status}"
        draw.text((dot_x + 16, yy), label[:40], fill=(255, 255, 255, 255), font=font_small)

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")
