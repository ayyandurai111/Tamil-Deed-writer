# Tamil Sale Deed MCP Server 🏡

AI-powered Tamil Sale Deed generator using MCP protocol.
Any MCP-compatible AI (Claude, ChatGPT, Gemini, etc.) controls everything — **no AI API inside this server**.

## Project Structure

```
tamil-deed-mcp/
├── templates/
│   ├── agriculture_skeleton.json   ← Agriculture template
│   └── plot_skeleton.json          ← Plot/மனை template
├── src/
│   └── server.py                   ← MCP Server
├── output/                         ← Generated DOCX files saved here
├── tests/
│   └── test_tools.py               ← Smoke test
├── SYSTEM_PROMPT.txt               ← Paste this into any AI chatbot
└── claude_desktop_config.json      ← MCP config for Claude Desktop (stdio mode)
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

### 3. Connect your AI chatbot

#### Claude Desktop (Local / stdio)
Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "tamil-deed-writer": {
      "command": "python3",
      "args": ["/FULL/PATH/TO/tamil-deed-mcp/run_stdio.py"]
    }
  }
}
```
Restart Claude Desktop.

#### Claude / ChatGPT / Gemini / Any bot (Remote / SSE)
1. Deploy to Render (see render.yaml)
2. Your MCP URL: `https://tamil-deed-writer.onrender.com/sse`
3. Add this URL in your chatbot's MCP settings
4. Paste `SYSTEM_PROMPT.txt` content as the system/custom instructions

## MCP Tools

| Tool | Purpose |
|------|---------|
| `identify_document_type` | Agriculture or Plot கண்டுபிடி |
| `prepare_document_template` | சரியான template எடு |
| `read_document_details` | Prompt-இல் இருந்து fields parse செய் |
| `confirm_document_date` | தேதி → Tamil format |
| `check_document_completeness` | சட்டரீதியான fields சரிபார்; missing list கொடு |
| `draft_document` | Data-ஐ placeholders-இல் போடு |
| `verify_document_quality` | L1–L4 skeleton review |
| `create_final_document` | DOCX file உருவாக்கு |
| `get_document_download` | Generated files + download links |

## Workflow

```
User types deed data
    ↓
detect_deed_type → load_skeleton → extract_fields → resolve_date
    ↓
validate_fields
  ├── Missing fields? → AI asks user in Tamil → loop
  └── Complete? → fill_skeleton → review_draft (L1–L4)
                      ↓
                 generate_docx → list_output_files → Download ✅
```

## Example Prompt

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
legal formatting, and all clauses from the original templates.
