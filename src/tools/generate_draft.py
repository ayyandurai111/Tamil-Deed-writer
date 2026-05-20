"""
tools/generate_draft.py
=======================
Tool 6 — generate_draft

Claude (the orchestrating AI) writes the Tamil legal prose draft.
This tool receives the Claude-written draft, validates it, and returns
with metadata (draft_id, unfilled count).

No f-string templates. Claude writes proper legal Tamil.

Annotation:
  readOnlyHint   = True
  idempotentHint = False  (Claude's prose may vary slightly)
"""

import re
import json
from datetime import datetime
from mcp.types import Tool, TextContent

TOOL_DEFINITION = Tool(
    name="generate_draft",
    description=(
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
        "(4) If a value is still '___' → write it as _______________ (blank line). "
        "(5) Do NOT invent values. Use only what is in filled_skeleton. "
        "(6) Language: Tamil prose. English only for proper nouns, numbers. "

        "After YOU write the full draft text, call this tool with: "
        "draft_text = your complete Tamil prose, "
        "filled_skeleton = the skeleton from Step 5, "
        "deed_type = agriculture or plot. "

        "பயனருக்கு சொல்: Draft தயாரானது ✅ — 3 அடுக்கு சரிபார்ப்பு செய்கிறேன். "
        "draft_text + filled_skeleton + deed_type → review_draft-க்கு pass செய்."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "draft_text": {
                "type": "string",
                "description": "The complete Tamil legal deed prose YOU wrote."
            },
            "filled_skeleton": {
                "type": "object",
                "description": "The filled skeleton from Step 5 — used for placeholder cross-check."
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

    # Count unfilled placeholders Claude left in draft
    unfilled_tags = list(set(re.findall(r"\{\{[A-Z_]+\}\}", draft_text)))
    unfilled_count = len(re.findall(r"\{\{[A-Z_]+\}\}", draft_text))

    # Count blank lines (___) as a quality hint
    blank_count = draft_text.count("_______________")

    draft_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return [TextContent(
        type="text",
        text=json.dumps({
            "draft_id":       draft_id,
            "deed_type":      deed_type,
            "draft_text":     draft_text,
            "unfilled_count": unfilled_count,
            "unfilled_tags":  unfilled_tags,
            "blank_count":    blank_count,
            "message": (
                f"✅ Draft received ({draft_id}). "
                f"{unfilled_count} unfilled {{{{TAGS}}}}, {blank_count} blank lines. "
                "Pass draft_text + filled_skeleton + deed_type to review_draft."
            )
        }, ensure_ascii=False, indent=2)
    )]
