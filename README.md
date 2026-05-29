# Tamil Sale Deed MCP Server 🏡

AI-powered Tamil Sale Deed generator using the **MCP (Model Context Protocol)**.
The AI client controls the workflow — **no AI API key inside this server itself**.

## 🤖 AI Compatibility

This MCP server works with **any MCP-capable AI client**:

| AI Client | Connect Method |
|-----------|---------------|
| **Claude** (Anthropic) | Claude Desktop (`claude_desktop_config.json`) or Claude.ai |
| **ChatGPT** (OpenAI) | MCP plugin / tool integration |
| **Gemini** (Google) | MCP support |
| **LangChain / LlamaIndex** | MCP framework client |
| **Any other LLM** | Any MCP-protocol-compatible client |

> **Key principle**: The server exposes tools. The AI decides which tools to call and in what order.
> This design is **model-agnostic** — swap the AI client without changing the server.

## Project Structure

```
Tamil-Deed-writer-v4/
├── templates/
│   ├── agriculture_skeleton.json   ← Agriculture template
│   └── plot_skeleton.json          ← Plot/மனை template
├── src/
│   ├── server.py                   ← MCP Server core
│   ├── constants.py                ← Shared constants
│   ├── file_store.py               ← In-memory file store
│   └── tools/
│       ├── detect_deed_type.py
│       ├── load_skeleton.py
│       ├── extract_fields.py
│       ├── resolve_date.py
│       ├── validate_fields.py
│       ├── fill_skeleton.py
│       ├── generate_docx.py
│       └── list_output_files.py
├── prompts/                        ← Per-step AI prompt fragments
├── output/                         ← Generated DOCX files saved here
├── tests/
│   └── test_tools.py               ← Smoke tests
├── AI_SYSTEM_PROMPT.txt            ← System prompt (works with any AI)
├── CLAUDE_SYSTEM_PROMPT.txt        ← Legacy alias (same content)
├── claude_desktop_config.json      ← Quick-start config for Claude Desktop
├── main.py                         ← HTTP/SSE server (Render deployment)
├── run_stdio.py                    ← Local stdio mode
└── render.yaml                     ← Render.com deployment config
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run tests
```bash
python3 tests/test_tools.py
```

### 3. Start the server

**Local (stdio — for Claude Desktop or local AI clients):**
```bash
python3 run_stdio.py
```

**HTTP/SSE (for remote AI clients — Render, cloud):**
```bash
python3 main.py
# Server starts at http://localhost:8000
# SSE endpoint: http://localhost:8000/sse
```

---

## Connecting Your AI Client

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "tamil-deed-writer": {
      "command": "python3",
      "args": ["/FULL/PATH/TO/Tamil-Deed-writer-v4/run_stdio.py"]
    }
  }
}
```

Then paste the contents of `AI_SYSTEM_PROMPT.txt` as your Claude system prompt.

### Claude.ai (Remote MCP)

In Claude.ai settings → Integrations → Add MCP Server:
```
URL: https://your-server.onrender.com/sse
```

### ChatGPT / OpenAI (MCP Plugin)

Point your MCP client configuration to:
```
SSE endpoint: https://your-server.onrender.com/sse
```

### LangChain / LlamaIndex

```python
from langchain_mcp import MCPClient

client = MCPClient(url="https://your-server.onrender.com/sse")
tools = client.get_tools()
# Use tools in your agent
```

### Generic MCP Client

```
SSE URL:  https://your-server.onrender.com/sse
POST URL: https://your-server.onrender.com/messages/
```

---

## MCP Tools (9 tools, 8 calls)

| # | Tool | Purpose |
|---|------|---------|
| 1 | `detect_deed_type` | Agriculture or Plot கண்டுபிடி |
| 2 | `load_skeleton` | சரியான JSON template எடு |
| 3 | `extract_fields` | Prompt-இல் இருந்து fields parse செய் |
| 3b | `resolve_date` | தேதியை Tamil format-ல் resolve செய் |
| 4 | `validate_fields` | சட்டரீதியான fields சரிபார்; missing list கொடு |
| 5 | `fill_skeleton` | Data-ஐ placeholders-இல் போடு + cleanup |
| 6 | `generate_docx` | DOCX file உருவாக்கு (Latha font) |
| 7 | `list_output_files` | Generated files list + download links |

## Workflow

```
User Prompt
    ↓
[CALL 1]  detect_deed_type   ← AI determines deed type
    ↓
[CALL 2]  load_skeleton      ← Load JSON template
    ↓
[CALL 3]  extract_fields     ← AI extracts fields from prompt
    ↓
[CALL 4]  resolve_date       ← Resolve deed date (default: today)
    ↓
[CALL 5]  validate_fields    ← Legal check + PAN/TDS rules
    ↓
Missing fields?
  ├── YES → AI asks user in Tamil ✋
  │          User replies → extract_fields → validate_fields  ← LOOP
  └── NO  →
    ↓
[CALL 6]  fill_skeleton      ← Replace {{PLACEHOLDERS}} + cleanup
    ↓
[CALL 7]  generate_docx      ← Render .docx (Latha font)
    ↓
[CALL 8]  list_output_files  ← Return download URL ✅
```

## Health Check / API

```bash
curl https://your-server.onrender.com/
# → { "status": "ok", "version": "9.0.0", "ai_support": [...], "tools": 8 }

curl https://your-server.onrender.com/files
# → list of generated .docx files with download URLs
```

## Example Prompt (in any AI client)

```
தஞ்சாவூர் மாவட்டம் பட்டுக்கோட்டை தாலுக்காவில்,
வேளாங்கண்ணி கிராமம் survey no 45/2, 2.50 ஏக்கர் நஞ்சை நிலம்.
விற்பவர்: திரு. ராமசாமி (55 வயது), தந்தை பெரியசாமி,
  12 தெற்கு தெரு பட்டுக்கோட்டை, ஆதார் 1234-5678-9012.
வாங்குபவர்: திரு. முருகன் (40 வயது), தந்தை கண்ணன்,
  34 வடக்கு தெரு கும்பகோணம், ஆதார் 9876-5432-1098.
மொத்த விலை: ரூ. 25,00,000 (NEFT மூலம்).
பட்டா எண் 1234, முன்னோர் ஆவணம் 987/2010.
சாட்சி 1: வேலுசாமி, 5 ஆத்தூர் தெரு.
சாட்சி 2: அன்பழகன், 22 கோவில் தெரு.
விற்பனை பத்திரம் உருவாக்கு.
```

## Output

Generated DOCX files are saved to the `output/` folder with Tamil font (Latha),
legal formatting, and all clauses from the templates. A download URL is returned
automatically at the end of each successful workflow.

---

> ⚠️ **Disclaimer**: Generated deeds are draft samples only.
> Consult a licensed attorney before registration.
