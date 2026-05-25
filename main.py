#!/usr/bin/env python3
"""
main.py
=======
Tamil Sale Deed MCP Server — Render / HTTP deployment entry point.

Exposes the MCP server over HTTP using SSE (Server-Sent Events) transport,
which is the standard for remote MCP deployments.

Compatible with any MCP-capable AI client:
  • Claude (Anthropic) — Claude Desktop, Claude.ai
  • OpenAI ChatGPT (with MCP plugin support)
  • Google Gemini (with MCP support)
  • Any LLM framework supporting the MCP protocol (LangChain, LlamaIndex, etc.)

Endpoints:
  GET  /          → Health check + server info
  GET  /sse       → MCP SSE connection (AI client connects here)
  POST /messages/ → MCP message posting (used by SSE transport internally)
  GET  /download/{filename} → Download a generated .docx file
  GET  /files     → List all generated .docx files
"""

import sys
import os
from pathlib import Path

# ── Path setup: make src/ importable ─────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
SRC_DIR  = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

# ── Imports ───────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
import uvicorn

from mcp.server.sse import SseServerTransport

# Import the MCP server instance from src/server.py
from server import server as mcp_server
from constants import OUTPUT_DIR, BASE_URL
from file_store import get as _mem_get

# ── SSE Transport ─────────────────────────────────────────────────────────────
sse_transport = SseServerTransport("/messages/")


async def handle_sse(request):
    """MCP SSE connection handler — AI client connects here."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


# (MCP routes registered directly on FastAPI app below)


# ── FastAPI app (health + file download routes) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Tamil Sale Deed MCP Server",
    description=(
        "AI-powered Tamil Sale Deed generator via MCP protocol. "
        "Compatible with Claude, ChatGPT, Gemini, and any MCP-capable AI client."
    ),
    version="8.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def health():
    """Health check — also shows available MCP tools count."""
    from tools import TOOL_DEFINITIONS
    return {
        "status":  "ok",
        "server":  "tamil-deed-writer",
        "version": "8.0.0",
        "tools":   len(TOOL_DEFINITIONS),
        "mcp_sse": "/sse",
        "ai_support": ["claude", "chatgpt", "gemini", "any-mcp-client"],
        "message": "Tamil Sale Deed MCP Server is running 🏡",
    }


@app.get("/files")
async def list_files():
    """List all generated .docx files."""
    from datetime import datetime
    files = sorted(
        OUTPUT_DIR.glob("*.docx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return {
        "files": [
            {
                "filename": f.name,
                "size_kb":  round(f.stat().st_size / 1024, 1),
                "created":  datetime.fromtimestamp(f.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "download_url": f"{BASE_URL.rstrip('/')}/download/{f.name}",
            }
            for f in files
        ],
        "total": len(files),
    }


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated .docx file by name."""
    # Security: only allow .docx files, no path traversal
    if not filename.endswith(".docx") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # 1️⃣ Try disk first
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return FileResponse(path=str(filepath), filename=filename, media_type=MEDIA_TYPE)

    # 2️⃣ Fall back to in-memory store (survives Render /tmp wipe)
    data = _mem_get(filename)
    if data:
        return Response(
            content=data,
            media_type=MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=404, detail=f"File '{filename}' not found")


# ── Mount MCP SSE routes directly (avoid catch-all "/" conflict) ─────────────
app.add_route("/sse", handle_sse)
app.mount("/messages", sse_transport.handle_post_message)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
