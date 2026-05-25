#!/usr/bin/env python3
"""
run_stdio.py
============
Local stdio entry point — for Claude Desktop or any local MCP-capable AI client.

Use this for any local AI client that supports MCP stdio transport.
For Render / cloud deployment, use main.py instead.

Usage:
  python3 run_stdio.py

Claude Desktop config (claude_desktop_config.json) — also works as a template
for any local MCP client config:
  {
    "mcpServers": {
      "tamil-deed-writer": {
        "command": "python3",
        "args": ["/FULL/PATH/TO/tamil-deed-mcp/run_stdio.py"]
      }
    }
  }
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.server.stdio import stdio_server
from server import server


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
