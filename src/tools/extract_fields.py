"""
tools/extract_fields.py
=======================
Tool 3 — extract_fields

The AI reads the user prompt and extracts fields itself.
This tool receives extracted fields, normalizes keys to UPPERCASE,
merges with existing_fields, and returns what is still missing.

FIX: All keys normalized to UPPERCASE before storing,
     so key-case mismatches from the AI never cause placeholder leaks.
"""

import json
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS, TAMIL_MONTHS

TOOL_DEFINITION = Tool(
    name="extract_fields",
    description=(
        "[CALL 3 of 12] ONE TASK: call this tool only. "
        "Before calling — YOU extract all fields from the user's text. Pass what you found to this tool. "
        "Do NOT pass the raw user prompt — extract first, then call. "

        "WHAT TO EXTRACT: "
        "VENDOR_NAME / VENDOR_FATHER / VENDOR_AGE / VENDOR_ADDRESS / VENDOR_AADHAAR(12 digits) / VENDOR_PHONE / VENDOR_PREFIX. "
        "PURCHASER_NAME / PURCHASER_FATHER / PURCHASER_AGE / PURCHASER_ADDRESS / PURCHASER_AADHAAR(12 digits) / PURCHASER_PHONE / PURCHASER_PREFIX. "
        "DATE_DAY / DATE_MONTH(Tamil: ஜனவரி…டிசம்பர்) / DATE_YEAR. "
        "TOTAL_AMOUNT(digits only, strip commas). NANJAI_OR_PUNJAI(exact Tamil word from text). Other deed fields. "
        "Field not in text → null. Never guess or fabricate. All keys UPPERCASE. "

        "Loop call: extracted_fields = new reply only; existing_fields = full accumulated dict from all turns. "
        "This tool merges: existing non-null values are never overwritten. "

        "Next separate response: CALL 4 resolve_date — ALWAYS call; pass date text or '' if none given."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Deed type from detect_deed_type result."
            },
            "extracted_fields": {
                "type": "object",
                "description": (
                    "Fields YOU (the AI) extracted from the user prompt. "
                    "Every key must be UPPERCASE matching CRITICAL_FIELDS. "
                    "Use null for fields not found in the prompt."
                )
            },
            "existing_fields": {
                "type": "object",
                "description": (
                    "Fields collected in previous conversation turns. "
                    "Pass {} on the very first call."
                ),
                "default": {}
            }
        },
        "required": ["deed_type", "extracted_fields"]
    },
    outputSchema={
        "type": "object",
        "properties": {
            "fields": {
                "type": "object",
                "description": "Merged dict of all collected field values (UPPERCASE keys). Null values indicate missing fields."
            },
            "found_count": {
                "type": "integer",
                "description": "Number of fields that have non-null values."
            },
            "missing_count": {
                "type": "integer",
                "description": "Number of fields still missing (null)."
            },
            "found_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of field keys that have been filled."
            },
            "missing_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of field keys that are still null."
            },
            "message": {
                "type": "string",
                "description": "Summary message with found/missing counts."
            },
            "next_tool": {
                "type": "string",
                "const": "resolve_date",
                "description": "Always call resolve_date next (CALL 4) — pass date string or empty string."
            }
        },
        "required": ["fields", "found_count", "missing_count", "found_fields", "missing_fields", "message", "next_tool"]
    },
    annotations={
        "title":          "Field Merger",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


def _normalize(fields: dict) -> dict:
    """Normalize all keys to UPPERCASE and strip null-like values."""
    out = {}
    for k, v in fields.items():
        key = str(k).strip().upper()
        if v in (None, "null", "None", "undefined", ""):
            out[key] = None
        else:
            out[key] = str(v).strip() if not isinstance(v, (dict, list)) else v
    return out


def _fixup(fields: dict) -> dict:
    """Post-normalize corrections applied once after merging."""

    # Fix 1 — DATE_MONTH: any format → Tamil name
    # User may give: "05" / "5" (number), "May" (English), "மே" (Tamil already correct)
    _EN_TO_NUM = {
        "january":1,  "jan":1,  "february":2, "feb":2,
        "march":3,    "mar":3,  "april":4,    "apr":4,
        "may":5,      "june":6, "jun":6,      "july":7,
        "jul":7,      "august":8,"aug":8,     "september":9,
        "sep":9,      "sept":9, "october":10, "oct":10,
        "november":11,"nov":11, "december":12,"dec":12,
    }
    month_val = fields.get("DATE_MONTH")
    if month_val:
        mv = str(month_val).strip()
        if mv.isdigit():
            # "05" or "5" → Tamil name
            tamil_name = TAMIL_MONTHS.get(int(mv))
            if tamil_name:
                fields["DATE_MONTH"] = tamil_name
        elif mv.lower() in _EN_TO_NUM:
            # "May" or "may" → Tamil name
            tamil_name = TAMIL_MONTHS.get(_EN_TO_NUM[mv.lower()])
            if tamil_name:
                fields["DATE_MONTH"] = tamil_name
        # Already Tamil ("மே") → unchanged ✅

    # Fix 2 — AMOUNT_WORDS: strip trailing "மட்டும்" to avoid duplicate
    # Template already ends with "மட்டும்" — user or the AI may append one too
    for key in ("AMOUNT_WORDS", "RECEIVED_WORDS", "ADVANCE_WORDS", "BALANCE_WORDS"):
        val = fields.get(key)
        if val and str(val).strip().endswith("மட்டும்"):
            fields[key] = str(val).strip()[:-len("மட்டும்")].strip()

    return fields


async def handle(arguments: dict) -> list[TextContent]:
    deed_type        = arguments.get("deed_type", "plot")
    extracted_fields = arguments.get("extracted_fields") or {}
    existing_fields  = arguments.get("existing_fields")  or {}

    # Normalize both to UPPERCASE keys
    extracted = _normalize(extracted_fields)
    existing  = _normalize(existing_fields)

    # Merge: start from existing, fill nulls with new extracted values
    merged = dict(existing)
    for key, val in extracted.items():
        if key not in merged or merged[key] is None:
            merged[key] = val

    # Ensure every critical field key is present (None if never found)
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        merged.setdefault(key.upper(), None)

    # Apply post-normalize corrections
    merged = _fixup(merged)

    found   = [k for k, v in merged.items() if v is not None]
    missing = [k for k, v in merged.items() if v is None]

    return [TextContent(
        type="text",
        text=json.dumps({
            "fields":         merged,
            "found_count":    len(found),
            "missing_count":  len(missing),
            "found_fields":   found,
            "missing_fields": missing,
            "message": (
                f"✅ {len(found)} fields found, {len(missing)} still missing. "
                "Pass these fields to validate_fields next."
            ),
            "next_tool": "resolve_date"
        }, ensure_ascii=False, indent=2)
    )]
