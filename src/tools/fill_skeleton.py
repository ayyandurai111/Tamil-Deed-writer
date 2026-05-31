"""
tools/fill_skeleton.py
======================
TWO-PHASE processing:

  Phase 1 — fill():              {{PLACEHOLDER}} → value
  Phase 2 — _cleanup_blanks():   blank optional fields → None
                                  blank list entries    → removed
  Phase 3 — _fix_grammar():      Fix ", ," ", ." trailing punctuation
                                  after optional field removal

After Phase 3 the skeleton is clean:
  • No "___________" in output
  • No phantom list rows (blank 3rd owner etc.)
  • No orphan labels or trailing commas/periods
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
        "This tool runs three phases internally: "
        "Phase 1 — replaces all {{PLACEHOLDER}} tokens with field values. "
        "Phase 2 — cleans up: blank optional fields → None, empty list entries → removed. "
        "Phase 3 — grammar fix: removes orphan commas/periods after cleanup. "
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
            "clean_skeleton":          {"type": "object"},
            "filled_skeleton":         {"type": "object"},
            "fields_applied":          {"type": "integer"},
            "placeholders_remaining":  {"type": "integer"},
            "optional_cleaned":        {"type": "integer"},
            "removed_fields":          {"type": "array", "items": {"type": "string"}},
            "message":                 {"type": "string"},
            "next_tool":               {"type": "string", "const": "generate_docx"}
        },
        "required": [
            "clean_skeleton", "filled_skeleton", "fields_applied",
            "placeholders_remaining", "optional_cleaned", "removed_fields",
            "message", "next_tool"
        ],
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
            # Unwrap {"value": "...", "optional": true} skeleton markers
            # If value is blank after fill → return "" so Phase 2 sets it to None
            if set(obj.keys()) <= {"value", "optional"} and "value" in obj:
                filled_val = _replace(obj["value"])
                return filled_val  # "" if blank, actual value if filled
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    filled        = _replace(copy.deepcopy(skeleton))
    filled_str    = json.dumps(filled, ensure_ascii=False)
    remaining     = filled_str.count("{{")
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
    removed = []

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
#  PHASE 3 — GRAMMAR FIX
#  After optional fields are removed, fix orphan punctuation in string values
# ══════════════════════════════════════════════════════════════════════════════

def _fix_grammar(text: str) -> str:
    """
    Fix punctuation artifacts left after optional field removal.

    Examples:
      "நஞ்சை நிலம்,  , 5 தென்னை"   → "நஞ்சை நிலம், 5 தென்னை"
      "ஆழ்துளை கிணறு, ."            → "ஆழ்துளை கிணறு."
      ", நஞ்சை நிலம்"               → "நஞ்சை நிலம்"
      "விவரம்:  "                    → removed by caller (None check)
    """
    if not isinstance(text, str):
        return text

    # Multiple spaces → single space
    text = re.sub(r"  +", " ", text)

    # Multiple consecutive commas (with optional spaces) → single comma
    text = re.sub(r"(,\s*){2,}", ", ", text)

    # Comma + optional spaces + period → period
    text = re.sub(r",\s*\.", ".", text)

    # Semicolon + optional spaces + semicolon → single semicolon
    text = re.sub(r";\s*;+", ";", text)

    # Comma + optional spaces + semicolon → semicolon
    text = re.sub(r",\s*;", ";", text)

    # Leading comma/semicolon at start of string
    text = re.sub(r"^\s*[,;]\s*", "", text)

    # Trailing comma → period
    text = re.sub(r",\s*$", ".", text)

    # "label: ," or "label: ." at end → strip trailing punct after colon
    text = re.sub(r"(:\s*)[,;.]+\s*$", r"\1", text)

    # Clean up any " ." double space before period
    text = re.sub(r"\s+\.", ".", text)

    return text.strip()


def _apply_grammar_fix(obj):
    """Recursively apply _fix_grammar to all string values in the skeleton."""
    if isinstance(obj, str):
        return _fix_grammar(obj)
    if isinstance(obj, dict):
        return {k: _apply_grammar_fix(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_apply_grammar_fix(item) for item in obj]
    return obj


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

    # Phase 3 — fix grammar artifacts (orphan commas/periods)
    clean_skeleton = _apply_grammar_fix(clean_skeleton)

    return [TextContent(
        type="text",
        text=json.dumps({
            "filled_skeleton":        clean_skeleton,   # alias kept for API compatibility
            "clean_skeleton":         clean_skeleton,
            "fields_applied":         fields_applied,
            "placeholders_remaining": remaining,
            "optional_cleaned":       len(removed_fields),
            "removed_fields":         removed_fields,
            "message": (
                f"✅ {fields_applied} fields applied. "
                f"{remaining} placeholders remaining. "
                f"{len(removed_fields)} blank optional fields cleaned. "
                "clean_skeleton-ஐ generate_docx-க்கு pass செய்."
            ),
            "next_tool": "generate_docx"
        }, ensure_ascii=False, indent=2)
    )]
