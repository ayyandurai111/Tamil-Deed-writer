"""
src/file_store.py
=================
In-memory file store for generated .docx files.

Why this exists:
  Render free tier uses an ephemeral /tmp filesystem that is wiped whenever
  the service spins down (after ~15 min of inactivity).  A user who generates
  a deed and then clicks the download link a minute later may hit a freshly
  restarted instance that has no files on disk.

  This module keeps the last N generated files in process memory so the
  download endpoint can serve them even after /tmp has been cleared, as long
  as the same process is still running.

Usage:
  from file_store import put, get, all_files

  put("deed_20260524.docx", some_bytes)   # called by generate_docx
  data = get("deed_20260524.docx")        # called by download endpoint
  listing = all_files()                   # called by list endpoint
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime

# Maximum number of files to keep in memory (oldest evicted first)
_MAX_FILES = 20

_lock: threading.Lock = threading.Lock()

# OrderedDict preserves insertion order so we can evict the oldest entry
_store: OrderedDict[str, dict] = OrderedDict()


def put(filename: str, data: bytes) -> None:
    """Store file bytes in memory.  Evicts oldest entry when over capacity."""
    with _lock:
        # Evict oldest if at capacity
        while len(_store) >= _MAX_FILES:
            _store.popitem(last=False)
        _store[filename] = {
            "data":    data,
            "size_kb": round(len(data) / 1024, 1),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        # Move to end so it is the most-recently-used
        _store.move_to_end(filename)


def get(filename: str) -> bytes | None:
    """Return file bytes, or None if not in memory."""
    with _lock:
        entry = _store.get(filename)
        return entry["data"] if entry else None


def all_files() -> list[dict]:
    """Return metadata list (newest first), without the raw bytes."""
    with _lock:
        return [
            {
                "filename": name,
                "size_kb":  entry["size_kb"],
                "created":  entry["created"],
            }
            for name, entry in reversed(_store.items())
        ]
