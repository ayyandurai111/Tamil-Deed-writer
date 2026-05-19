"""
tools/fill_skeleton.py
======================
Tool 5 — fill_skeleton

Walks the skeleton JSON tree and replaces every {{PLACEHOLDER}}
with the corresponding value from the fields dict.

Annotation:
  readOnlyHint   = True   (produces a new object — no file writes)
  idempotentHint = True   (same skeleton + fields → same result)
"""

import json
import copy
from mcp.types import Tool, TextContent

# ── Tool definition ────────────────────────────────────────────────────────────
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
    """Recursively replace {{KEY}} placeholders throughout the skeleton."""

    def _replace(obj):
        if isinstance(obj, str):
            for key, val in fields.items():
                if val:
                    obj = obj.replace(f"{{{{{key}}}}}", str(val))
            return obj
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    filled = _replace(copy.deepcopy(skeleton))

    # Count how many placeholders remain unfilled
    filled_str      = json.dumps(filled, ensure_ascii=False)
    remaining       = filled_str.count("{{")
    fields_applied  = sum(1 for v in fields.values() if v)

    return filled, fields_applied, remaining


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    skeleton = arguments.get("skeleton", {})
    fields   = arguments.get("fields",   {})

    filled, fields_applied, remaining = fill(skeleton, fields)

    return [TextContent(
        type="text",
        text=json.dumps({
            "filled_skeleton":       filled,
            "fields_applied":        fields_applied,
            "placeholders_remaining": remaining,
            "message": (
                f"✅ {fields_applied} fields applied. "
                f"{remaining} placeholders still unfilled."
            )
        }, ensure_ascii=False, indent=2)
    )]
