"""
tools/detect_deed_type.py
=========================
Tool 1 — detect_deed_type

Determines whether the user prompt describes an agriculture land deed
or a plot/site deed by scoring keyword matches.

Annotation:
  readOnlyHint   = True   (no data is written or modified)
  idempotentHint = True   (same prompt always returns same result)
"""

import json
from mcp.types import Tool, TextContent

# ── Tool definition (returned in list_tools) ───────────────────────────────────
TOOL_DEFINITION = Tool(
    name="detect_deed_type",
    description=(
        "[STEP 1 of 9] பயனரின் prompt-ஐ படித்து deed வகை கண்டுபிடி. "
        "user_prompt = பயனரின் முழு raw text. "
        "Returns deed_type: 'agriculture' (விவசாய நிலம்) or 'plot' (மனை நிலம்). "
        "Result-ஐ வைத்துக்கொள் — load_skeleton-க்கு தேவை. "
        "பயனருக்கு சொல்: நிலம் வகை கண்டுபிடிக்கப்பட்டது."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "user_prompt": {
                "type": "string",
                "description": "The raw user prompt describing the property."
            }
        },
        "required": ["user_prompt"]
    },
    # ── Annotations ───────────────────────────────────────────────────────────
    annotations={
        "title":         "Deed Type Detector",
        "readOnlyHint":  True,    # reads only — no writes
        "idempotentHint": True,   # deterministic
    }
)

# ── Keyword banks ─────────────────────────────────────────────────────────────
_AGRICULTURE_KW = [
    "விவசாய", "நஞ்சை", "புஞ்சை", "ஏக்கர்", "சென்ட்", "survey",
    "பட்டா", "சிட்டா", "அடங்கல", "fmb", "கால்வாய்", "நீர்வரி",
    "kist", "a-register", "acre", "cent", "nanjai", "punjai",
    "agriculture", "farm", "paddy", "field", "crop", "புல எண்",
    "நில", "ஏரி", "கிணறு", "ஆழ்துளை"
]

_PLOT_KW = [
    "மனை", "plot", "sq ft", "sqft", "square feet", "door no",
    "ward", "வார்டு", "கதவு எண்", "காலிமனை", "site", "வீட்டு மனை",
    "residential", "urban", "நகர்ப்புற", "தெரு", "layout"
]


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    prompt = arguments.get("user_prompt", "").lower()

    ag_score   = sum(1 for kw in _AGRICULTURE_KW if kw in prompt)
    plot_score = sum(1 for kw in _PLOT_KW        if kw in prompt)
    deed_type  = "agriculture" if ag_score >= plot_score else "plot"

    return [TextContent(
        type="text",
        text=json.dumps({
            "deed_type":         deed_type,
            "agriculture_score": ag_score,
            "plot_score":        plot_score,
            "message":           f"Detected deed type: {deed_type}"
        }, ensure_ascii=False, indent=2)
    )]
