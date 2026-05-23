"""
tools/load_skeleton.py
======================
Tool 2 — load_skeleton

Loads the blank JSON template for the detected deed type.
Templates live in tamil-deed-mcp/templates/*.json

Annotation:
  readOnlyHint   = True   (reads template file, no writes)
  idempotentHint = True   (same deed_type → same skeleton)
"""

import json
from mcp.types import Tool, TextContent
from constants import TEMPLATES_DIR

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="prepare_document_template",
    description=(
        "[CALL 2 of 12] ONE TASK: இந்த tool call மட்டும். detect_deed_type result-ஐ deed_type-ஆக pass செய். "
        "சரியான JSON template-ஐ {{PLACEHOLDER}} fields உடன் return செய்யும். "
        "skeleton-ஐ வைத்துக்கொள் — fill_skeleton-க்கு தேவை. "
        "skeleton-ஐ வைத்துக்கொள் — fill_skeleton-க்கு தேவை. tool call முடிந்தவுடன் response முடிந்தது. NEXT CALL (தனி response): extract_fields. பயனருக்கு சொல்ல வேண்டாம் — silent step."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "The type of deed: 'agriculture' or 'plot'."
            }
        },
        "required": ["deed_type"]
    },
    annotations={
        "title":          "Skeleton Loader",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    deed_type     = arguments.get("deed_type", "plot")
    template_file = TEMPLATES_DIR / f"{deed_type}_skeleton.json"

    if not template_file.exists():
        return [TextContent(type="text", text=json.dumps({
            "error": f"Template not found: {template_file}"
        }))]

    with open(template_file, "r", encoding="utf-8") as f:
        skeleton = json.load(f)

    return [TextContent(
        type="text",
        text=json.dumps({
            "skeleton":  skeleton,
            "deed_type": deed_type,
            "message":   f"Skeleton loaded for: {deed_type}"
        }, ensure_ascii=False, indent=2)
    )]
