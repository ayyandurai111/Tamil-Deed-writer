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
        "[CALL 5 of 12] ONE TASK: இந்த tool call மட்டும். "
        "deed_type = CALL 1 result. fields = extract_fields result (resolve_date merge ஆனது இருந்தால் அதுவும் சேர்). "
        "tool call முடிந்தவுடன் response முடிந்தது. can_generate=True → NEXT CALL: fill_skeleton. "
        "can_generate=False → NEXT CALL (தனி response): missing fields மட்டும் கேள் — tool call அல்ல. "
        "'பத்திரம் உருவாக்க கீழ்கண்ட விவரங்கள் தேவை: 1.[field]? 2.[field]? ...' "
        "பயனர் reply வந்த பிறகு: extract_fields CALL (existing_fields pass) → validate_fields CALL LOOP. "
        "pan_block=True → can_generate எப்போதும் False — PAN எண் கேள், fill_skeleton செல்லாதே — HARD BLOCK. "
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

    # ── PAN / TDS amount check ────────────────────────────────────────────────
    # BUG FIX 1: Strip rupee symbol (₹) and other non-numeric chars before int()
    # Previously "₹1500000" caused ValueError → pan_needed silently became False.
    import re as _re
    _amount_raw = str(fields.get("TOTAL_AMOUNT", "0"))
    _amount_clean = _re.sub(r"[^\d]", "", _amount_raw)  # keep digits only
    try:
        amount     = int(_amount_clean) if _amount_clean else 0
        pan_needed = amount >= PAN_THRESHOLD
        tds_needed = amount >= TDS_THRESHOLD
    except (ValueError, TypeError):
        pan_needed = False
        tds_needed = False

    # Valid PAN pattern: 5 alpha, 4 digit, 1 alpha — anchored with word boundary
    # BUG FIX 2: Use stricter pattern to reject "ABCDE1234FF" (extra trailing char)
    _PAN_RE = _re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])")

    def _has_valid_pan(value: str) -> bool:
        """Return True if value contains a syntactically valid PAN number."""
        return bool(_PAN_RE.search((value or "").upper()))

    # If PAN needed, add to missing if absent
    if pan_needed:
        if deed_type == "agriculture":
            # BUG FIX 3: Agriculture also accepts PAN embedded in VENDOR_AADHAAR
            # or any related field Claude may have stored it in, not only VENDOR_PAN.
            # Primary check: dedicated VENDOR_PAN / PURCHASER_PAN fields.
            # Fallback: search regex in VENDOR_AADHAAR field (some users give
            # "Aadhaar: 1234..., PAN: ABCDE1234F" as a combined string).
            for pan_key, fallback_key, role in (
                ("VENDOR_PAN",    "VENDOR_AADHAAR",    "விற்பவர்"),
                ("PURCHASER_PAN", "PURCHASER_AADHAAR", "வாங்குபவர்"),
            ):
                pan_val      = fields.get(pan_key, "") or ""
                fallback_val = fields.get(fallback_key, "") or ""
                if not _has_valid_pan(pan_val) and not _has_valid_pan(fallback_val):
                    missing[pan_key] = (
                        f"{role} PAN எண் "
                        f"(IT Rule 114B — ₹10 லட்சத்திற்கு மேல் PAN கட்டாயம்)"
                    )
        else:
            # Plot deed: PAN is embedded inside VENDOR_ID / PURCHASER_ID
            for id_key, label in (("VENDOR_ID", "விற்பவர்"), ("PURCHASER_ID", "வாங்குபவர்")):
                val = fields.get(id_key, "") or ""
                if not _has_valid_pan(val):
                    missing[id_key + "_PAN"] = (
                        f"{label} PAN எண் (VENDOR_ID-ல் சேர்க்கவும் — "
                        f"IT Rule 114B — ₹10 லட்சத்திற்கு மேல் PAN கட்டாயம்)"
                    )

    # BUG FIX 4: Correct advisory wording — thresholds are >= not just >
    # "மேல்" (above) is wrong at the boundary value; use "மேல் அல்லது சமம்" or ₹X+ phrasing
    notes = []
    if pan_needed:
        notes.append("⚠️ தொகை ₹10 லட்சம் அல்லது அதிகம் — PAN எண் கட்டாயம் (IT Rule 114B)")
    if tds_needed:
        notes.append("⚠️ தொகை ₹50 லட்சம் அல்லது அதிகம் — வாங்குபவர் 1% TDS பிடிக்க வேண்டும் (IT S.194-IA)")

    pan_fields_missing = any("PAN" in k for k in missing)

    # BUG FIX 5: When pan_block=True, add an explicit BLOCK note so Claude cannot
    # misread the advisory notes as permission to proceed to fill_skeleton.
    if pan_needed and pan_fields_missing:
        notes.append("🚫 pan_block=True — PAN எண் இல்லாமல் fill_skeleton செல்லாதே. PAN கேள், பின் validate_fields மீண்டும்.")

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
