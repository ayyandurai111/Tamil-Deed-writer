#!/usr/bin/env python3
"""
main.py
=======
Tamil Sale Deed MCP Server — Render / HTTP deployment entry point.

Exposes the MCP server over HTTP using SSE (Server-Sent Events) transport,
which is the standard for remote MCP deployments.

Endpoints:
  GET  /          → Health check + server info
  GET  /sse       → MCP SSE connection (Claude connects here)
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
from fastapi.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.applications import Starlette
import uvicorn

from mcp.server.sse import SseServerTransport

# Import the MCP server instance from src/server.py
from server import server as mcp_server
from constants import OUTPUT_DIR

# ── SSE Transport ─────────────────────────────────────────────────────────────
sse_transport = SseServerTransport("/messages/")


async def handle_sse(request):
    """MCP SSE connection handler — Claude connects here."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


# ── Starlette app (MCP SSE routes) ───────────────────────────────────────────
mcp_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]
)


# ── FastAPI app (health + file download routes) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Tamil Sale Deed MCP Server",
    description="AI-powered Tamil Sale Deed generator via MCP protocol",
    version="9.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def health():
    """Health check — also shows available MCP tools count."""
    from tools import TOOL_DEFINITIONS
    return {
        "status":  "ok",
        "server":  "tamil-deed-writer",
        "version": "9.0.0",
        "tools":   len(TOOL_DEFINITIONS),
        "mcp_sse": "/sse",
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
                "download_url": f"/download/{f.name}",
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

    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── Mount MCP SSE app under the FastAPI app ───────────────────────────────────
app.mount("/", mcp_app)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
