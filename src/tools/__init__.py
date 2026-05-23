"""
tools/__init__.py
=================
Central registry — imports every tool module and exposes:

  TOOL_DEFINITIONS  : list[Tool]   — passed to @server.list_tools()
  TOOL_HANDLERS     : dict         — maps tool name → async handle() function

Workflow (9 steps):
  1. identify_document_type      — agriculture or plot
  2. prepare_document_template   — JSON template
  3. read_document_details       — parse + merge fields
  4. confirm_document_date       — date → Tamil names
  5. check_document_completeness — legal check + PAN/TDS
  6. draft_document              — replace {{PLACEHOLDERS}} + cleanup blanks
  7. verify_document_quality     — L1–L4 skeleton review
  8. create_final_document       — render .docx (Latha font)
  9. get_document_download       — download links

NOTE: Template is the single source of truth.
      draft_document Phase 2 handles optional field cleanup.
      verify_document_quality reads clean template directly.
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
    resolve_date.TOOL_DEFINITION,        # 4
    validate_fields.TOOL_DEFINITION,     # 5
    fill_skeleton.TOOL_DEFINITION,       # 6
    review_draft.TOOL_DEFINITION,        # 7
    generate_docx.TOOL_DEFINITION,       # 8
    list_output_files.TOOL_DEFINITION,   # 9
]

TOOL_HANDLERS = {
    "identify_document_type":      detect_deed_type.handle,
    "prepare_document_template":   load_skeleton.handle,
    "read_document_details":       extract_fields.handle,
    "confirm_document_date":       resolve_date.handle,
    "check_document_completeness": validate_fields.handle,
    "draft_document":              fill_skeleton.handle,
    "verify_document_quality":     review_draft.handle,
    "create_final_document":       generate_docx.handle,
    "get_document_download":       list_output_files.handle,
}
