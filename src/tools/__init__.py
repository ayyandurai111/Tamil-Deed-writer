"""
tools/__init__.py — 3-Tool Workflow
=====================================
TOOL 1  extract   — AI extracts fields, Logic validates + normalizes
TOOL 2  analyse   — 100% Logic: skeleton load + legal validation
TOOL 3  build     — 100% Logic: fill + generate .docx + download URL
"""

from tools import tool1_extract, tool2_analyse, tool3_build

TOOL_DEFINITIONS = [
    tool1_extract.TOOL_DEFINITION,
    tool2_analyse.TOOL_DEFINITION,
    tool3_build.TOOL_DEFINITION,
]

TOOL_HANDLERS = {
    "extract": tool1_extract.handle,
    "analyse": tool2_analyse.handle,
    "build":   tool3_build.handle,
}
