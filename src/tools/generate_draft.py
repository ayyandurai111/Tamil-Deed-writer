"""
tools/generate_draft.py
=======================
Tool 6 — generate_draft

Claude (the orchestrating AI) writes the Tamil legal prose draft.
This tool receives the Claude-written draft, validates it, and returns
with metadata (draft_id, unfilled count).

ADDED: blank_fields — dynamically inject list of fields that are blank
       into the tool description so Claude knows exactly which phrases to drop.
"""

import re
import json
from datetime import datetime
from mcp.types import Tool, TextContent


def _find_blank_fields(filled_skeleton: dict) -> list[str]:
    """
    Walk filled_skeleton and collect every leaf whose value is blank / empty.
    Returns dotted-path keys (e.g. 'WITNESSES[0].AADHAAR') so Claude knows
    exactly which field is blank, not just an ambiguous key name like 'AADHAAR'.
    """
    blank = []

    def _walk(obj, path: str = ""):
        if isinstance(obj, str):
            if obj.strip() == "" and path:
                blank.append(path.upper())
        elif isinstance(obj, dict):
            for k, v in obj.items():
                child_path = f"{path}.{k}" if path else k
                _walk(v, child_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(filled_skeleton)
    return sorted(set(blank))


def _build_description() -> str:
    return (
        "[STEP 6 of 9] "
        "YOU (Claude) write the full Tamil legal deed draft from filled_skeleton. "
        "Then call this tool with your draft_text. "

        "HOW TO WRITE THE DRAFT: "
        "(1) Use proper legal Tamil prose — not a table, not a list. "
        "(2) Follow this structure: "
        "   • Title + date line "
        "   • தரப்பினர் விவரம் — full sentence for each party "
        "   • முன்னைய உரிமை அறிவிப்பு — prior ownership clause "
        "   • சொத்து விவரம் — property schedule with all 4 boundaries "
        "   • விற்பனை தொகை விவரம் — consideration clause "
        "   • static clauses from skeleton (encumbrance, tax, possession, relinquish) "
        "   • சாட்சிகள் + கையொப்பம் lines "
        "(3) Every value from filled_skeleton MUST appear in the draft. "
        "(4) Do NOT invent values. Use only what is in filled_skeleton. "
        "(5) Language: Tamil prose. English only for proper nouns, numbers. "

        "BLANK FIELDS RULE: "
        "This tool response will contain a 'blank_fields' list. "
        "For each field in that list — remove the entire phrase containing it. "
        "The remaining sentence must read as natural Tamil. "
        "Do NOT write empty gaps. Do NOT invent values. Legal meaning must not change. "
        "If blank_fields is empty — all fields are filled, no cleanup needed. "

        "After YOU write the full draft text, call this tool with: "
        "draft_text = your complete Tamil prose, "
        "filled_skeleton = the skeleton from Step 5, "
        "deed_type = agriculture or plot. "
        "பயனருக்கு சொல்: Draft தயாரானது ✅ — review_draft-க்கு pass செய்கிறேன். "
    )


TOOL_DEFINITION = Tool(
    name="generate_draft",
    description=_build_description(),
    inputSchema={
        "type": "object",
        "properties": {
            "draft_text": {
                "type": "string",
                "description": "The complete Tamil legal deed prose YOU wrote."
            },
            "filled_skeleton": {
                "type": "object",
                "description": "The filled skeleton from Step 5 — used for blank detection and cross-check."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"]
            }
        },
        "required": ["draft_text", "filled_skeleton", "deed_type"]
    },
    annotations={
        "title":          "Draft Receiver",
        "readOnlyHint":   True,
        "idempotentHint": False,
    }
)


async def handle(arguments: dict) -> list[TextContent]:
    draft_text    = arguments.get("draft_text", "")
    filled        = arguments.get("filled_skeleton", {})
    deed_type     = arguments.get("deed_type", "plot")

    # Detect blank fields from this specific filled_skeleton
    blank_fields  = _find_blank_fields(filled)

    # Count unfilled placeholders Claude left in draft
    unfilled_tags  = list(set(re.findall(r"\{\{[A-Z_]+\}\}", draft_text)))
    unfilled_count = len(re.findall(r"\{\{[A-Z_]+\}\}", draft_text))

    draft_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Build blank fields instruction for Claude to act on
    if blank_fields:
        blank_instruction = (
            f"BLANK FIELDS DETECTED {blank_fields} — "
            "IMPORTANT: Rewrite draft_text now. "
            "For each field in this list, remove the entire phrase containing it. "
            "Remaining sentences must read as natural Tamil. "
            "Do NOT leave empty gaps. Legal meaning must not change. "
            "After rewriting, pass to review_draft."
        )
    else:
        blank_instruction = "All fields filled — no cleanup needed. Pass to review_draft."

    return [TextContent(
        type="text",
        text=json.dumps({
            "draft_id":           draft_id,
            "deed_type":          deed_type,
            "draft_text":         draft_text,
            "blank_fields":       blank_fields,
            "blank_instruction":  blank_instruction,
            "unfilled_count":     unfilled_count,
            "unfilled_tags":      unfilled_tags,
            "message": (
                f"✅ Draft received ({draft_id}). "
                f"blank_fields: {blank_fields}. "
                f"{unfilled_count} unfilled {{{{TAGS}}}} remaining. "
                "Read blank_instruction and act on it before review_draft."
            )
        }, ensure_ascii=False, indent=2)
    )]
