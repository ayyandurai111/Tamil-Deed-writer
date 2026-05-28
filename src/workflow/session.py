"""
workflow/session.py
===================
Server-side session store.

Every conversation is identified by a session_id (UUID string).
The AI carries ONLY the session_id across turns — no fields, no skeleton,
no state of any kind lives in the model context.

Thread-safe in-process dict. For multi-worker deployments replace with Redis.
"""

from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

# Sessions expire after this much inactivity
_TTL_MINUTES = 120

_lock: threading.Lock = threading.Lock()
_store: dict[str, dict] = {}


# ── Public helpers ─────────────────────────────────────────────────────────────

def new_id() -> str:
    """Generate a fresh session_id."""
    return str(uuid.uuid4())


def load(session_id: str) -> dict:
    """
    Return a deep-copy of the session dict, or a blank session if not found.
    Always returns a valid dict — callers never receive None.
    """
    _purge_expired()
    with _lock:
        raw = _store.get(session_id)
        if raw is None:
            return _blank()
        raw["_last_access"] = datetime.utcnow()
        return deepcopy(raw)


def save(session_id: str, session: dict) -> None:
    """Persist the session dict under session_id."""
    _purge_expired()
    session["_last_access"] = datetime.utcnow()
    with _lock:
        _store[session_id] = deepcopy(session)


def clear(session_id: str) -> None:
    """Delete a session (called after successful docx generation)."""
    with _lock:
        _store.pop(session_id, None)


# ── Internal ───────────────────────────────────────────────────────────────────

def _blank() -> dict:
    return {
        # Workflow position
        "step":            "detect",      # detect | collect | confirm | done
        # Deed
        "deed_type":       None,          # "agriculture" | "plot"
        "skeleton":        None,          # raw JSON template from load_skeleton
        # Field accumulation
        "fields":          {},            # merged field dict (UPPERCASE keys)
        # Review outputs
        "clean_skeleton":  None,          # filled + cleaned skeleton
        "review":          None,          # full review_draft result dict
        "warnings":        [],            # combined L1-L4 warning strings
        "errors":          [],            # critical error strings
        # Metadata
        "_last_access":    datetime.utcnow(),
    }


def _purge_expired() -> None:
    cutoff = datetime.utcnow() - timedelta(minutes=_TTL_MINUTES)
    with _lock:
        expired = [k for k, v in _store.items() if v.get("_last_access", datetime.utcnow()) < cutoff]
        for k in expired:
            del _store[k]
