"""
tools/fill_skeleton.py
======================
Tool 5 — fill_skeleton  (STEP 5 of 8)

TWO-PHASE processing:

  Phase 1 — fill():              {{PLACEHOLDER}} → value
  Phase 2 — _cleanup_blanks():   blank optional fields → None
                                  blank list entries    → removed

After Phase 2 the skeleton is clean:
  • No "___________" in output
  • No phantom list rows (blank 3rd owner etc.)
  • generate_docx receives clean, fully resolved data
"""

import json
import re
import copy
from mcp.types import Tool, TextContent
from constants import OPTIONAL_FIELDS

TOOL_DEFINITION = Tool(
    name="fill_skeleton",
    description=(
        "[CALL 6 of 8] ONE TASK: call this tool only. "
        "Pass skeleton (CALL 2 result) and fields (validate_fields passed dict). "
        "This tool runs two phases internally: "
        "Phase 1 — replaces all {{PLACEHOLDER}} tokens with field values. "
        "Phase 2 — cleans up: blank optional fields → None, empty list entries → removed. "
        "IMPORTANT: store only the 'clean_skeleton' key from the result. "
        "Pass clean_skeleton to generate_docx (CALL 7). "
        "Tell user: 'பத்திர வரைவு தயாரிக்கிறேன்...' "
        "Next separate response: CALL 7 generate_docx."
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
                    "Keys match the {{PLACEHOLDER}} names (UPPERCASE). "
                    "e.g. {'VENDOR_NAME': 'ராமன்', 'TOTAL_AMOUNT': '4500000'}."
                )
            }
        },
        "required": ["skeleton", "fields"],
        "additionalProperties": False
    },
    outputSchema={
        "type": "object",
        "properties": {
            "clean_skeleton": {
                "type": "object",
                "description": "The fully filled and cleaned skeleton JSON. Pass this — not filled_skeleton — to generate_docx."
            },
            "filled_skeleton": {
                "type": "object",
                "description": "Alias for clean_skeleton — kept for API backward compatibility."
            },
            "fields_applied": {
                "type": "integer",
                "description": "Number of {{PLACEHOLDER}} tokens that were successfully replaced with values."
            },
            "placeholders_remaining": {
                "type": "integer",
                "description": "Number of {{PLACEHOLDER}} tokens still unfilled (should be 0 if can_generate was true)."
            },
            "optional_cleaned": {
                "type": "integer",
                "description": "Number of blank optional fields removed during Phase 2 cleanup."
            },
            "removed_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of optional field keys that were blanked and removed."
            },
            "message": {
                "type": "string",
                "description": "Summary: fields applied, placeholders remaining, optional fields cleaned."
            },
            "next_tool": {
                "type": "string",
                "const": "generate_docx",
                "description": "Always call generate_docx next (CALL 7) — pass clean_skeleton."
            }
        },
        "required": ["clean_skeleton", "filled_skeleton", "fields_applied", "placeholders_remaining", "optional_cleaned", "removed_fields", "message", "next_tool"],
        "additionalProperties": False
    },
    annotations={
        "title":          "Skeleton Filler + Cleanup",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — PLACEHOLDER REPLACEMENT
# ══════════════════════════════════════════════════════════════════════════════

def fill(skeleton: dict, fields: dict) -> tuple[dict, int, int]:
    """
    Recursively replace {{KEY}} placeholders throughout the skeleton.
    Remaining unfilled {{...}} → "" (blank string, cleaned in Phase 2).
    """
    normalized = {}
    for k, v in fields.items():
        upper_key = str(k).strip().upper()
        if v in (None, "null", "None", "undefined", ""):
            normalized[upper_key] = None
        else:
            normalized[upper_key] = str(v).strip()

    def _replace(obj):
        if isinstance(obj, str):
            for key, val in normalized.items():
                if val is not None:
                    obj = obj.replace(f"{{{{{key}}}}}", val)
            # Erase any remaining unfilled placeholders → blank string
            obj = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", obj)
            return obj
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    filled = _replace(copy.deepcopy(skeleton))
    filled_str     = json.dumps(filled, ensure_ascii=False)
    remaining      = filled_str.count("{{")
    fields_applied = sum(1 for v in normalized.values() if v is not None)
    return filled, fields_applied, remaining


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — BLANK OPTIONAL FIELD CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

def _cleanup_blanks(filled: dict) -> tuple[dict, list]:
    """
    Walk the filled skeleton after Phase 1.

    Rules:
      1. Any leaf string that is "" (blank after placeholder erasure) → None.
         This signals generate_docx to skip the field entirely — no "___".

      2. List entries where the primary identity key is blank → removed.
         Handles: chain_of_title (owner blank), witnesses (name blank).

    Returns:
      cleaned_skeleton : dict
      removed_fields   : list[str]   — paths of blanked/removed fields
    """
    deed_type = filled.get("type", "agriculture")
    optional  = OPTIONAL_FIELDS.get(deed_type, frozenset())
    removed   = []

    # Primary identity keys for list-entry removal
    _LIST_PRIMARY_KEYS = ("owner", "name")

    def _clean(obj, path: str = ""):
        if isinstance(obj, str):
            stripped = obj.strip()
            if stripped == "":
                removed.append(path)
                return None
            return stripped

        if isinstance(obj, dict):
            return {k: _clean(v, f"{path}.{k}" if path else k) for k, v in obj.items()}

        if isinstance(obj, list):
            result = []
            for i, item in enumerate(obj):
                item_path = f"{path}[{i}]"
                if isinstance(item, dict):
                    # Check if the primary identity key of this entry is blank
                    primary_blank = any(
                        k in item and (not item[k] or str(item[k]).strip() == "")
                        for k in _LIST_PRIMARY_KEYS
                    )
                    if primary_blank:
                        removed.append(f"{item_path} (blank entry removed)")
                        continue
                    result.append({k: _clean(v, f"{item_path}.{k}") for k, v in item.items()})
                else:
                    cleaned = _clean(item, item_path)
                    if cleaned is not None:
                        result.append(cleaned)
            return result

        return obj

    cleaned = _clean(copy.deepcopy(filled))
    return cleaned, removed


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    skeleton = arguments.get("skeleton", {})
    fields   = arguments.get("fields",   {})

    # Phase 1 — replace placeholders
    filled, fields_applied, remaining = fill(skeleton, fields)

    # Phase 2 — cleanup blank optional fields
    clean_skeleton, removed_fields = _cleanup_blanks(filled)

    return [TextContent(
        type="text",
        text=json.dumps({
            "filled_skeleton":       clean_skeleton,   # alias kept for API compatibility
            "clean_skeleton":        clean_skeleton,
            "fields_applied":        fields_applied,
            "placeholders_remaining": remaining,
            "optional_cleaned":      len(removed_fields),
            "removed_fields":        removed_fields,
            "message": (
                f"✅ {fields_applied} fields applied. "
                f"{remaining} placeholders remaining. "
                f"{len(removed_fields)} blank optional fields cleaned. "
                "clean_skeleton-ஐ generate_docx-க்கு pass செய்."
            ),
            "next_tool": "generate_docx"
        }, ensure_ascii=False, indent=2)
    )]
