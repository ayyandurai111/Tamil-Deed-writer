"""
tools/fill_skeleton.py
======================
Tool 5 — fill_skeleton

Walks the skeleton JSON tree and replaces every {{PLACEHOLDER}}
with the corresponding value from the fields dict.

FIXES:
  1. if val is not None  (was: if val — skipped 0, False, "0")
  2. After replace, all remaining {{...}} placeholders → "" (blank)
     so docx never shows raw placeholder text
  3. Keys normalized to UPPER before matching

Annotation:
  readOnlyHint   = True
  idempotentHint = True
"""

import json
import re
import copy
from mcp.types import Tool, TextContent

TOOL_DEFINITION = Tool(
    name="fill_skeleton",
    description=(
        "[STEP 5 of 9] skeleton template-இல் உள்ள எல்லா {{PLACEHOLDER}}-ஐயும் fields-இல் உள்ள values-ஆல் மாற்று. "
        "skeleton = Step 2 load_skeleton result. fields = validate_fields pass ஆன முழு dict. "
        "placeholders_remaining > 0 இருந்தாலும் தொடர் — optional fields unfilled-ஆக இருக்கலாம். "
        "filled_skeleton-ஐ generate_draft-க்கு pass செய். "
        "பயனருக்கு சொல்: பத்திர வரைவு தயாரிக்கிறேன்..."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "skeleton": {
                "type": "object",
                "description": "The skeleton JSON returned by load_skeleton."
            },
            "fields": {
                "type": "object",
                "description": (
                    "Flat key-value dict of field values. "
                    "Keys match the {{PLACEHOLDER}} names (without braces), e.g. "
                    "{'VENDOR_NAME': 'ராமன்', 'TOTAL_AMOUNT': '4500000'}."
                )
            }
        },
        "required": ["skeleton", "fields"]
    },
    annotations={
        "title":          "Skeleton Filler",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ── Core fill function ─────────────────────────────────────────────────────────

def fill(skeleton: dict, fields: dict) -> dict:
    """
    Recursively replace {{KEY}} placeholders throughout the skeleton.

    FIX 1: use `is not None` — so "0", False, "" are still replaced
    FIX 2: normalize keys to UPPER before matching
    FIX 3: after all replacements, erase any remaining {{...}} → ""
    """

    # Normalize all keys to UPPERCASE so Claude's key-case doesn't matter
    normalized = {}
    for k, v in fields.items():
        upper_key = str(k).strip().upper()
        # Skip null-like values — treat as missing
        if v in (None, "null", "None", "undefined", ""):
            normalized[upper_key] = None
        else:
            normalized[upper_key] = str(v).strip()

    def _replace(obj):
        if isinstance(obj, str):
            # FIX 1: replace only when value is not None
            for key, val in normalized.items():
                if val is not None:
                    obj = obj.replace(f"{{{{{key}}}}}", val)
            # FIX 3: erase any remaining unfilled placeholders → blank string
            obj = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", obj)
            return obj
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    filled = _replace(copy.deepcopy(skeleton))

    # Count stats BEFORE erasing (already erased above, so count 0 remaining)
    filled_str     = json.dumps(filled, ensure_ascii=False)
    remaining      = filled_str.count("{{")   # should be 0 after fix 3
    fields_applied = sum(1 for v in normalized.values() if v is not None)

    return filled, fields_applied, remaining


# ── Handler ────────────────────────────────────────────────────────────────────

async def handle(arguments: dict) -> list[TextContent]:
    skeleton = arguments.get("skeleton", {})
    fields   = arguments.get("fields",   {})

    filled, fields_applied, remaining = fill(skeleton, fields)

    return [TextContent(
        type="text",
        text=json.dumps({
            "filled_skeleton":        filled,
            "fields_applied":         fields_applied,
            "placeholders_remaining": remaining,
            "message": (
                f"✅ {fields_applied} fields applied. "
                f"{remaining} placeholders still unfilled (blanked out in output)."
            )
        }, ensure_ascii=False, indent=2)
    )]
