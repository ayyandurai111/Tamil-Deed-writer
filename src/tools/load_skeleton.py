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
    name="load_skeleton",
    description=(
        "[CALL 2 of 12] ONE TASK: call this tool only. "
        "Pass deed_type from CALL 1 result. "
        "Returns the JSON template with {{PLACEHOLDER}} fields. "
        "Store the returned skeleton — needed for fill_skeleton (CALL 6). "
        "Silent step — nothing to tell user. "
        "Next separate response: CALL 3 extract_fields."
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
    outputSchema={
        "type": "object",
        "properties": {
            "skeleton": {
                "type": "object",
                "description": "The blank JSON template with {{PLACEHOLDER}} fields for the deed type."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "The deed type the skeleton was loaded for."
            },
            "message": {
                "type": "string",
                "description": "Confirmation message."
            },
            "next_tool": {
                "type": "string",
                "const": "extract_fields",
                "description": "Always call extract_fields next (CALL 3)."
            }
        },
        "required": ["skeleton", "deed_type", "message", "next_tool"]
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
            "error": f"Template not found: {template_file}",
            "next_tool": None
        }))]

    with open(template_file, "r", encoding="utf-8") as f:
        skeleton = json.load(f)

    return [TextContent(
        type="text",
        text=json.dumps({
            "skeleton":  skeleton,
            "deed_type": deed_type,
            "message":   f"Skeleton loaded for: {deed_type}",
            "next_tool": "extract_fields"
        }, ensure_ascii=False, indent=2)
    )]
