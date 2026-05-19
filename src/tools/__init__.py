"""
tools/__init__.py
=================
Central registry — imports every tool module and exposes:

  TOOL_DEFINITIONS  : list[Tool]   — passed to @server.list_tools()
  TOOL_HANDLERS     : dict         — maps tool name → async handle() function

Adding a new tool:
  1. Create src/tools/my_new_tool.py with TOOL_DEFINITION and handle()
  2. Import it here and add to both lists below — nothing else to change.
"""

from tools import (
    detect_deed_type,
    load_skeleton,
    extract_fields,
    resolve_date,
    validate_fields,
    fill_skeleton,
    generate_draft,
    review_draft,
    generate_docx,
    list_output_files,
)

# ── All tool definitions returned to Claude / ChatGPT ─────────────────────────
TOOL_DEFINITIONS = [
    detect_deed_type.TOOL_DEFINITION,   # 1
    load_skeleton.TOOL_DEFINITION,      # 2
    extract_fields.TOOL_DEFINITION,     # 3
    resolve_date.TOOL_DEFINITION,       # 3b
    validate_fields.TOOL_DEFINITION,    # 4
    fill_skeleton.TOOL_DEFINITION,      # 5
    generate_draft.TOOL_DEFINITION,     # 6
    review_draft.TOOL_DEFINITION,       # 7
    generate_docx.TOOL_DEFINITION,      # 8
    list_output_files.TOOL_DEFINITION,  # 9
]

# ── name → handler mapping used by call_tool dispatcher ───────────────────────
TOOL_HANDLERS = {
    "detect_deed_type":  detect_deed_type.handle,
    "load_skeleton":     load_skeleton.handle,
    "extract_fields":    extract_fields.handle,
    "resolve_date":      resolve_date.handle,
    "validate_fields":   validate_fields.handle,
    "fill_skeleton":     fill_skeleton.handle,
    "generate_draft":    generate_draft.handle,
    "review_draft":      review_draft.handle,
    "generate_docx":     generate_docx.handle,
    "list_output_files": list_output_files.handle,
}
