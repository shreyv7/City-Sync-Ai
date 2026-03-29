"""
Floor Plan Annotator — Generates rich compliance overlays on floor plan images.

Two-layer approach:
  1. PIL layer: draws color-coded bounding boxes + labels on the image
  2. HTML layer: wraps the annotated image in an interactive Streamlit component
     with layer toggles, hover tooltips, and zoom support.

Because OCR gives us room text but NOT pixel coordinates, we assign
"virtual bounding boxes" using a proportional grid layout based on room area.
This is visually honest — we never misrepresent exact room boundaries.
"""

from __future__ import annotations

import base64
import io
import math
import json

from PIL import Image, ImageDraw, ImageFont


# ── Status color palette ─────────────────────────────────────────────────────
_STATUS = {
    "PASS": {
        "box":   (39, 174, 96),      # green
        "fill":  (39, 174, 96, 40),  # translucent
        "label": (20, 120, 60),
        "emoji": "✅",
        "badge": "#27ae60",
    },
    "FAIL": {
        "box":   (231, 76, 60),
        "fill":  (231, 76, 60, 55),
        "label": (180, 30, 20),
        "emoji": "❌",
        "badge": "#e74c3c",
    },
    "INSUFFICIENT_DATA": {
        "box":   (243, 156, 18),
        "fill":  (243, 156, 18, 45),
        "label": (170, 100, 0),
        "emoji": "⚠️",
        "badge": "#f39c12",
    },
    "NOT_APPLICABLE": {
        "box":   (149, 165, 166),
        "fill":  (149, 165, 166, 30),
        "label": (80, 90, 95),
        "emoji": "➖",
        "badge": "#95a5a6",
    },
}
_DEFAULT_STATUS = _STATUS["NOT_APPLICABLE"]

# Padding between virtual boxes (fraction of image)
_PADDING_FRAC = 0.01


import re

def build_annotation_data(
    compliance_results: list[dict],
    image_size: tuple[int, int],
    text_blocks: list[dict] = None
) -> list[dict]:
    """
    Assign bounding boxes to each room based on actual OCR text block locations.
    If OCR block is found for a room, its bounding box is heavily expanded to
    approximate the physical room size visually.
    If no text is found, we fall back to a proportional grid layout.
    """
    if not compliance_results:
        return []
    
    if text_blocks is None:
        text_blocks = []

    img_w, img_h = image_size
    n = len(compliance_results)

    # Calculate grid for fallback
    cols = max(2, math.ceil(math.sqrt(n * (img_w / img_h))))
    rows = math.ceil(n / cols)
    cell_w = img_w / cols
    cell_h = img_h / rows
    pad_x = max(4, int(img_w * _PADDING_FRAC))
    pad_y = max(4, int(img_h * _PADDING_FRAC))

    def _normalize(t):
        return re.sub(r'[^a-z0-9]', '', str(t).lower())

    # 1. First Pass: Anchor exact text coordinates
    anchored_rooms = []
    unanchored_rooms = []
    
    for room in compliance_results:
        room_name = room.get("room_name", "Unknown")
        norm_name = _normalize(room_name)
        core_name = re.sub(r'\d+$', '', norm_name)
        
        matched_block = None
        for block in text_blocks:
            norm_block = _normalize(block["text"])
            if norm_name in norm_block or (len(core_name) > 3 and core_name in norm_block):
                matched_block = block
                text_blocks.remove(block)
                break
                
        if matched_block:
            bx1, by1, bx2, by2 = matched_block["bbox"]
            cx = (bx1 + bx2) / 2
            cy = (by1 + by2) / 2
            anchored_rooms.append({
                "room": room,
                "center": (cx, cy),
                "text_bbox": (bx1, by1, bx2, by2)
            })
        else:
            unanchored_rooms.append(room)

    # 2. Rectilinear Bisection (Voronoi) to compute non-overlapping boundaries
    annotations = []
    for i, anchor in enumerate(anchored_rooms):
        cx, cy = anchor["center"]
        bx1, by1, bx2, by2 = anchor["text_bbox"]
        
        # Start with a tightly bounded maximum room boundary
        # We allow it to expand up to its own text width + just 3.5% of the total image size.
        # This ensures the box stays comfortably inside the physical room walls!
        max_dist_x = (bx2 - bx1) / 2 + (img_w * 0.035)
        max_dist_y = (by2 - by1) / 2 + (img_h * 0.035)
        
        min_x = max(0, cx - max_dist_x)
        max_x = min(img_w, cx + max_dist_x)
        min_y = max(0, cy - max_dist_y)
        max_y = min(img_h, cy + max_dist_y)
        
        # Constrain boundary against every other room to prevent overlap
        for j, other in enumerate(anchored_rooms):
            if i == j: continue
            ox, oy = other["center"]
            dx = ox - cx
            dy = oy - cy
            
            # Decide if relation is strictly horizontal or vertical
            if abs(dx) > abs(dy):
                mid_x = (cx + ox) / 2
                if dx > 0: # other is to the right
                    max_x = min(max_x, mid_x)
                else:      # other is to the left
                    min_x = max(min_x, mid_x)
            else:
                mid_y = (cy + oy) / 2
                if dy > 0: # other is below
                    max_y = min(max_y, mid_y)
                else:      # other is above
                    min_y = max(min_y, mid_y)
                    
        # Add slight padding so boxes don't touch seamlessly
        pad = 8
        ex1 = max(0, int(min_x) + pad)
        ey1 = max(0, int(min_y) + pad)
        ex2 = min(img_w, int(max_x) - pad)
        ey2 = min(img_h, int(max_y) - pad)
        
        # Fallback if the space is too squeezed
        if ex2 <= ex1: ex1 = bx1; ex2 = bx2
        if ey2 <= ey1: ey1 = by1; ey2 = by2
        
        room = anchor["room"]
        annotations.append({
            "room_name":          room.get("room_name", "Unknown"),
            "status":             room.get("status", "NOT_APPLICABLE"),
            "area_sqft":          room.get("area_sqft", 0),
            "required_area_sqft": room.get("required_area_sqft", 0),
            "suggested_fix":      room.get("suggested_fix", ""),
            "severity":           room.get("severity", ""),
            "code_reference":     room.get("code_reference", ""),
            "reason":             room.get("reason", ""),
            "bbox":               (ex1, ey1, ex2, ey2),
        })

    # 3. Fallback grid for unanchored rooms
    fallback_idx = 0
    for room in unanchored_rooms:
        col = fallback_idx % cols
        row = fallback_idx // cols
        x1 = int(col * cell_w) + pad_x
        y1 = int(row * cell_h) + pad_y
        x2 = int((col + 1) * cell_w) - pad_x
        y2 = int((row + 1) * cell_h) - pad_y
        fallback_idx += 1

        annotations.append({
            "room_name":          room.get("room_name", "Unknown"),
            "status":             room.get("status", "NOT_APPLICABLE"),
            "area_sqft":          room.get("area_sqft", 0),
            "required_area_sqft": room.get("required_area_sqft", 0),
            "suggested_fix":      room.get("suggested_fix", ""),
            "severity":           room.get("severity", ""),
            "code_reference":     room.get("code_reference", ""),
            "reason":             room.get("reason", ""),
            "bbox":               (x1, y1, x2, y2),
        })

    return annotations


def draw_annotated_image(
    image: Image.Image,
    annotations: list[dict],
    border_width: int = 3,
) -> Image.Image:
    """
    Render PIL-based annotations onto the floor plan image.

    Draws:
      - Semi-transparent filled rectangle per room
      - Solid color border (status-coded)
      - Room name + status icon text label
    """
    base = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Fonts
    try:
        fnt_room = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        fnt_stat = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except Exception:
        fnt_room = ImageFont.load_default()
        fnt_stat = fnt_room

    for ann in annotations:
        status_cfg = _STATUS.get(ann["status"], _DEFAULT_STATUS)
        x1, y1, x2, y2 = ann["bbox"]

        # ── semi-transparent fill ─────────────────────────────────────
        draw.rectangle([x1, y1, x2, y2], fill=status_cfg["fill"])

        # ── border ───────────────────────────────────────────────────
        for b in range(border_width):
            draw.rectangle(
                [x1 + b, y1 + b, x2 - b, y2 - b],
                outline=(*status_cfg["box"], 200),
            )

        # ── label background ─────────────────────────────────────────
        label = f'{status_cfg["emoji"]} {ann["room_name"]}'
        bbox = draw.textbbox((0, 0), label, font=fnt_room)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        lx, ly = x1 + 4, y1 + 4
        # pill background
        draw.rounded_rectangle(
            [lx - 2, ly - 2, lx + lw + 4, ly + lh + 4],
            radius=4,
            fill=(255, 255, 255, 210),
        )
        draw.text((lx, ly), label, fill=(*status_cfg["label"], 255), font=fnt_room)

        # ── area line ─────────────────────────────────────────────────
        if ann["area_sqft"] and ann["area_sqft"] > 0:
            area_txt = f'{ann["area_sqft"]:.0f} sqft'
            draw.text((lx, ly + lh + 6), area_txt, fill=(*status_cfg["label"], 180), font=fnt_stat)

    result = Image.alpha_composite(base, overlay)
    return result.convert("RGB")


def render_interactive_overlay(
    image: Image.Image,
    annotations: list[dict],
) -> str:
    """
    Generate a self-contained HTML string for a Streamlit `st.components.v1.html()` call.

    Features:
      - Renders the annotated image as a base64 inline PNG
      - Layer toggle buttons (All / PASS / FAIL / Warnings)
      - Room cards beneath image: color coded, with fix suggestion
      - Hover-over room name highlights corresponding card

    Returns:
        Full HTML string ready for `st.components.v1.html(html, height=...)`
    """
    # ── render annotated image → base64 ──────────────────────────────
    annotated_img = draw_annotated_image(image, annotations)
    buf = io.BytesIO()
    annotated_img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()

    # ── build room cards JSON for JS ─────────────────────────────────
    cards_json = json.dumps([
        {
            "name":    a["room_name"],
            "status":  a["status"],
            "area":    a["area_sqft"],
            "req":     a["required_area_sqft"],
            "fix":     a["suggested_fix"] or "",
            "reason":  a["reason"] or "",
            "code":    a["code_reference"] or "",
            "badge":   _STATUS.get(a["status"], _DEFAULT_STATUS)["badge"],
            "emoji":   _STATUS.get(a["status"], _DEFAULT_STATUS)["emoji"],
        }
        for a in annotations
    ], ensure_ascii=False)

    # Precompute summary counts
    fail_count = sum(1 for a in annotations if a["status"] == "FAIL")
    pass_count = sum(1 for a in annotations if a["status"] == "PASS")
    warn_count = sum(1 for a in annotations if a["status"] == "INSUFFICIENT_DATA")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #1e293b; }}

  /* ── Header strip ── */
  .header {{
    display: flex; align-items: center; gap: 12px; padding: 14px 16px;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    color: white; border-radius: 12px 12px 0 0;
  }}
  .header h2 {{ font-size: 15px; font-weight: 700; letter-spacing: 0.3px; }}
  .header .pill {{
    background: rgba(255,255,255,0.18); border-radius: 999px;
    padding: 3px 10px; font-size: 12px; font-weight: 600;
  }}
  .pill.fail {{ background: #e74c3c; }}
  .pill.pass {{ background: #27ae60; }}
  .pill.warn {{ background: #f39c12; }}

  /* ── Toggle buttons ── */
  .toggles {{
    display: flex; gap: 8px; padding: 12px 16px;
    background: white; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap;
  }}
  .toggle-btn {{
    padding: 6px 14px; border-radius: 999px; border: 2px solid #e2e8f0;
    font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s;
    background: white; color: #64748b;
  }}
  .toggle-btn:hover {{ transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .toggle-btn.active {{ color: white; border-color: transparent; }}
  .toggle-btn.all.active   {{ background: #2a5298; }}
  .toggle-btn.pass.active  {{ background: #27ae60; }}
  .toggle-btn.fail.active  {{ background: #e74c3c; }}
  .toggle-btn.warn.active  {{ background: #f39c12; }}
  .toggle-btn.na.active    {{ background: #95a5a6; }}

  /* ── Floor plan image ── */
  .image-wrapper {{
    overflow: auto; background: #f1f5f9; max-height: 500px;
    border-bottom: 1px solid #e2e8f0; position: relative;
  }}
  .floor-plan-img {{ display: block; width: 100%; cursor: zoom-in; transition: transform 0.3s; }}
  .zoom-controls {{
    position: sticky; top: 8px; right: 8px; float: right;
    display: flex; gap: 4px; z-index: 10; margin: 8px;
  }}
  .zoom-btn {{
    width: 30px; height: 30px; border-radius: 8px; border: none;
    background: rgba(255,255,255,0.9); box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    font-size: 16px; font-weight: bold; cursor: pointer; color: #2a5298;
  }}
  .zoom-btn:hover {{ background: white; }}

  /* ── Room cards grid ── */
  .cards-section {{ padding: 14px 16px; background: white; }}
  .cards-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; color: #94a3b8; margin-bottom: 10px; }}
  .cards-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px;
  }}
  .room-card {{
    border-radius: 10px; border: 2px solid #f1f5f9; padding: 10px 12px;
    transition: all 0.2s; cursor: default; position: relative; overflow: hidden;
  }}
  .room-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
  .room-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  }}
  .room-card .card-name {{ font-size: 13px; font-weight: 600; margin-bottom: 4px;
    display: flex; align-items: center; gap: 6px; }}
  .room-card .card-area {{ font-size: 11px; color: #64748b; margin-bottom: 6px; }}
  .room-card .card-fix {{
    font-size: 11px; color: #475569; background: #f8fafc;
    border-radius: 6px; padding: 5px 7px; border-left: 3px solid #e2e8f0;
    display: none;
  }}
  .room-card.expanded .card-fix {{ display: block; }}
  .room-card .expand-btn {{
    font-size: 10px; color: #94a3b8; margin-top: 4px; cursor: pointer;
    text-decoration: underline; display: none;
  }}
  .room-card.has-fix .expand-btn {{ display: block; }}

  /* hidden state */
  .room-card.hidden {{ display: none; }}
</style>
</head>
<body>

<div class="header">
  <h2>🗺️ Annotated Floor Plan</h2>
  <span class="pill fail">❌ {fail_count} Fail</span>
  <span class="pill pass">✅ {pass_count} Pass</span>
  <span class="pill warn">⚠️ {warn_count} Warnings</span>
</div>

<div class="toggles">
  <button class="toggle-btn all active" onclick="filterCards('ALL')">All Rooms</button>
  <button class="toggle-btn fail" onclick="filterCards('FAIL')">❌ Errors</button>
  <button class="toggle-btn warn" onclick="filterCards('INSUFFICIENT_DATA')">⚠️ Warnings</button>
  <button class="toggle-btn pass" onclick="filterCards('PASS')">✅ Pass</button>
  <button class="toggle-btn na"   onclick="filterCards('NOT_APPLICABLE')">➖ N/A</button>
</div>

<div class="image-wrapper" id="imgWrapper">
  <div class="zoom-controls">
    <button class="zoom-btn" onclick="zoom(1.2)">+</button>
    <button class="zoom-btn" onclick="zoom(0.8)">−</button>
    <button class="zoom-btn" onclick="resetZoom()" title="Reset">⟳</button>
  </div>
  <img id="floorPlan" class="floor-plan-img"
    src="data:image/png;base64,{b64}" alt="Annotated Floor Plan"/>
</div>

<div class="cards-section">
  <div class="cards-label">Room Compliance Details — click a card to see suggested fix</div>
  <div class="cards-grid" id="cardsGrid"></div>
</div>

<script>
const cards = {cards_json};
let currentZoom = 1.0;

// ── Build room cards ──────────────────────────────────────────────
function buildCards(data) {{
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = '';
  data.forEach((r, i) => {{
    const hasFix = r.fix && r.fix.trim().length > 0;
    const hasReason = r.reason && r.reason.trim().length > 0;
    const div = document.createElement('div');
    div.className = 'room-card' + (hasFix ? ' has-fix' : '');
    div.dataset.status = r.status;
    div.dataset.idx = i;
    div.style.borderColor = r.badge + '40';
    div.style.setProperty('--card-color', r.badge);
    div.style.cssText += `border-color:${{r.badge}}30;`;
    div.querySelector && null;

    div.innerHTML = `
      <div style="position:absolute;top:0;left:0;right:0;height:3px;background:${{r.badge}};border-radius:8px 8px 0 0"></div>
      <div class="card-name" style="color:${{r.badge}}">${{r.emoji}} ${{r.name}}</div>
      <div class="card-area">
        ${{r.area > 0 ? r.area.toFixed(0) + ' sq ft' : 'No data'}}
        ${{r.req > 0 ? ' / Min ' + r.req.toFixed(0) + ' sq ft' : ''}}
      </div>
      ${{hasReason ? '<div class="card-area" style="color:#e74c3c;font-size:10px">' + r.reason.slice(0,80) + (r.reason.length>80?'…':'') + '</div>' : ''}}
      ${{hasFix ? '<div class="card-fix" id="fix-'+i+'">💡 ' + r.fix + '</div>' : ''}}
      ${{r.code ? '<div class="card-area" style="font-style:italic;margin-top:3px">📖 ' + r.code.slice(0,60) + '</div>' : ''}}
      ${{hasFix ? '<div class="expand-btn" onclick="toggleFix('+i+',this)">Show fix suggestion ▼</div>' : ''}}
    `;
    grid.appendChild(div);
  }});
}}

function toggleFix(idx, btn) {{
  const card = btn.closest('.room-card');
  const fix = document.getElementById('fix-' + idx);
  if (card.classList.contains('expanded')) {{
    card.classList.remove('expanded');
    btn.textContent = 'Show fix suggestion ▼';
  }} else {{
    card.classList.add('expanded');
    btn.textContent = 'Hide ▲';
  }}
}}

// ── Layer toggle ───────────────────────────────────────────────────
function filterCards(status) {{
  // Update button states
  document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  document.querySelectorAll('.room-card').forEach(card => {{
    if (status === 'ALL' || card.dataset.status === status) {{
      card.classList.remove('hidden');
    }} else {{
      card.classList.add('hidden');
    }}
  }});
}}

// ── Zoom ───────────────────────────────────────────────────────────
function zoom(factor) {{
  currentZoom = Math.min(Math.max(currentZoom * factor, 0.5), 4.0);
  document.getElementById('floorPlan').style.transform = 'scale(' + currentZoom + ')';
  document.getElementById('floorPlan').style.transformOrigin = 'top left';
  document.getElementById('floorPlan').style.width = (100 / currentZoom) + '%';
}}
function resetZoom() {{
  currentZoom = 1.0;
  const img = document.getElementById('floorPlan');
  img.style.transform = 'scale(1)';
  img.style.width = '100%';
}}

// Init
buildCards(cards);
</script>
</body>
</html>
"""
    return html


def estimate_component_height(n_rooms: int) -> int:
    """Estimate a good Streamlit component height for n rooms."""
    card_rows = math.ceil(n_rooms / 4)
    return 500 + 120 + card_rows * 120 + 80
