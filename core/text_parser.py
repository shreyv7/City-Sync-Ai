"""
Text-based room parser for architectural floor plan PDFs.
Extracts room names and dimensions (feet-inches format) from PDF text
using pattern matching. Works with both clean pdfplumber text and
noisy OCR output from pytesseract.

Strategy:
  1.  Find ALL dimensions in the text (with their positions).
  2.  Find ALL room names in the text (with their positions).
  3.  Pair each room name to its CLOSEST dimension (by character
      distance), using a greedy nearest-neighbour assignment so that
      no dimension is assigned to two rooms.
"""

import re


# ── Known room name patterns ────────────────────────────────────────
_ROOM_BASE_PATTERNS = [
    # Combined rooms (must be before individual matches)
    r"DINING\s*(?:/|\\|CUM|AND|&|-)?\s*LIVING",
    r"LIVING\s*(?:/|\\|CUM|AND|&|-)?\s*DINING",
    r"DRAWING\s*(?:/|\\|CUM|AND|&|-)?\s*DINING",
    r"DRAWING\s*(?:/|\\|CUM|AND|&|-)?\s*LIVING",
    # Bedrooms
    r"GUEST\s*ROOM",
    r"BED\s*ROOM",
    r"BEDROOM",
    r"MASTER\s*BED(?:\s*ROOM)?",
    r"(?:[A-Z]\s*\.?\s*)?BED(?:\s*ROOM)?",
    # Living areas
    r"LIVING\s*ROOM",
    r"LIVING\s*HALL",
    r"LIVING",
    r"DRAWING\s*ROOM",
    r"DRAWING",
    r"HALL",
    r"FOYER",
    r"PASSAGE",
    # Kitchen
    r"KITCHEN",
    # Bathrooms / Toilets
    r"COMMON\s*TOILET",
    r"ATTACHED\s*TOILET",
    r"(?:[A-Z]\s*\.?\s*)?TOILET",
    r"(?:[A-Z]\s*\.?\s*)?WASH\s*ROO(?:M)?",
    r"(?:[A-Z]\s*\.?\s*)?WASHROOM",
    r"(?:[A-Z]\s*\.?\s*)?BATHROOM",
    r"(?:[A-Z]\s*\.?\s*)?BATH\s*ROOM",
    r"(?:[A-Z]\s*\.?\s*)?BATH",
    r"POWDER",
    r"W\.?\s*C\.?",
    r"WC",
    # Worship
    r"PUJ?A\s*(?:ROOM)?",
    r"POOJA\s*(?:ROOM)?",
    # Dressing
    r"DRESS(?:\s*(?:ROOM|ING))?",
    # Outdoor / balcony
    r"PORCH",
    r"VERANDA",
    r"VERANDAH",
    r"BALCONY",
    r"SIT\s*(?:OUT|AREA)",
    r"TERRACE",
    # Utility
    r"UTILITY",
    r"STORE(?:\s*ROOM)?",
    r"STUDY(?:\s*ROOM)?",
    r"SERVANT\s*(?:ROOM|QUARTER)?",
    r"GARAGE",
    r"CAR\s*PARK(?:ING)?",
    r"CANOPY",
    r"STAIR(?:\s*CASE)?",
    # Lobby / Lifts
    r"LIFT\s*LOBBY",
    r"LIFT(?!\s*LOBBY)",
    r"LOBBY",
    # Dining (standalone — after combined patterns)
    r"DINING(?:\s*ROOM)?",
]

# Build the regex:
#   group(1) = base room name
#   group(2) = optional room number preceded by - or space
_ROOM_NAME_RE = re.compile(
    r"\b(" + "|".join(_ROOM_BASE_PATTERNS) + r")"
    r"(?:\s*[-–]\s*(\d+))?",
    re.IGNORECASE
)

# ── Dimension patterns ──────────────────────────────────────────────
_FT_IN = (
    r"(\d{1,3})"                              # feet
    r"""[''\u2019\u2032\-]"""                  # foot mark
    r"[-\s]*"
    r"(\d{1,2})?"                              # inches (optional)
    r"(?:\s*[½¼¾]|\s*\d+\s*/\s*\d+)?"         # fraction
    # inch mark / noise — allow any non-digit non-letter char, plus
    # stray OCR-garbled fraction chars (single letters/symbols)
    r"""[\s""''\u201D\u2033°A-Za-z%#@]*"""    # permissive noise before X
)

_DIM_FT_IN_RE = re.compile(
    _FT_IN + r"\s*[xX×*]\s*" + _FT_IN          # sometimes OCR reads X as *
)


def _ft_in_to_float(feet_str, inches_str):
    """
    Convert feet + inches strings to a float in feet.

    OCR often merges superscript fractions into the inch digits, e.g.
    7½" → 72", turning 7 inches into 72 inches.  Since valid inches
    are 0-11, any value ≥ 12 means the trailing digit(s) are noise
    from a fraction and must be stripped.
    """
    feet = int(feet_str) if feet_str else 0
    inches = int(inches_str) if inches_str else 0
    # Fix OCR fraction merge: 72→7, 42→4, 102→10
    if inches > 11:
        inches = inches // 10
    return feet + inches / 12.0


def _find_all_dimensions(text):
    """
    Find every feet-inches dimension occurrence in the text.
    Only matches the architectural format with foot marks:
        7'-5"X6'-5"   10'-6"X10'-1"   8'-0"X4'-0"

    Does NOT match plain decimal like 20x33 (which appears in titles/plot sizes).

    Returns:
        list of (start_pos, end_pos, width_ft, length_ft)
    """
    dims = []

    for m in _DIM_FT_IN_RE.finditer(text):
        w = _ft_in_to_float(m.group(1), m.group(2))
        l = _ft_in_to_float(m.group(3), m.group(4))
        if 1 < w < 100 and 1 < l < 100:
            dims.append((m.start(), m.end(), round(w, 1), round(l, 1)))

    return dims


def _is_garbled_text(text):
    """Check if pdfplumber text contains CID codes (custom font encoding)."""
    if not text:
        return True
    return text.count("(cid:") > 5


# ── Title block / notes phrases to strip before parsing ──────────────
# These phrases from the architectural title block contain room-like
# keywords (DRAWING, HALL, etc.) that cause false room name matches.
_TITLE_BLOCK_PHRASES = [
    r"DRAWING\s+(STATUS|NO|TITLE|IS|NOT)\b[^\n]*",
    r"NOTE[S:]?\s*[^\n]*",
    r"SCALE\b[^\n]*",
    r"DEALT\b[^\n]*",
    r"CKD\s*BY\b[^\n]*",
    r"REVISION\b[^\n]*",
    r"DWG\s*NO\b[^\n]*",
    r"PROPERTY\s+OF[^\n]*",
    r"SHALL\s+NOT\b[^\n]*",
    r"PERMISSION[^\n]*",
    r"DIMENSIONS\s+ARE\b[^\n]*",
    r"NOT\s+TO\s+BE\s*SCALED[^\n]*",
    r"WRITTEN\s+DIMENSIONS[^\n]*",
    r"PROJECT\b[^\n]*",
    r"PLOT\s*(NO|SIZE)\b[^\n]*",
    r"WORKING\s*PLAN[^\n]*",
    r"GROUND\s*FLOOR\s*PLAN",
    r"FRONT\s*DOOR\b[^\n]*",
    r"DESIGN\s*AIDE\b[^\n]*",
    r"OPTION\s*[-–]?\s*\d+",
    r"proposed\s+column",
    r"existing\s+column[^\n]*",
    r"column\s+position[^\n]*",
]
_TITLE_BLOCK_RE = re.compile(
    "|".join(_TITLE_BLOCK_PHRASES), re.IGNORECASE
)


def _normalize_ocr_text(text):
    """Normalise common OCR artefacts."""
    if not text:
        return text
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201C', '"').replace('\u201D', '"')
    text = text.replace('\u2032', "'").replace('\u2033', '"')
    text = text.replace('\u00D7', 'x')
    text = text.replace("''", '"')  # Two single quotes -> double quote

    # ── Strip title block / notes phrases that contain room-like words ──
    text = _TITLE_BLOCK_RE.sub('', text)

    # ── OCR fraction artifact cleanup ──
    # OCR reads superscript fractions (½ ³⁄₈) as random letters/symbols.
    # Strip lone letters/symbols between a digit and an inch mark (" or ').
    # e.g. 7 Z" → 7"   |   4 %" → 4"   |   7 %"X → 7"X
    text = re.sub(r'(\d)\s*[A-Za-z%@#]+\s*(?=["\'])', r'\1', text)

    # ── Common OCR misreads in numbers ──
    # Number-O-quote -> Number-0-quote (e.g. 1O' -> 10')
    text = re.sub(r"(?<=\d)[Oo](?=['\"-])", "0", text)

    # S-quote -> 5-quote (e.g. S' -> 5', S" -> 5")
    text = re.sub(r"\b[Ss](?=['\"-])", "5", text)

    # O-quote -> 0-quote
    text = re.sub(r"\b[Oo](?=['\"-])", "0", text)

    # dash-S -> dash-5 (e.g. 7'-S)
    text = re.sub(r"(?<=-)[Ss]\b", "5", text)

    # dash-O -> dash-0
    text = re.sub(r"(?<=-)[Oo]\b", "0", text)

    return text


def _merge_split_rooms(rooms):
    """
    Merges common combined room names (like Dining and Living) if they were
    separated by OCR spatial sorting (e.g. DINING -> Dimension -> LIVING).
    """
    if not rooms:
        return rooms

    merged = []
    i = 0
    pairs_to_merge = [{'DINING', 'LIVING'}, {'DRAWING', 'DINING'}, {'DRAWING', 'LIVING'}]

    while i < len(rooms):
        if i < len(rooms) - 1:
            name1 = rooms[i]['room_name'].upper()
            name2 = rooms[i+1]['room_name'].upper()
            
            # Remove trailing numbers just for matching (e.g. Dining 1)
            base1 = re.sub(r'\s*\d+$', '', name1).strip()
            base2 = re.sub(r'\s*\d+$', '', name2).strip()
            
            if {base1, base2} in pairs_to_merge:
                # Merge them into a single room
                dim_w = max(rooms[i]['width_ft'], rooms[i+1]['width_ft'])
                dim_l = max(rooms[i]['length_ft'], rooms[i+1]['length_ft'])
                
                merged.append({
                    "room_name": f"{base1.title()}/{base2.title()}",
                    "width_ft": dim_w,
                    "length_ft": dim_l
                })
                i += 2
                continue
                
        merged.append(rooms[i])
        i += 1
        
    return merged


def parse_rooms_from_text(text):
    """
    Parses room names and their associated dimensions from floor plan text.

    Uses a nearest-neighbour pairing strategy:
      1. Find all room name positions in the text.
      2. Find all dimension positions in the text.
      3. For each room, find the closest unassigned dimension
         (by character distance between room-match-end and dim-start).

    This avoids the old bug where a large search window grabbed
    the wrong room's dimensions.

    Returns:
        list[dict]: Rooms with room_name, width_ft, length_ft.
    """
    if not text or _is_garbled_text(text):
        return []

    text = _normalize_ocr_text(text)

    # ── Step 1: find all room names ──────────────────────────────────
    room_matches = []
    seen_keys = {}

    for match in _ROOM_NAME_RE.finditer(text):
        base_name = match.group(1).strip()
        room_number = match.group(2)

        name = re.sub(r"\s+", " ", base_name).strip().title()
        if room_number:
            name = f"{name}-{room_number}"

        # De-duplicate
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key in seen_keys:
            seen_keys[key] += 1
            name = f"{name} {seen_keys[key]}"
            new_key = re.sub(r"[^a-z0-9]", "", name.lower())
            seen_keys[new_key] = 1
        else:
            seen_keys[key] = 1

        room_matches.append({
            "name": name,
            "start": match.start(),
            "end": match.end(),
        })

    if not room_matches:
        return []

    # ── Step 2: find all dimensions ──────────────────────────────────
    all_dims = _find_all_dimensions(text)

    # ── Step 3: pair each room to its closest dimension ──────────────
    # Sort room-dim pairs by distance and greedily assign.
    # Distance = abs(room_end - dim_start), with a bonus for dims
    # that appear AFTER the room name (more natural reading order).
    assigned_dims = set()

    # Build all (room_idx, dim_idx, distance) candidates
    candidates = []
    for ri, room in enumerate(room_matches):
        for di, dim in enumerate(all_dims):
            # Prefer dims that come AFTER the room name
            if dim[0] >= room["end"]:
                dist = dim[0] - room["end"]
            else:
                # Dim is BEFORE room name — penalise slightly
                dist = (room["start"] - dim[1]) + 500  # penalty
                if dist < 0:
                    dist = 9999  # dim overlaps room text, skip
            candidates.append((dist, ri, di))

    candidates.sort()

    room_to_dim = {}
    for dist, ri, di in candidates:
        if ri in room_to_dim or di in assigned_dims:
            continue
        # Max distance threshold — don't pair if too far away
        if dist > 1000:
            continue
        room_to_dim[ri] = di
        assigned_dims.add(di)

    # ── Step 4: build result list ────────────────────────────────────
    rooms = []
    for ri, room in enumerate(room_matches):
        if ri in room_to_dim:
            dim = all_dims[room_to_dim[ri]]
            width, length = dim[2], dim[3]
        else:
            width, length = 0.0, 0.0

        rooms.append({
            "room_name": room["name"],
            "width_ft": width,
            "length_ft": length,
        })

    return _merge_split_rooms(rooms)
