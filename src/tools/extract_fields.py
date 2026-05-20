"""
tools/extract_fields.py
=======================
Tool 3 — extract_fields

Claude (the orchestrating AI) reads the user prompt and extracts fields itself.
This tool receives the already-extracted fields, merges with existing_fields,
and returns what is still missing.

No regex. No extra API call. Claude IS the AI — trust it to extract.

inputSchema change:
  - REMOVED: prompt  (Claude reads it directly, not passed here)
  - ADDED:   extracted_fields  (Claude fills this from the prompt)
  - KEPT:    existing_fields   (previous turn accumulation)

Annotation:
  readOnlyHint   = True
  idempotentHint = True
"""

import json
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="extract_fields",
    description=(
        "[STEP 3 of 9] "
        "YOU (Claude) are the AI — read the user's raw prompt yourself and extract all deed fields. "
        "Then call this tool with what you found. "
        "DO NOT pass the raw prompt here — extract first, then call. "

        "HOW TO CALL: "
        "extracted_fields = every field key you could find, null for anything missing. "
        "existing_fields  = fields collected in previous turns (empty on first call). "

        "EXTRACTION RULES (apply before calling): "
        "(1) Vendor = விற்பவர் / seller / grantor. "
        "(2) Purchaser = வாங்குபவர் / buyer / grantee. "
        "(3) DATE_DAY / DATE_MONTH / DATE_YEAR — split the date into three parts. "
        "(4) AADHAAR — 12 digits only, strip spaces and dashes. "
        "(5) TOTAL_AMOUNT — digits only, strip commas. "
        "(6) NANJAI_OR_PUNJAI — use exact Tamil word found in text. "
        "(7) If a field is not mentioned in the prompt → set it to null. Never guess. "

        "MERGE RULE (this tool handles it): "
        "existing non-null values are never overwritten. "
        "new non-null values fill in null slots only. "

        "After this tool returns, pass missing_fields to validate_fields."
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
                    "Fields YOU extracted from the user prompt. "
                    "Every key must be a valid CRITICAL_FIELDS key for the deed_type. "
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


# ── Handler — merge only, zero extraction logic ────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    deed_type        = arguments.get("deed_type", "plot")
    extracted_fields = arguments.get("extracted_fields") or {}
    existing_fields  = arguments.get("existing_fields") or {}

    # Start from existing accumulated fields
    merged = dict(existing_fields)

    # Merge: new non-null values fill null slots only
    for key, val in extracted_fields.items():
        # Normalise "null" strings → None
        if val in ("null", "None", "", "undefined"):
            val = None
        if val is not None and merged.get(key) is None:
            merged[key] = val
        elif key not in merged:
            merged[key] = val if val not in (None, "null", "None", "") else None

    # Ensure every critical field key is present (None if never found)
    for key in CRITICAL_FIELDS.get(deed_type, {}):
        merged.setdefault(key, None)

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
            )
        }, ensure_ascii=False, indent=2)
    )]
