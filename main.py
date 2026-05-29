#!/usr/bin/env python3
"""
main.py
=======
Tamil Sale Deed MCP Server — Render / HTTP deployment entry point.

Transports supported:
  /sse   → SSE transport    (Claude Desktop, Claude.ai)
  /mcp   → Streamable HTTP  (GPT / OpenAI Agents SDK — preferred)

Endpoints:
  GET  /          → Health check + server info
  GET  /sse       → MCP SSE connection (Claude)
  POST /messages/ → MCP message posting (SSE transport internally)
  POST /mcp       → MCP Streamable HTTP (GPT / OpenAI Agents SDK)
  GET  /download/{filename} → Download a generated .docx file
  GET  /files     → List all generated .docx files
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
SRC_DIR  = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
import uvicorn

from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport

from server import server as mcp_server
from constants import OUTPUT_DIR, BASE_URL
from file_store import get as _mem_get

# ── SSE Transport (Claude) ────────────────────────────────────────────────────
sse_transport = SseServerTransport("/messages/")

async def handle_sse(request):
    """Claude Desktop / Claude.ai → SSE transport."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )

# ── Streamable HTTP Transport (GPT / OpenAI Agents SDK) ──────────────────────
async def handle_streamable_http(request: Request):
    """GPT / OpenAI Agents SDK → Streamable HTTP transport."""
    transport = StreamableHTTPServerTransport("/mcp")
    async with transport.connect(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )

# ── FastAPI app ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="Tamil Sale Deed MCP Server",
    description=(
        "AI-powered Tamil Sale Deed generator via MCP protocol. "
        "Compatible with Claude (SSE) and GPT / OpenAI Agents SDK (Streamable HTTP)."
    ),
    version="9.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def health():
    from tools import TOOL_DEFINITIONS
    return {
        "status":     "ok",
        "server":     "tamil-deed-writer",
        "version":    "9.0.0",
        "tools":      len(TOOL_DEFINITIONS),
        "transports": {
            "claude": "/sse  (SSE transport)",
            "gpt":    "/mcp  (Streamable HTTP — OpenAI Agents SDK)"
        },
        "ai_support": ["claude", "chatgpt", "gemini", "any-mcp-client"],
        "message":    "Tamil Sale Deed MCP Server is running 🏡",
    }

@app.get("/files")
async def list_files():
    from datetime import datetime
    files = sorted(
        OUTPUT_DIR.glob("*.docx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return {
        "files": [
            {
                "filename":     f.name,
                "size_kb":      round(f.stat().st_size / 1024, 1),
                "created":      datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": f"{BASE_URL.rstrip('/')}/download/{f.name}",
            }
            for f in files
        ],
        "total": len(files),
    }

@app.get("/download/{filename}")
async def download_file(filename: str):
    if not filename.endswith(".docx") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return FileResponse(path=str(filepath), filename=filename, media_type=MEDIA_TYPE)

    data = _mem_get(filename)
    if data:
        return Response(
            content=data,
            media_type=MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

# ── Mount both transports ─────────────────────────────────────────────────────
app.add_route("/sse", handle_sse)                            # Claude
app.mount("/messages", sse_transport.handle_post_message)   # Claude SSE internal
app.add_route("/mcp", handle_streamable_http, methods=["POST", "GET", "DELETE"])  # GPT

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
