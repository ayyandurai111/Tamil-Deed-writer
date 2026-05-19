"""
tools/validate_fields.py
========================
Tool 4 — validate_fields

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
    name="validate_fields",
    description=(
        "[STEP 4 of 9] collect ஆன fields-ஐ legal requirements-க்கு எதிராக சரிபார். "
        "deed_type = Step 1 result. fields = extract_fields + resolve_date merge ஆன dict. "
        "can_generate=True → Step 5 fill_skeleton செல். "
        "can_generate=False → பயனரிடம் Tamil-இல் கேள்: "
        "'பத்திரம் உருவாக்க கீழ்கண்ட விவரங்கள் தேவை: 1.[field]? 2.[field]? ...'. "
        "பயனர் reply → extract_fields (existing_fields pass) → resolve_date → validate_fields LOOP. "
        "pan_tds_notes இருந்தால் பயனருக்கு காட்டு — block செய்யாதே."
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
                "description": "The fields dict returned by extract_fields."
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
        for pan_key in ("VENDOR_PAN", "PURCHASER_PAN"):
            if not fields.get(pan_key):
                missing[pan_key] = (
                    f"{pan_key.split('_')[0].title()} PAN எண் "
                    f"(IT Rule 114B — ₹10 லட்சத்திற்கு மேல் PAN கட்டாயம்)"
                )

    # Advisory notes in Tamil
    notes = []
    if pan_needed:
        notes.append("⚠️ தொகை ₹10 லட்சத்திற்கு மேல் — PAN எண் கட்டாயம் (IT Rule 114B)")
    if tds_needed:
        notes.append("⚠️ தொகை ₹50 லட்சத்திற்கு மேல் — வாங்குபவர் 1% TDS பிடிக்க வேண்டும் (IT S.194-IA)")

    return {
        "missing_critical": missing,
        "missing_count":    len(missing),
        "pan_required":     pan_needed,
        "tds_required":     tds_needed,
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
