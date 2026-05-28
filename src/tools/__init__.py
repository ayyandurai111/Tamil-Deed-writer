"""
tools/__init__.py — v3 single-tool registry
============================================
Exposes ONE tool: run_deed_workflow

All workflow logic lives server-side in workflow/pipeline.py.
The AI calls run_deed_workflow on every turn and reads next_action.

Compatible with: Claude, ChatGPT, Gemini, Mistral, LLaMA, any MCP host.
No LLM API required. No mixed language in prompts.
"""

from tools.run_deed_workflow import TOOL_DEFINITION, handle

TOOL_DEFINITIONS = [TOOL_DEFINITION]

TOOL_HANDLERS = {
    "run_deed_workflow": handle,
}
