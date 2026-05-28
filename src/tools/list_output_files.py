"""
tools/list_output_files.py
==========================
Tool 8 — list_output_files

Lists all generated .docx files in the output folder with metadata
and full download links.

Annotation:
  readOnlyHint   = True   (reads directory only — no writes)
  idempotentHint = True   (same folder state → same result)
"""

import json
from datetime import datetime
from mcp.types import Tool, TextContent
from constants import OUTPUT_DIR, BASE_URL

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="list_output_files",
    description=(
        "[CALL 12 of 12 — workflow final step] ONE TASK: call this tool only. "
        "Call only after generate_docx returns success=True. "

        "After tool returns — show the user exactly this format, nothing more: "
        "'✅ பத்திரம் தயாரானது! 📥 [download_url] "
        "⚠️ இந்த பத்திரம் மாதிரி வரைவு மட்டுமே. பதிவுக்கு முன் வழக்கறிஞர் / சார்பதிவாளர் ஆலோசனை பெறவும்.' "

        "❌ Do NOT show the filename. "
        "❌ Do NOT ask any follow-up questions. "
        "Workflow is complete."
    ),
    inputSchema={
        "type": "object",
        "properties": {}
    },
    outputSchema={
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "description": "List of generated .docx files, newest first.",
                "items": {
                    "type": "object",
                    "properties": {
                        "filename":     {"type": "string", "description": "Filename on disk."},
                        "size_kb":      {"type": "number",  "description": "File size in kilobytes."},
                        "created":      {"type": "string",  "description": "Creation timestamp (YYYY-MM-DD HH:MM:SS)."},
                        "download_url": {"type": "string",  "description": "Full URL to download this file."}
                    },
                    "required": ["filename", "size_kb", "created", "download_url"]
                }
            },
            "total_files": {
                "type": "integer",
                "description": "Total number of generated files."
            },
            "output_dir": {
                "type": "string",
                "description": "Absolute path to the output directory on the server."
            },
            "message": {
                "type": "string",
                "description": "Tamil message with file count."
            },
            "next_tool": {
                "type": "null",
                "const": None,
                "description": "Workflow is complete. No further tool call needed."
            }
        },
        "required": ["files", "total_files", "output_dir", "message", "next_tool"]
    },
    annotations={
        "title":          "Output File Lister",
        "readOnlyHint":   True,
        "idempotentHint": True,
    }
)


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    files = sorted(OUTPUT_DIR.glob("*.docx"), key=lambda f: f.stat().st_mtime, reverse=True)

    file_list = []
    for f in files:
        stat = f.stat()
        download_url = f"{BASE_URL.rstrip('/')}/download/{f.name}"
        file_list.append({
            "filename":     f.name,
            "size_kb":      round(stat.st_size / 1024, 1),
            "created":      datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": download_url,
        })

    return [TextContent(
        type="text",
        text=json.dumps({
            "files":       file_list,
            "total_files": len(file_list),
            "output_dir":  str(OUTPUT_DIR),
            "message":     f"📁 {len(file_list)} பத்திரங்கள் கண்டுபிடிக்கப்பட்டன.",
            "next_tool":   None
        }, ensure_ascii=False, indent=2)
    )]
