#!/usr/bin/env python3
"""
server.py
=========
Tamil Sale Deed MCP Server — core MCP server instance.

Compatible with any MCP-capable AI client (Claude, ChatGPT, Gemini, etc.).

Imported by:
  - main.py      → HTTP/SSE deployment (Render, cloud)
  - run_stdio.py → Local stdio mode (Claude Desktop or other local AI clients)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

import tools as tool_registry

# ── MCP Server instance — exported for main.py and run_stdio.py ───────────────
server = Server("tamil-deed-writer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return tool_registry.TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = tool_registry.TOOL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(
            type="text",
            text='{"error": "Unknown tool: ' + name + '"}'
        )]
    return await handler(arguments)
