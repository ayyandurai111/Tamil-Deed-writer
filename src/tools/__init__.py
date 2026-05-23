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
    detect_deed_type.TOOL_DEFINITION,
    load_skeleton.TOOL_DEFINITION,
    extract_fields.TOOL_DEFINITION,
    resolve_date.TOOL_DEFINITION,
    validate_fields.TOOL_DEFINITION,
    fill_skeleton.TOOL_DEFINITION,
    review_draft.TOOL_DEFINITION,
    generate_docx.TOOL_DEFINITION,
    list_output_files.TOOL_DEFINITION,
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
