"""
Lightweight reading-quality helpers (headings, TOC hints, hyphenation merge hints).
"""

from __future__ import annotations

import re


def normalize_reader_heading(text: str) -> str:
    """Collapse redundant whitespace in heading lines without changing wording."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    return text


def is_probable_toc_leader_line(text: str) -> bool:
    """
    Heuristic for table-of-contents rows: dot leaders and trailing page number.
    Conservative — only strong patterns to avoid stripping real prose when enabled.
    """
    t = text.strip()
    if len(t) > 180:
        return False
    if not re.search(r"\.{4,}", t):
        return False
    if not re.search(r"\d+\s*$", t):
        return False
    if len(t.split()) > 18:
        return False
    return True
