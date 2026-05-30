"""
tools/tool3_build.py
====================
Tool 3 — build

100% Pure Logic — Zero AI involvement.

Receives:
  - fields       from Tool 1 (extract)
  - skeleton     from Tool 2 (analyse)
  - deed_type    from Tool 2 (analyse)
  - filename_prefix (optional)

Runs internally:
  1. fill_skeleton   — {{PLACEHOLDER}} → values
  2. cleanup_blanks  — remove empty optional fields
  3. generate_docx   — render .docx (Latha 12pt)
  4. list_files      — return download URL

Returns:
  success, download_url, filename
"""

import json
from mcp.types import Tool, TextContent
from tools.fill_skeleton import fill, _cleanup_blanks
from tools.generate_docx import handle as _generate_handle
from tools.list_output_files import handle as _list_handle

TOOL_DEFINITION = Tool(
    name="build",
    description=(
    "WHEN TO CALL: When Tool 2 (analyse) returns can_proceed=true AND pan_block=false. "
    "Both conditions must be true. NEVER call if pan_block=true. "

    "POSITION: Tool 3 of 3. Final tool in workflow. "

    "WHAT THIS TOOL DOES: 100% Logic — no AI work. "
    "Internally: fills template placeholders, removes empty optional fields, "
    "generates .docx with Latha Tamil font, returns download URL. "

    "PARAMETERS: "
    "fields = the 'fields' object from Tool 1 result. "
    "skeleton = the 'skeleton' object from Tool 2 result. "
    "deed_type = from Tool 2 result ('agriculture' or 'plot'). "
    "filename_prefix = 'vendorname_purchasername' format (e.g. 'ramasamy_murugan'). "

    "AFTER TOOL RETURNS — follow exactly one branch: "
    "IF success=true → send Tamil message with download_url: "
    "  '✅ பத்திரம் தயாரானது! 📥 [download_url] "
    "   ⚠️ மாதிரி வரைவு மட்டுமே. வழக்கறிஞர் / சார்பதிவாளர் ஆலோசனை பெறவும்.' "
    "IF success=false → send Tamil error message and ask user to retry."
),
    inputSchema={
        "type": "object",
        "properties": {
            "fields": {
                "type": "object",
                "description": "Clean validated fields from Tool 1 (extract) output."
            },
            "skeleton": {
                "type": "object",
                "description": "JSON template from Tool 2 (analyse) output."
            },
            "deed_type": {
                "type": "string",
                "enum": ["agriculture", "plot"],
                "description": "Deed type from Tool 2 output."
            },
            "filename_prefix": {
                "type": "string",
                "description": "vendorname_purchasername format. e.g. 'ramasamy_murugan'.",
                "default": "deed"
            }
        },
        "required": ["fields", "skeleton", "deed_type"],
        "additionalProperties": False
    },
    outputSchema={
        "type": "object",
        "properties": {
            "success":      {"type": "boolean"},
            "download_url": {"type": ["string", "null"]},
            "filename":     {"type": ["string", "null"]},
            "fields_applied":       {"type": "integer"},
            "placeholders_remaining": {"type": "integer"},
            "optional_cleaned":     {"type": "integer"},
            "error":        {"type": ["string", "null"]},
            "message":      {"type": "string"},
            "next_tool":    {"type": "null"}
        },
        "required": ["success","download_url","filename","fields_applied",
                     "placeholders_remaining","optional_cleaned","error","message","next_tool"],
        "additionalProperties": False
    },
    annotations={"title": "Deed Builder (Pure Logic)", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}
)


async def handle(arguments: dict) -> list[TextContent]:
    fields          = arguments.get("fields", {})
    skeleton        = arguments.get("skeleton", {})
    deed_type       = arguments.get("deed_type", "plot")
    filename_prefix = arguments.get("filename_prefix", "deed")

    # ── Guard: skeleton must not be empty ─────────────────────────────────────
    if not skeleton or len(skeleton) < 3:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "download_url": None,
                "filename": None,
                "fields_applied": 0,
                "placeholders_remaining": 0,
                "optional_cleaned": 0,
                "error": "skeleton காலியாக உள்ளது — Tool 2 (analyse) முடிந்த பிறகே Tool 3 அழைக்கவும்.",
                "message": "❌ skeleton இல்லை — analyse tool முதலில் அழைக்கவும்.",
                "next_tool": None
            }, ensure_ascii=False, indent=2)
        )]

    # ── Step 1: fill {{PLACEHOLDER}} tokens ──────────────────────────────────
    filled, fields_applied, remaining = fill(skeleton, fields)

    # ── Step 2: cleanup blank optional fields ─────────────────────────────────
    clean_skeleton, removed_fields = _cleanup_blanks(filled)

    # ── Step 3: generate .docx via existing generate_docx handler ─────────────
    gen_result_raw = await _generate_handle({
        "filled_skeleton": clean_skeleton,
        "filename_prefix": filename_prefix
    })
    gen_result = json.loads(gen_result_raw[0].text)

    if not gen_result.get("success"):
        return [TextContent(
            type="text",
            text=json.dumps({
                "success":               False,
                "download_url":          None,
                "filename":              None,
                "fields_applied":        fields_applied,
                "placeholders_remaining": remaining,
                "optional_cleaned":      len(removed_fields),
                "error":                 gen_result.get("error", "Unknown error"),
                "message":               f"❌ பத்திரம் உருவாக்க தோல்வி: {gen_result.get('error')}",
                "next_tool":             None
            }, ensure_ascii=False, indent=2)
        )]

    # ── Step 4: get download URL ───────────────────────────────────────────────
    list_result_raw = await _list_handle({})
    list_result     = json.loads(list_result_raw[0].text)

    files        = list_result.get("files", [])
    download_url = files[0]["download_url"] if files else None
    filename     = files[0]["filename"]     if files else gen_result.get("filename")

    return [TextContent(
        type="text",
        text=json.dumps({
            "success":               True,
            "download_url":          download_url,
            "filename":              filename,
            "fields_applied":        fields_applied,
            "placeholders_remaining": remaining,
            "optional_cleaned":      len(removed_fields),
            "error":                 None,
            "message": (
                f"✅ பத்திரம் தயாரானது! "
                f"{fields_applied} fields நிரப்பப்பட்டன. "
                f"{len(removed_fields)} காலி fields நீக்கப்பட்டன. "
                f"📥 {download_url} "
                "⚠️ இந்த பத்திரம் மாதிரி வரைவு மட்டுமே. பதிவுக்கு முன் வழக்கறிஞர் ஆலோசனை பெறவும்."
            ),
            "next_tool": None
        }, ensure_ascii=False, indent=2)
    )]
