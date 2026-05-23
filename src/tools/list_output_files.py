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
    name="get_document_download",
    description=(
        "[CALL 12 of 12 — workflow final step] ONE TASK: இந்த tool call மட்டும். "
        "generate_docx success=True பெற்ற பிறகு உடனே call செய். "
        "Return-ல் download_url மட்டும் பயனருக்கு காட்டு. "
        "❌ file name காட்டாதே. ❌ link வேண்டுமா என கேட்காதே. ❌ வேறு எந்த கேள்வியும் கேட்காதே. "
        "✅ Auto response format: '✅ பத்திரம் தயாரானது! 📥 [download_url] ⚠️ மாதிரி வரைவு மட்டுமே. பதிவுக்கு முன் வழக்கறிஞர் ஆலோசனை பெறவும்.'"
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
        }, ensure_ascii=False, indent=2)
    )]
