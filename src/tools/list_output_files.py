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
        "[CALL 12 of 12 — workflow final step] ONE TASK: இந்த tool call மட்டும். "
        "generate_docx success=True பெற்ற பிறகு உடனே call செய். Return: filename, size_kb, created, download_url. "
        "output/ folder-இல் உள்ள எல்லா .docx files-ஐயும் காட்டும். "
        "Return: filename, size_kb, created, download_url (full https link). "
        "பயனருக்கு: 📁 உருவாக்கப்பட்ட பத்திரங்கள் ([count]): 1.[name] — [size]KB — [date] — [download_url]"
    ),
    inputSchema={
        "type": "object",
        "properties": {}
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
        download_url = f"{BASE_URL.rstrip('/')}/download/{f.name}"
        file_list.append(download_url)

    return [TextContent(
        type="text",
        text=json.dumps(file_list, ensure_ascii=False, indent=2)
    )]
