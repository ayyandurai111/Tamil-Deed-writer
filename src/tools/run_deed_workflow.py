"""
tools/run_deed_workflow.py
==========================
Single MCP tool that replaces the previous 9-tool architecture.

Tool description and system prompt follow global prompt engineering principles:
  - English only (no mixed language)
  - Deterministic: model reads next_action, never decides workflow logic
  - Stateless model: model carries only session_id, server carries everything
  - No LLM API calls: all processing is pure Python server-side
  - Compatible with Claude, ChatGPT, Gemini, Mistral, LLaMA, and any MCP host
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.types import TextContent, Tool

import workflow


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL DEFINITION — contract between server and any MCP-compatible model
# ══════════════════════════════════════════════════════════════════════════════

TOOL_DEFINITION = Tool(
    name="run_deed_workflow",

    description=(
        "Stateful Tamil sale deed generator. "
        "Call this tool on every user turn without exception. "
        "The server handles all processing — do not pre-process, translate, or modify user_message. "
        "Read next_action from the response and follow the action rules below. "

        "ACTION RULES: "
        "next_action=ask_user  → show ask_message to the user exactly as returned. "
        "                         Wait for the user reply. Call this tool again with step=reply. "
        "next_action=complete  → show ask_message to the user. Show download_url. "
        "                         Stop. Do not call this tool again. "
        "next_action=error     → show ask_message to the user. Call this tool again with step=reply. "

        "SESSION RULE: "
        "Generate one session_id (UUID v4) at the start of each conversation. "
        "Pass the same session_id on every subsequent call. Never change it mid-conversation. "

        "STEP VALUES: "
        "step=start → first call of a new conversation or when user sends their initial deed request. "
        "step=reply → every subsequent call after the first. "

        "FIELDS RULE: "
        "If the user sends structured deed data (a dict or JSON), pass it in fields_update. "
        "Otherwise leave fields_update empty. Never build or transform the dict yourself. "
    ),

    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "UUID v4 string. Generate once per conversation and reuse on every call. "
                    "Example: '3f2504e0-4f89-11d3-9a0c-0305e82c3301'"
                ),
            },
            "step": {
                "type": "string",
                "enum": ["start", "reply"],
                "description": (
                    "start — first call of the conversation. "
                    "reply — every subsequent call."
                ),
            },
            "user_message": {
                "type": "string",
                "description": (
                    "The user's raw message text. Pass as-is. Do not translate, "
                    "summarize, or extract from it before passing."
                ),
            },
            "fields_update": {
                "type": "object",
                "description": (
                    "Optional. Structured deed field dict if the user sent one. "
                    "Keys must be UPPERCASE (e.g. VENDOR_NAME, TOTAL_AMOUNT). "
                    "Omit this parameter if the user sent only natural language text."
                ),
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["session_id", "step", "user_message"],
    },

    outputSchema={
        "type": "object",
        "properties": {
            "next_action": {
                "type": "string",
                "enum": ["ask_user", "complete", "error"],
                "description": (
                    "ask_user — show ask_message, wait for user, call tool again with step=reply. "
                    "complete — show ask_message and download_url. Stop. Do not call again. "
                    "error    — show ask_message, call tool again with step=reply."
                ),
            },
            "ask_message": {
                "type": "string",
                "description": "Show this text to the user exactly as returned. Do not modify.",
            },
            "download_url": {
                "type": ["string", "null"],
                "description": "Present when next_action=complete. The .docx file download link.",
            },
            "debug_step": {
                "type": "string",
                "description": "Internal pipeline step name. For debugging only — do not show to user.",
            },
        },
        "required": ["next_action", "ask_message"],
    },

    annotations={
        "title":           "Tamil Sale Deed Workflow",
        "readOnlyHint":    False,
        "destructiveHint": False,
        "idempotentHint":  False,
    },
)


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle(arguments: dict) -> list[TextContent]:
    session_id    = (arguments.get("session_id") or "").strip()
    step          = (arguments.get("step") or "start").strip()
    user_message  = (arguments.get("user_message") or "").strip()
    fields_update = arguments.get("fields_update") or None

    # Validate session_id
    if not session_id:
        return _respond({
            "next_action":  "error",
            "ask_message":  "session_id is required. Please generate a UUID v4 and pass it on every call.",
            "download_url": None,
            "debug_step":   "error:no_session_id",
        })

    # Load session from server-side store
    session = workflow.load(session_id)
    session["_session_id"] = session_id

    # Override step to "start" if session is brand new regardless of what model sent
    if session.get("step") == "detect" and step != "start":
        step = "start"

    try:
        response, updated_session = workflow.run(
            session=session,
            user_message=user_message,
            step=step,
            fields_update=fields_update,
        )
    except Exception as exc:
        response = {
            "next_action":  "error",
            "ask_message":  f"An internal error occurred. Please try again. ({type(exc).__name__}: {exc})",
            "download_url": None,
            "debug_step":   f"exception:{type(exc).__name__}",
        }
        updated_session = session

    # Persist updated session (mark done before clearing so re-calls are caught)
    if updated_session.get("step") == "done":
        # Keep a tombstone so re-calls on the same session_id get a proper error
        workflow.save(session_id, {"step": "done", "_session_id": session_id})
    else:
        workflow.save(session_id, updated_session)

    return _respond(response)


def _respond(data: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]
