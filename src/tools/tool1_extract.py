"""
tools/tool1_extract.py
======================
Tool 1 — extract

AI reads user text and extracts fields.
This tool receives extracted fields, validates format, normalizes,
merges with existing_fields, and returns what is still missing.

AI role  : 100% — reads user text, extracts field values
Logic role: 100% — format validation, normalize, merge, missing check

VALIDATION RULES (pure logic, no AI):
  AADHAAR  → exactly 12 digits
  PHONE    → exactly 10 digits
  PAN      → 5 alpha + 4 digit + 1 alpha
  AMOUNT   → digits only (strip commas/₹)
  AGE      → numeric, 1-120
  DATE_MONTH → convert number/English → Tamil name
"""

import json
import re
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS, TAMIL_MONTHS, PAN_THRESHOLD

# ── Regex patterns ─────────────────────────────────────────────────────────────
_AADHAAR_RE = re.compile(r"^\d{12}$")
_PHONE_RE   = re.compile(r"^\d{10}$")
_PAN_RE     = re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])")
_DIGITS_RE  = re.compile(r"[^\d]")

_EN_TO_NUM = {
    "january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,
    "april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,
    "august":8,"aug":8,"september":9,"sep":9,"sept":9,
    "october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12,
}

TOOL_DEFINITION = Tool(
    name="extract",
    description=(
    "WHEN TO CALL: When the user provides any deed-related information. "
    "Also call again after user replies to a missing-fields question or error correction. "

    "POSITION: Tool 1 of 3. Call this first, before any other tool. "

    "WHAT YOU (AI) DO BEFORE CALLING: "
    "Read user text. Extract field values yourself. "
    "Pass extracted values in extracted_fields. UPPERCASE keys. null if not in text. "
    "NEVER guess or invent values. "

    "FIELDS TO EXTRACT: "
    "VENDOR_NAME, VENDOR_FATHER, VENDOR_RELATION, VENDOR_AGE, VENDOR_PREFIX, "
    "VENDOR_ADDRESS, VENDOR_AADHAAR (12 digits), VENDOR_PHONE (10 digits), VENDOR_PAN. "
    "PURCHASER_NAME, PURCHASER_FATHER, PURCHASER_RELATION, PURCHASER_AGE, PURCHASER_PREFIX, "
    "PURCHASER_ADDRESS, PURCHASER_ID (aadhaar or PAN), PURCHASER_PHONE, PURCHASER_PAN. "
    "DATE_DAY, DATE_MONTH, DATE_YEAR. "
    "TOTAL_AMOUNT (digits only). NANJAI_OR_PUNJAI (exact Tamil word). "
    "Any other deed field present in text. "

    "PARAMETERS: "
    "deed_type = 'agriculture' or 'plot' (you determine from text). "
    "extracted_fields = fields from THIS turn only. "
    "existing_fields = full accumulated dict from ALL previous turns (never empty after turn 1). "
    "date_text = raw date string from user, or empty string. "

    "AFTER TOOL RETURNS — follow exactly one branch: "
    "IF extract_ok=false → send Tamil error message. Ask user to correct. Call again. "
    "IF extract_ok=true AND missing_fields not empty → ask user in Tamil for missing fields. Call again with all accumulated fields. "
    "IF ready_for_analyse=true → call Tool 2 (analyse) immediately."
),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "YOU determine deed type from user text. agriculture=விவசாய நிலம், plot=மனை நிலம். Default plot if unclear."
            },
            "extracted_fields": {
                "type": "object",
                "description": "Fields YOU extracted from user text. UPPERCASE keys. null for missing."
            },
            "existing_fields": {
                "type": "object",
                "description": "Full accumulated dict from previous turns. Pass {} on first call.",
                "default": {}
            },
            "date_text": {
                "type": "string",
                "description": "Raw date string from user text (e.g. '15/05/2026', 'இன்று', ''). Pass '' if no date given.",
                "default": ""
            }
        },
        "required": ["deed_type", "extracted_fields"],
        "additionalProperties": False
    },
    outputSchema={
        "type": "object",
        "properties": {
            "deed_type":       {"type": "string"},
            "fields":          {"type": "object", "description": "Merged + normalized fields (UPPERCASE keys)."},
            "field_errors":    {"type": "object", "description": "Format errors found by logic. Empty = all valid."},
            "missing_fields":  {"type": "object", "description": "Critical fields still null. Empty = all present."},
            "extract_ok":      {"type": "boolean", "description": "True when no format errors exist. Missing fields may still exist."},
            "ready_for_analyse": {"type": "boolean", "description": "True when extract_ok=true AND missing_fields is empty."},
            "found_count":     {"type": "integer"},
            "missing_count":   {"type": "integer"},
            "message":         {"type": "string"},
            "next_tool":       {"type": "string", "description": "'analyse' when ready. 'user:fix_errors' when errors. 'user:ask_missing' when fields missing."}
        },
        "required": ["deed_type","fields","field_errors","missing_fields","extract_ok","ready_for_analyse","found_count","missing_count","message","next_tool"],
        "additionalProperties": False
    },
    annotations={"title": "Field Extractor + Validator", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: normalize
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(fields: dict) -> dict:
    out = {}
    for k, v in fields.items():
        key = str(k).strip().upper()
        if v in (None, "null", "None", "undefined", ""):
            out[key] = None
        else:
            out[key] = str(v).strip() if not isinstance(v, (dict, list)) else v
    return out


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: format validation — 100% pure Python, zero AI
# ══════════════════════════════════════════════════════════════════════════════

def _validate_formats(fields: dict) -> dict:
    """
    Returns field_errors: { FIELD_KEY: "error description in Tamil" }
    Empty dict = all fields valid.
    """
    errors = {}

    # AADHAAR fields — must be exactly 12 digits
    for key in ("VENDOR_AADHAAR", "PURCHASER_AADHAAR"):
        val = fields.get(key)
        if val and not _AADHAAR_RE.match(_DIGITS_RE.sub("", val)):
            errors[key] = f"{key}: ஆதார் எண் 12 இலக்கமாக இருக்க வேண்டும் (கிடைத்தது: '{val}')"

    # PHONE fields — must be exactly 10 digits
    for key in ("VENDOR_PHONE", "PURCHASER_PHONE", "WITNESS1_PHONE", "WITNESS2_PHONE"):
        val = fields.get(key)
        if val and not _PHONE_RE.match(_DIGITS_RE.sub("", val)):
            errors[key] = f"{key}: கைபேசி எண் 10 இலக்கமாக இருக்க வேண்டும் (கிடைத்தது: '{val}')"

    # PAN fields — if provided must match pattern
    for key in ("VENDOR_PAN", "PURCHASER_PAN"):
        val = fields.get(key)
        if val and not _PAN_RE.search(val.upper()):
            errors[key] = f"{key}: PAN தவறான format (சரியான format: ABCDE1234F)"

    # AMOUNT — must be digits only after strip
    val = fields.get("TOTAL_AMOUNT")
    if val:
        clean = _DIGITS_RE.sub("", val)
        if not clean:
            errors["TOTAL_AMOUNT"] = f"TOTAL_AMOUNT: தொகை எண்ணில் மட்டும் கொடுக்கவும் (கிடைத்தது: '{val}')"
        else:
            fields["TOTAL_AMOUNT"] = clean  # normalize in place

    # AGE — numeric
    for key in ("VENDOR_AGE", "PURCHASER_AGE"):
        val = fields.get(key)
        if val:
            try:
                age = int(val)
                if not (1 <= age <= 120):
                    errors[key] = f"{key}: வயது 1-120 இடையில் இருக்க வேண்டும் (கிடைத்தது: '{val}')"
            except ValueError:
                errors[key] = f"{key}: வயது எண்ணில் கொடுக்கவும் (கிடைத்தது: '{val}')"

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: date resolve — from extract date_text
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_date(date_text: str, fields: dict) -> dict:
    """
    Resolve date from date_text and inject DATE_DAY/DATE_MONTH/DATE_YEAR into fields.
    Reuses existing resolve_date logic inline.
    """
    from tools.resolve_date import parse_date
    result = parse_date(date_text or "")
    fields["DATE_DAY"]   = result.get("DATE_DAY",   "")
    fields["DATE_MONTH"] = result.get("DATE_MONTH", "")
    fields["DATE_YEAR"]  = result.get("DATE_YEAR",  "")
    fields["DATE_FULL"]  = result.get("DATE_FULL",  "")
    return result.get("source", "today_default")


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: month fixup
# ══════════════════════════════════════════════════════════════════════════════

def _fixup_month(fields: dict):
    month_val = fields.get("DATE_MONTH")
    if month_val:
        mv = str(month_val).strip()
        if mv.isdigit():
            tamil = TAMIL_MONTHS.get(int(mv))
            if tamil:
                fields["DATE_MONTH"] = tamil
        elif mv.lower() in _EN_TO_NUM:
            tamil = TAMIL_MONTHS.get(_EN_TO_NUM[mv.lower()])
            if tamil:
                fields["DATE_MONTH"] = tamil


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: AMOUNT_WORDS suffix fixup
# ══════════════════════════════════════════════════════════════════════════════

def _fixup_words(fields: dict):
    for key in ("AMOUNT_WORDS", "RECEIVED_WORDS", "ADVANCE_WORDS", "BALANCE_WORDS"):
        val = fields.get(key)
        if val and str(val).strip().endswith("மட்டும்"):
            fields[key] = str(val).strip()[:-len("மட்டும்")].strip()


def _fixup_plot_id(deed_type: str, fields: dict):
    """
    BUG FIX: AI often sends VENDOR_AADHAAR / PURCHASER_AADHAAR for plot deeds.
    Plot skeleton uses VENDOR_ID / PURCHASER_ID.
    Auto-map if VENDOR_ID is null but VENDOR_AADHAAR is present.
    """
    if deed_type != "plot":
        return
    if not fields.get("VENDOR_ID") and fields.get("VENDOR_AADHAAR"):
        fields["VENDOR_ID"] = fields["VENDOR_AADHAAR"]
    if not fields.get("PURCHASER_ID") and fields.get("PURCHASER_AADHAAR"):
        fields["PURCHASER_ID"] = fields["PURCHASER_AADHAAR"]


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC: missing critical fields check
# ══════════════════════════════════════════════════════════════════════════════

def _find_missing(deed_type: str, fields: dict) -> dict:
    critical = CRITICAL_FIELDS.get(deed_type, {})
    missing = {}
    for key, label in critical.items():
        val = fields.get(key.upper())
        if not val or str(val).startswith("{{"):
            missing[key.upper()] = label
    return missing


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    deed_type        = arguments.get("deed_type", "plot")
    extracted_fields = arguments.get("extracted_fields") or {}
    existing_fields  = arguments.get("existing_fields")  or {}
    date_text        = arguments.get("date_text", "")

    # Step 1: normalize both dicts
    extracted = _normalize(extracted_fields)
    existing  = _normalize(existing_fields)

    # Step 2: merge — existing non-null values are never overwritten
    merged = dict(existing)
    for key, val in extracted.items():
        if key not in merged or merged[key] is None:
            merged[key] = val

    # Step 3: ensure all critical keys present (None if never found)
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        merged.setdefault(key.upper(), None)

    # Step 4: resolve date (pure logic)
    _resolve_date(date_text, merged)

    # Step 5: month fixup
    _fixup_month(merged)

    # Step 6: AMOUNT_WORDS suffix fixup
    _fixup_words(merged)

    # Step 6b: plot deed VENDOR_AADHAAR → VENDOR_ID auto-map
    _fixup_plot_id(deed_type, merged)

    # Step 7: format validation (pure logic)
    field_errors = _validate_formats(merged)

    # Step 8: missing critical fields check
    missing_fields = _find_missing(deed_type, merged)

    extract_ok       = len(field_errors) == 0
    ready_for_analyse = extract_ok and len(missing_fields) == 0

    found   = [k for k, v in merged.items() if v is not None]
    missing = [k for k, v in merged.items() if v is None]

    if not extract_ok:
        next_tool = "user:fix_errors"
    elif missing_fields:
        next_tool = "user:ask_missing"
    else:
        next_tool = "analyse"

    return [TextContent(
        type="text",
        text=json.dumps({
            "deed_type":          deed_type,
            "fields":             merged,
            "field_errors":       field_errors,
            "missing_fields":     missing_fields,
            "extract_ok":         extract_ok,
            "ready_for_analyse":  ready_for_analyse,
            "found_count":        len(found),
            "missing_count":      len(missing_fields),
            "message": (
                f"{'✅' if extract_ok else '❌'} "
                f"{len(found)} fields found. "
                f"{len(field_errors)} format errors. "
                f"{len(missing_fields)} critical fields missing. "
                f"next_tool={next_tool}"
            ),
            "next_tool": next_tool
        }, ensure_ascii=False, indent=2)
    )]
