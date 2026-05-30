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
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult

import tools as tool_registry

# ── MCP Server instance — exported for main.py and run_stdio.py ───────────────
server = Server("tamil-deed-writer")

# Build a lookup: tool_name → outputSchema (if any)
_OUTPUT_SCHEMAS: dict[str, dict] = {
    t.name: t.outputSchema
    for t in tool_registry.TOOL_DEFINITIONS
    if getattr(t, "outputSchema", None)
}


SERVER_INSTRUCTIONS = """
Tamil Sale Deed Writer — 3-Tool Workflow

STRICT CALL ORDER: extract → analyse → build
- Never call analyse before extract returns ready_for_analyse=true
- Never call build before analyse returns can_proceed=true and pan_block=false
- Never call two tools in one response

LOOP RULES:
- If extract returns field_errors or missing_fields → ask user in Tamil → call extract again
- If analyse returns pan_block=true → ask user for PAN in Tamil → call extract + analyse again
- Always pass existing_fields (full accumulated dict) when looping extract

LANGUAGE: All replies to user must be in Tamil only.
"""

@server.list_tools()
async def list_tools() -> list[Tool]:
    return tool_registry.TOOL_DEFINITIONS

@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None):
    from mcp.types import GetPromptResult, PromptMessage, TextContent as TC
    return GetPromptResult(
        description="Tamil Deed Writer workflow instructions",
        messages=[PromptMessage(role="user", content=TC(type="text", text=SERVER_INSTRUCTIONS))]
    )


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    handler = tool_registry.TOOL_HANDLERS.get(name)
    if handler is None:
        return CallToolResult(
            content=[TextContent(type="text", text='{"error": "Unknown tool: ' + name + '"}')],
            isError=True,
        )

    content = await handler(arguments)

    # ── Structured-output support ──────────────────────────────────────────────
    # When a tool declares outputSchema, MCP hosts such as ChatGPT require
    # structuredContent to be populated — returning only TextContent causes
    # "Output validation error: outputSchema defined but no structured output returned".
    #
    # Strategy: if the first content block is a TextContent that contains valid
    # JSON, promote it to structuredContent automatically.  This keeps every
    # individual tool handler simple (they still return TextContent) while
    # satisfying the structured-output contract at the server level.
    structured: dict | None = None
    if name in _OUTPUT_SCHEMAS and content:
        first = content[0]
        if isinstance(first, TextContent):
            try:
                structured = json.loads(first.text)
            except (json.JSONDecodeError, AttributeError):
                structured = None

    return CallToolResult(
        content=content,
        structuredContent=structured,
    )
