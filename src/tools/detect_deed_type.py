"""
tools/detect_deed_type.py
=========================
Tool 1 — detect_deed_type

Claude (the orchestrating AI) reads the user prompt and determines deed type.
This tool receives Claude's determination, validates it, and returns it.

No keyword scoring. Claude reads context, not keywords.

Annotation:
  readOnlyHint   = True
  idempotentHint = True
"""

import json
from mcp.types import Tool, TextContent

TOOL_DEFINITION = Tool(
    name="detect_deed_type",
    description=(
        "[CALL 1 of 12] ONE TASK: இந்த tool call மட்டும்.  "
        "YOU (Claude) read the user prompt and determine the deed type yourself. "
        "Then call this tool with your determination. "

        "HOW TO DETERMINE: "
        "(1) Agriculture = விவசாய நிலம், ஏக்கர், நஞ்சை, புஞ்சை, survey no, பட்டா, "
        "FMB, கால்வாய், paddy, farm, acre, cent, crop. "
        "(2) Plot = மனை, வீட்டு மனை, site, sq ft, sqft, square feet, door no, "
        "ward, வார்டு, கதவு எண், layout, residential, urban. "
        "(3) Context wins over keywords — "
        "'2400 sqft வீட்டுமனை' → plot even without explicit 'plot' word. "
        "(4) If unclear → default to plot. "

        "tool call முடிந்தவுடன் response முடிந்தது. "
        "NEXT CALL (தனி response): load_skeleton. "
        "பயனருக்கு சொல்: '[deed_type] பத்திரம் தயாரிக்கிறோம்.'"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "The deed type YOU determined from the user prompt."
            },
            "reason": {
                "type": "string",
                "description": "Brief reason for your determination (e.g. 'user mentioned ஏக்கர் and நஞ்சை')."
            }
        },
        "required": ["deed_type"]
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

    return [TextContent(
        type="text",
        text=json.dumps({
            "deed_type": deed_type,
            "label":     label,
            "reason":    reason,
            "message":   f"Deed type confirmed: {deed_type} ({label})"
        }, ensure_ascii=False, indent=2)
    )]
