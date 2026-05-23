"""
tools/validate_fields.py (check_document_completeness)
========================
Tool 5 — check_document_completeness

Checks collected fields against CRITICAL_FIELDS law requirements.
Also applies PAN / TDS rules based on total transaction amount.

Returns can_generate=True only when ALL critical fields are present.

Annotation:
  readOnlyHint   = True   (no writes — pure validation logic)
  idempotentHint = True   (same fields → same result)
"""

import json
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS, PAN_THRESHOLD, TDS_THRESHOLD

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="check_document_completeness",
    description=(
        "[CALL 5 of 12] ONE TASK: இந்த tool call மட்டும். "
        "deed_type = CALL 1 result. fields = read_document_details result (confirm_document_date merge ஆனது இருந்தால் அதுவும் சேர்). "
        "tool call முடிந்தவுடன் response முடிந்தது. can_generate=True → NEXT CALL: draft_document. "
        "can_generate=False → NEXT CALL (தனி response): missing fields மட்டும் கேள் — tool call அல்ல. "
        "'பத்திரம் உருவாக்க கீழ்கண்ட விவரங்கள் தேவை: 1.[field]? 2.[field]? ...' "
        "பயனர் reply வந்த பிறகு: read_document_details CALL (existing_fields pass) → check_document_completeness CALL LOOP. "
        "pan_block=True → can_generate எப்போதும் False — PAN எண் கேள், draft_document செல்லாதே — HARD BLOCK. "
        "tds_required=True மட்டும் (pan_block=False) → TDS note காட்டு, block இல்லை — proceed செய். "
        "pan_tds_notes-ஐ காட்டுவது advisory மட்டும் — pan_block=True-ஐ override செய்யாது."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Type of deed."
            },
            "fields": {
                "type": "object",
                "description": "The fields dict returned by read_document_details."
            }
        },
        "required": ["deed_type", "fields"]
    },
    annotations={
        "title":          "Legal Field Validator",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ── Core validation function (also called directly by tests) ───────────────────
def run_validation(deed_type: str, fields: dict) -> dict:
    """
    Returns:
      {
        "missing_critical": { field_key: tamil_label_with_law },
        "missing_count":    int,
        "pan_required":     bool,
        "tds_required":     bool,
        "can_generate":     bool,
        "pan_tds_notes":    list[str]   — Tamil advisory messages
      }
    """
    critical = CRITICAL_FIELDS.get(deed_type, {})
    missing  = {}

    for key, label in critical.items():
        val = fields.get(key, "")
        if not val or str(val).startswith("{{"):
            missing[key] = label

    # PAN / TDS amount check
    try:
        amount     = int(str(fields.get("TOTAL_AMOUNT", "0")).replace(",", "").replace(" ", ""))
        pan_needed = amount >= PAN_THRESHOLD
        tds_needed = amount >= TDS_THRESHOLD
    except (ValueError, TypeError):
        pan_needed = False
        tds_needed = False

    # If PAN needed, add to missing if absent
    if pan_needed:
        if deed_type == "agriculture":
            for pan_key in ("VENDOR_PAN", "PURCHASER_PAN"):
                if not fields.get(pan_key):
                    missing[pan_key] = (
                        f"{pan_key.split('_')[0].title()} PAN எண் "
                        f"(IT Rule 114B — ₹10 லட்சத்திற்கு மேல் PAN கட்டாயம்)"
                    )
        else:
            # Plot deed: PAN is embedded inside VENDOR_ID / PURCHASER_ID
            import re as _re
            pan_pattern = r"[A-Z]{5}[0-9]{4}[A-Z]"
            for id_key, label in (("VENDOR_ID", "விற்பவர்"), ("PURCHASER_ID", "வாங்குபவர்")):
                val = fields.get(id_key, "") or ""
                if not _re.search(pan_pattern, val.upper()):
                    missing[id_key + "_PAN"] = (
                        f"{label} PAN எண் (VENDOR_ID-ல் சேர்க்கவும் — "
                        f"IT Rule 114B — ₹10 லட்சத்திற்கு மேல் PAN கட்டாயம்)"
                    )

    # Advisory notes in Tamil
    notes = []
    if pan_needed:
        notes.append("⚠️ தொகை ₹10 லட்சத்திற்கு மேல் — PAN எண் கட்டாயம் (IT Rule 114B)")
    if tds_needed:
        notes.append("⚠️ தொகை ₹50 லட்சத்திற்கு மேல் — வாங்குபவர் 1% TDS பிடிக்க வேண்டும் (IT S.194-IA)")

    pan_fields_missing = any("PAN" in k for k in missing)

    return {
        "missing_critical": missing,
        "missing_count":    len(missing),
        "pan_required":     pan_needed,
        "tds_required":     tds_needed,
        # BUG 3 FIX: explicit pan_block flag so Claude cannot confuse
        # "show pan_tds_notes" advisory with "PAN field is still missing".
        "pan_block":        pan_needed and pan_fields_missing,
        "can_generate":     len(missing) == 0,
        "pan_tds_notes":    notes
    }


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    deed_type = arguments.get("deed_type", "plot")
    fields    = arguments.get("fields", {})

    result = run_validation(deed_type, fields)

    return [TextContent(
        type="text",
        text=json.dumps(result, ensure_ascii=False, indent=2)
    )]
