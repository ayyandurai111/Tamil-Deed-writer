# GPT / OpenAI Agents SDK — Connection Guide

## Endpoint

| AI Client | Transport | URL |
|-----------|-----------|-----|
| Claude Desktop / Claude.ai | SSE | `https://your-server.onrender.com/sse` |
| GPT / OpenAI Agents SDK | Streamable HTTP | `https://your-server.onrender.com/mcp` |

## OpenAI Agents SDK — Python Example

```python
from openai import OpenAI
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

client = OpenAI()

mcp_server = MCPServerStreamableHttp(
    url="https://your-server.onrender.com/mcp"
)

agent = Agent(
    name="Tamil Deed Writer",
    model="gpt-4o",
    instructions=open("AI_SYSTEM_PROMPT.txt").read(),
    mcp_servers=[mcp_server],
)

result = Runner.run_sync(
    agent,
    "விவசாய நிலம் பத்திரம் தயார் செய்யவும்..."
)
print(result.final_output)
```

## ChatGPT Custom GPT — Actions Setup

1. Go to ChatGPT → My GPTs → Create
2. Instructions: paste AI_SYSTEM_PROMPT.txt content
3. Actions → Add Action:
   - Schema URL: `https://your-server.onrender.com/openapi.json`
   - Auth: None (or add API key if needed)

## Key Notes

- **tool_choice: "required"** — always set this in API calls so GPT doesn't skip tools
- **MCP version 1.9.0+** required for Streamable HTTP transport
