"""
tools/__init__.py
=================
Central registry — imports every tool module and exposes:

  TOOL_DEFINITIONS  : list[Tool]   — passed to @server.list_tools()
  TOOL_HANDLERS     : dict         — maps tool name → async handle() function

Compatible with any MCP-capable AI (Claude, ChatGPT, Gemini, LangChain, etc.).
The AI orchestrates the workflow by calling tools in sequence.

WORKFLOW — 9 tools, 12 calls total:
  CALL 1  [TOOL] detect_deed_type   — determine agriculture or plot
  CALL 2  [TOOL] load_skeleton      — load JSON template
  CALL 3  [TOOL] extract_fields     — AI extracts fields from user text, tool merges
  CALL 4  [TOOL] resolve_date       — parse date → Tamil day/month/year
  CALL 5  [TOOL] validate_fields    — legal checks + PAN/TDS rules
  CALL 6  [TOOL] fill_skeleton      — replace {{PLACEHOLDERS}} → clean_skeleton
  CALL 7  [TOOL] review_draft       — L1+L2 programmatic checks on clean_skeleton
  CALL 8  [AI ANALYSIS — NO TOOL]   — AI performs L3 consistency check
  CALL 9  [AI ANALYSIS — NO TOOL]   — AI performs L4 grammar check
  CALL 10 [AI DECISION — NO TOOL]   — AI combines CALL 7+8+9 → final go/no-go
  CALL 11 [TOOL] generate_docx      — render .docx (Latha font)
  CALL 12 [TOOL] list_output_files  — return download URL

IMPORTANT: CALL 8, 9, 10 are NOT tool calls. They are AI text responses.
No tools exist for these steps. The AI performs them as analysis between CALL 7 and CALL 11.
"""

from tools import (
    detect_deed_type,
    load_skeleton,
    extract_fields,
    resolve_date,
    validate_fields,
    fill_skeleton,
    review_draft,
    generate_docx,
    list_output_files,
)

TOOL_DEFINITIONS = [
    detect_deed_type.TOOL_DEFINITION,    # 1
    load_skeleton.TOOL_DEFINITION,       # 2
    extract_fields.TOOL_DEFINITION,      # 3
    resolve_date.TOOL_DEFINITION,        # 3b
    validate_fields.TOOL_DEFINITION,     # 4
    fill_skeleton.TOOL_DEFINITION,       # 5
    review_draft.TOOL_DEFINITION,        # 6 (CALL 7 — L1+L2 programmatic)
    generate_docx.TOOL_DEFINITION,       # 7 (CALL 11)
    list_output_files.TOOL_DEFINITION,   # 8 (CALL 12)
]

TOOL_HANDLERS = {
    "detect_deed_type":  detect_deed_type.handle,
    "load_skeleton":     load_skeleton.handle,
    "extract_fields":    extract_fields.handle,
    "resolve_date":      resolve_date.handle,
    "validate_fields":   validate_fields.handle,
    "fill_skeleton":     fill_skeleton.handle,
    "review_draft":      review_draft.handle,
    "generate_docx":     generate_docx.handle,
    "list_output_files": list_output_files.handle,
}
