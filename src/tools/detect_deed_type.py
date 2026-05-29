"""
tools/detect_deed_type.py
=========================
Tool 1 — detect_deed_type

The orchestrating AI reads the user prompt and determines deed type.
This tool receives the AI's determination, validates it, and returns it.

No keyword scoring. The AI reads context, not keywords.

Annotation:
  readOnlyHint   = True
  idempotentHint = True
"""

import json
from mcp.types import Tool, TextContent

TOOL_DEFINITION = Tool(
    name="detect_deed_type",
    description=(
        "[CALL 1 of 12] ONE TASK: call this tool only. "
        "Before calling: YOU read the user prompt and determine the deed type yourself. "

        "DETERMINATION RULES: "
        "Agriculture → keywords: விவசாய நிலம், ஏக்கர், நஞ்சை, புஞ்சை, survey no, பட்டா, FMB, acre, cent, paddy, crop. "
        "Plot        → keywords: மனை, site, sqft, sq ft, door no, ward, layout, residential, urban. "
        "Context wins over keywords — '2400 sqft வீட்டுமனை' is plot even without the word 'plot'. "
        "If unclear → default to plot. "

        "After tool returns: tell user '[deed_type label] பத்திரம் தயாரிக்கிறோம்.' "
        "Next separate response: CALL 2 load_skeleton."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "The deed type YOU (the AI) determined from the user prompt."
            },
            "reason": {
                "type": "string",
                "description": "Brief reason for your determination (e.g. 'user mentioned ஏக்கர் and நஞ்சை')."
            }
        },
        "required": ["deed_type"],
        "additionalProperties": False
    },
    outputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Validated deed type: 'agriculture' or 'plot'."
            },
            "label": {
                "type": "string",
                "description": "Tamil label: 'விவசாய நிலம்' or 'மனை நிலம்'."
            },
            "reason": {
                "type": "string",
                "description": "Reason the deed type was chosen."
            },
            "message": {
                "type": "string",
                "description": "Confirmation message."
            },
            "next_tool": {
                "type": "string",
                "const": "load_skeleton",
                "description": "Always call load_skeleton next (CALL 2)."
            }
        },
        "required": ["deed_type", "label", "reason", "message", "next_tool"],
        "additionalProperties": False
    },
    annotations={
        "title":          "Deed Type Validator",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


async def handle(arguments: dict) -> list[TextContent]:
    deed_type = arguments.get("deed_type", "plot")
    reason    = arguments.get("reason", "")

    # Validate
    if deed_type not in ("agriculture", "plot"):
        deed_type = "plot"

    label = "விவசாய நிலம்" if deed_type == "agriculture" else "மனை நிலம்"

    # Returns TextContent with JSON — server.py automatically promotes this
    # to structuredContent when outputSchema is defined on the tool.
    return [TextContent(
        type="text",
        text=json.dumps({
            "deed_type": deed_type,
            "label":     label,
            "reason":    reason,
            "message":   f"Deed type confirmed: {deed_type} ({label})",
            "next_tool": "load_skeleton"
        }, ensure_ascii=False, indent=2)
    )]
