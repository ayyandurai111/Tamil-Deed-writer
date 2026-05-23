"""
tools/extract_fields.py (read_document_details)
=======================
Tool 3 — read_document_details

The AI assistant reads the user prompt and extracts fields itself.
This tool receives extracted fields, normalizes keys to UPPERCASE,
merges with existing_fields, and returns what is still missing.

FIX: All keys normalized to UPPERCASE before storing,
     so key-case mismatches from the AI never cause placeholder leaks.
"""

import json
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS, TAMIL_MONTHS

TOOL_DEFINITION = Tool(
    name="read_document_details",
    description=(
        "[CALL 3 of 12] ONE TASK: இந்த tool call மட்டும். "
        "YOU (the AI assistant) are the one reading — read the user's raw prompt yourself and extract all deed fields. "
        "Then call this tool with what you found. "
        "DO NOT pass the raw prompt here — extract first, then call. "

        "HOW TO CALL: "
        "extracted_fields = every field key you could find, null for anything missing. "
        "existing_fields  = fields collected in previous turns (empty on first call). "

        "EXTRACTION RULES (apply before calling): "
        "(1) Vendor = விற்பவர் / seller / grantor. "
        "(2) Purchaser = வாங்குபவர் / buyer / grantee. "
        "(3) DATE_DAY / DATE_MONTH / DATE_YEAR — split the date into three parts. "
        "    DATE_MONTH must always be Tamil name: ஜனவரி பிப்ரவரி மார்ச் ஏப்ரல் மே ஜூன் ஜூலை ஆகஸ்ட் செப்டம்பர் அக்டோபர் நவம்பர் டிசம்பர். "
        "    உதாரணம்: '14/05/2026' → DATE_MONTH='மே', '14 May 2026' → DATE_MONTH='மே'. "
        "    (If you pass a number or English name, _fixup will auto-convert — but prefer Tamil directly.) "
        "(4) AADHAAR — 12 digits only, strip spaces and dashes. "
        "(5) TOTAL_AMOUNT — digits only, strip commas. "
        "(6) NANJAI_OR_PUNJAI — use exact Tamil word found in text. "
        "(7) If a field is not mentioned in the prompt → set it to null. Never guess. "
        "(8) All keys MUST be UPPERCASE (e.g. VENDOR_NAME not vendor_name). "

        "MERGE RULE (this tool handles it): "
        "existing non-null values are never overwritten. "
        "new non-null values fill in null slots only. "

        "tool call முடிந்தவுடன் response முடிந்தது. NEXT CALL (தனி response): confirm_document_date (CALL 4) — date இருந்தால் அது pass செய், இல்லாவிட்டால் '' pass செய். ALWAYS call."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Deed type from identify_document_type result."
            },
            "extracted_fields": {
                "type": "object",
                "description": (
                    "Fields YOU extracted from the user prompt. "
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
    # Template already ends with "மட்டும்" — user or Claude may append one too
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
                "Pass these fields to check_document_completeness next."
            )
        }, ensure_ascii=False, indent=2)
    )]
