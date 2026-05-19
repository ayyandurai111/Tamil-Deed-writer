# Tamil Sale Deed MCP Server 🏡

AI-powered Tamil Sale Deed generator using MCP protocol.
Claude/ChatGPT controls everything — **no AI API inside this server**.

## Project Structure

```
tamil-deed-mcp/
├── templates/
│   ├── agriculture_skeleton.json   ← Agriculture template
│   └── plot_skeleton.json          ← Plot/மனை template
├── src/
│   └── server.py                   ← MCP Server (5 tools)
├── output/                         ← Generated DOCX files saved here
├── tests/
│   └── test_tools.py               ← Smoke test
├── CLAUDE_SYSTEM_PROMPT.txt        ← Paste this into Claude Desktop
└── claude_desktop_config.json     ← MCP config for Claude Desktop
```

## Setup

### 1. Install dependencies
```bash
pip install python-docx "mcp[cli]"
```

### 2. Run tests
```bash
cd tamil-deed-mcp
python3 tests/test_tools.py
```

### 3. Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "tamil-deed-writer": {
      "command": "python3",
      "args": ["/FULL/PATH/TO/tamil-deed-mcp/src/server.py"]
    }
  }
}
```

Restart Claude Desktop.

## MCP Tools

| Tool | Purpose |
|------|---------|
| `detect_deed_type` | Agriculture or Plot கண்டுபிடி |
| `load_skeleton` | சரியான template எடு |
| `extract_fields` | Prompt-இல் இருந்து fields parse செய் **(NEW)** |
| `validate_fields` | சட்டரீதியான fields சரிபார்; missing list கொடு |
| `fill_skeleton` | Data-ஐ placeholders-இல் போடு |
| `generate_docx` | DOCX file உருவாக்கு |
| `list_output_files` | Generated files list |

## Workflow

```
User Prompt
    ↓
detect_deed_type
    ↓
load_skeleton
    ↓
extract_fields          ← Parses all fields from prompt automatically
    ↓
validate_fields         ← Checks legal requirements
    ↓
Missing fields?
  ├── YES → Claude asks user in Tamil ✋
  │          User replies
  │          extract_fields (new reply + existing_fields merged)
  │          validate_fields again  ← loop until complete
  │
  └── NO → fill_skeleton → generate_docx → Output ✅
```

## Example Prompt to Claude

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
legal formatting, and all clauses from your original templates.
