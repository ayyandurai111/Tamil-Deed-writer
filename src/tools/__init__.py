"""
tools/__init__.py
=================
Central registry — imports every tool module and exposes:

  TOOL_DEFINITIONS  : list[Tool]   — passed to @server.list_tools()
  TOOL_HANDLERS     : dict         — maps tool name → async handle() function

Workflow (8 steps):
  1. detect_deed_type  — agriculture or plot
  2. load_skeleton     — JSON template
  3. extract_fields    — parse + merge fields
  3b. resolve_date     — date → Tamil names
  4. validate_fields   — legal check + PAN/TDS
  5. fill_skeleton     — replace {{PLACEHOLDERS}} + cleanup blanks
  6. review_draft      — L1–L4 skeleton review
  7. generate_docx     — render .docx (Latha font)
  8. list_output_files — download links (optional)

NOTE: generate_draft removed. Skeleton is the single source of truth.
      fill_skeleton Phase 2 handles optional field cleanup.
      review_draft reads clean_skeleton directly (no draft prose needed).
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
    review_draft.TOOL_DEFINITION,        # 6
    generate_docx.TOOL_DEFINITION,       # 7
    list_output_files.TOOL_DEFINITION,   # 8
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
