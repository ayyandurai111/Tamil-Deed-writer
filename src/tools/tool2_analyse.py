"""
tools/tool2_analyse.py
======================
Tool 2 — analyse

100% Pure Logic — Zero AI involvement.

Receives clean validated fields from Tool 1 (extract).
Runs internally:
  1. detect_deed_type  — keyword logic (no AI)
  2. load_skeleton     — file read
  3. validate_fields   — PAN/TDS legal rules

Returns:
  deed_type, skeleton, pan_block, tds_required, can_proceed
"""

import json
import re
from pathlib import Path
from mcp.types import Tool, TextContent
from constants import CRITICAL_FIELDS, TEMPLATES_DIR, PAN_THRESHOLD, TDS_THRESHOLD

# ── Keyword sets for deed type detection ───────────────────────────────────────
_AGRICULTURE_KEYWORDS = {
    "விவசாய", "நஞ்சை", "புஞ்சை", "ஏக்கர்", "cent", "acre",
    "survey", "பட்டா", "fmb", "paddy", "crop", "நிலம்",
    "புல எண்", "survey no", "கிராமம்", "revenue"
}
_PLOT_KEYWORDS = {
    "மனை", "site", "sqft", "sq ft", "door no", "ward",
    "layout", "residential", "urban", "வீட்டுமனை", "plot"
}

_PAN_RE = re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])")


TOOL_DEFINITION = Tool(
    name="analyse",
    description=(
    "WHEN TO CALL: When Tool 1 (extract) returns ready_for_analyse=true. "
    "DO NOT call before that condition is met. "

    "POSITION: Tool 2 of 3. Always called after Tool 1. "

    "WHAT THIS TOOL DOES: 100% Logic — no AI work. "
    "Internally: detects deed type from keywords, loads correct JSON template, "
    "checks PAN/TDS legal rules, validates all critical fields. "

    "PARAMETERS: "
    "fields = the 'fields' object from Tool 1 result (not user text). "
    "deed_type = the 'deed_type' string from Tool 1 result. "

    "AFTER TOOL RETURNS — follow exactly one branch: "
    "IF pan_block=true → ask user in Tamil for VENDOR_PAN and PURCHASER_PAN. "
    "  Loop: call Tool 1 again with PAN values → then Tool 2 again. "
    "  NEVER call Tool 3 when pan_block=true. "
    "IF can_proceed=false (and pan_block=false) → ask user in Tamil for missing_critical fields. "
    "  Loop: call Tool 1 again → then Tool 2 again. "
    "IF can_proceed=true AND pan_block=false → "
    "  IF tds_required=true → send TDS advisory in Tamil first (separate response). "
    "  Then call Tool 3 (build)."
),
    inputSchema={
        "type": "object",
        "properties": {
            "fields": {
                "type": "object",
                "description": "Clean validated fields dict from Tool 1 extract output."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "deed_type from Tool 1 extract output."
            }
        },
        "required": ["fields", "deed_type"],
        "additionalProperties": False
    },
    outputSchema={
        "type": "object",
        "properties": {
            "deed_type":       {"type": "string"},
            "deed_label":      {"type": "string", "description": "Tamil label: விவசாய நிலம் / மனை நிலம்"},
            "skeleton":        {"type": "object", "description": "Loaded JSON template with {{PLACEHOLDER}} fields."},
            "missing_critical":{"type": "object", "description": "Missing critical fields with Tamil labels."},
            "missing_count":   {"type": "integer"},
            "pan_required":    {"type": "boolean"},
            "tds_required":    {"type": "boolean"},
            "pan_block":       {"type": "boolean", "description": "HARD BLOCK — do not call build until false."},
            "pan_tds_notes":   {"type": "array", "items": {"type": "string"}},
            "can_proceed":     {"type": "boolean", "description": "True = all fields present + no pan_block. Safe to call Tool 3 (build)."},
            "message":         {"type": "string"},
            "next_tool":       {"type": "string"}
        },
        "required": ["deed_type","deed_label","skeleton","missing_critical","missing_count",
                     "pan_required","tds_required","pan_block","pan_tds_notes","can_proceed","message","next_tool"],
        "additionalProperties": False
    },
    annotations={"title": "Deed Analyser (Pure Logic)", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC 1: detect deed type from fields (keyword-free — fields already extracted)
# Just trust deed_type passed from Tool 1
# ══════════════════════════════════════════════════════════════════════════════

def _deed_label(deed_type: str) -> str:
    return "விவசாய நிலம்" if deed_type == "agriculture" else "மனை நிலம்"


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC 2: load skeleton from file
# ══════════════════════════════════════════════════════════════════════════════

def _load_skeleton(deed_type: str) -> dict:
    template_file = TEMPLATES_DIR / f"{deed_type}_skeleton.json"
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")
    with open(template_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIC 3: PAN/TDS legal validation
# ══════════════════════════════════════════════════════════════════════════════

def _has_valid_pan(value: str) -> bool:
    return bool(_PAN_RE.search((value or "").upper()))


def _run_validation(deed_type: str, fields: dict) -> dict:
    critical = CRITICAL_FIELDS.get(deed_type, {})
    missing = {}
    for key, label in critical.items():
        val = fields.get(key.upper(), "")
        if not val or str(val).startswith("{{"):
            missing[key.upper()] = label

    # Amount check
    amount_raw = str(fields.get("TOTAL_AMOUNT", "0"))
    amount_clean = re.sub(r"[^\d]", "", amount_raw)
    try:
        amount     = int(amount_clean) if amount_clean else 0
        pan_needed = amount >= PAN_THRESHOLD
        tds_needed = amount >= TDS_THRESHOLD
    except (ValueError, TypeError):
        pan_needed = False
        tds_needed = False

    # PAN presence check
    if pan_needed:
        if deed_type == "agriculture":
            for pan_key, fallback_key, role in (
                ("VENDOR_PAN",    "VENDOR_AADHAAR",    "விற்பவர்"),
                ("PURCHASER_PAN", "PURCHASER_AADHAAR", "வாங்குபவர்"),
            ):
                pan_val      = fields.get(pan_key, "") or ""
                fallback_val = fields.get(fallback_key, "") or ""
                if not _has_valid_pan(pan_val) and not _has_valid_pan(fallback_val):
                    missing[pan_key] = (
                        f"{role} PAN எண் (IT Rule 114B — ₹10 லட்சம்+ PAN கட்டாயம்)"
                    )
        else:
            for id_key, label in (("VENDOR_ID", "விற்பவர்"), ("PURCHASER_ID", "வாங்குபவர்")):
                val = fields.get(id_key, "") or ""
                if not _has_valid_pan(val):
                    missing[id_key + "_PAN"] = (
                        f"{label} PAN எண் (IT Rule 114B — ₹10 லட்சம்+ PAN கட்டாயம்)"
                    )

    pan_fields_missing = any("PAN" in k for k in missing)
    notes = []
    if pan_needed:
        notes.append("⚠️ தொகை ₹10 லட்சம்+ — PAN எண் கட்டாயம் (IT Rule 114B)")
    if tds_needed:
        notes.append("⚠️ தொகை ₹50 லட்சம்+ — வாங்குபவர் 1% TDS பிடிக்க வேண்டும் (IT S.194-IA)")
    if pan_needed and pan_fields_missing:
        notes.append("🚫 pan_block=True — PAN இல்லாமல் build செல்லாதே.")

    return {
        "missing_critical":  missing,
        "missing_count":     len(missing),
        "pan_required":      pan_needed,
        "tds_required":      tds_needed,
        "pan_block":         pan_needed and pan_fields_missing,
        "can_proceed":       len(missing) == 0,
        "pan_tds_notes":     notes,
    }


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    fields    = arguments.get("fields", {})
    deed_type = arguments.get("deed_type", "plot")

    # Step 1: load skeleton
    try:
        skeleton = _load_skeleton(deed_type)
    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": str(e), "next_tool": None
        }))]

    # Step 2: legal validation
    validation = _run_validation(deed_type, fields)

    # Step 3: decide next_tool
    if validation["pan_block"]:
        next_tool = "user:ask_pan_number"
    elif validation["can_proceed"]:
        next_tool = "build"
    else:
        next_tool = "user:ask_missing_fields"

    return [TextContent(
        type="text",
        text=json.dumps({
            "deed_type":        deed_type,
            "deed_label":       _deed_label(deed_type),
            "skeleton":         skeleton,
            **validation,
            "message": (
                f"{'✅' if validation['can_proceed'] else '❌'} "
                f"deed_type={deed_type}. "
                f"{validation['missing_count']} critical missing. "
                f"pan_block={validation['pan_block']}. "
                f"next_tool={next_tool}"
            ),
            "next_tool": next_tool
        }, ensure_ascii=False, indent=2)
    )]
