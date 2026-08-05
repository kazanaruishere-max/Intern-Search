"""Helper kompatibilitas lintas platform (encoding UTF-8)."""

from __future__ import annotations

import sys


def setup_utf8_io() -> None:
    """Pastikan stdout/stderr memakai UTF-8 agar tidak error di Windows."""
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
