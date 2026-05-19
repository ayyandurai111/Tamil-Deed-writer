"""
tools/list_output_files.py
==========================
Tool 7 — list_output_files

Lists all generated .docx files in the output folder with metadata.

Annotation:
  readOnlyHint   = True   (reads directory only — no writes)
  idempotentHint = True   (same folder state → same result)
"""

import json
from datetime import datetime
from mcp.types import Tool, TextContent
from constants import OUTPUT_DIR

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="list_output_files",
    description=(
        "[Optional — user request மட்டும்] "
        "பயனர் 'என்ன files?', 'கோப்புகளை காட்டு', 'list files' என்று கேட்டால் மட்டும் call செய். "
        "output/ folder-இல் உள்ள எல்லா .docx files-ஐயும் காட்டும். "
        "Return: filename, path, size_kb, created. "
        "பயனருக்கு: 📁 உருவாக்கப்பட்ட பத்திரங்கள் ([count]): 1.[name] — [size]KB — [date]"
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
        file_list.append({
            "filename": f.name,
            "path":     str(f),
            "size_kb":  round(stat.st_size / 1024, 1),
            "created":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })

    return [TextContent(
        type="text",
        text=json.dumps({
            "files":       file_list,
            "total_files": len(file_list),
            "output_dir":  str(OUTPUT_DIR),
            "message":     f"📁 {len(file_list)} பத்திரங்கள் கண்டுபிடிக்கப்பட்டன."
        }, ensure_ascii=False, indent=2)
    )]
