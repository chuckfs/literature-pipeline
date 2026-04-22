"""
Render-oriented heuristics: heading levels, subheading promotion, quotes, TOC lines.
Conservative — prefer under-detection; never drop text (reclassify only).
"""

from __future__ import annotations

import re

from core.reading_quality import is_probable_toc_leader_line

_SMALL_WORDS = frozenset(
    "a an the and or but nor in on at to for of as by per via if vs et al".split()
)


def is_approx_title_case(text: str) -> bool:
    """Loose title-case check (allows small words lowercase after first word)."""
    words = text.strip().split()
    if not words:
        return False
    for i, w in enumerate(words):
        core = re.sub(r"^[^\w]+|[^\w]+$", "", w)
        if not core or not core[0].isalpha():
            continue
        if i > 0 and core.lower() in _SMALL_WORDS:
            continue
        if not core[0].isupper():
            return False
    return True


def is_all_caps_heading(text: str) -> bool:
    t = text.strip()
    if not any(c.isalpha() for c in t):
        return False
    letters = [c for c in t if c.isalpha()]
    return letters and all(c.isupper() for c in letters)


def assign_heading_level(text: str) -> int:
    """
    Heuristic heading depth for Docling headings (and promoted subheads).
    Level 1: very short + (title case or ALL CAPS)
    Level 2: short + title case
    Level 3: everything else
    """
    t = text.strip()
    words = t.split()
    n = len(words)
    if n <= 4 and (is_approx_title_case(t) or is_all_caps_heading(t)):
        return 1
    if n <= 8 and is_approx_title_case(t):
        return 2
    return 3


def paragraph_might_be_subheading(text: str) -> int | None:
    """
    Promote short title-case lines without sentence-ending punctuation to heading.
    Returns target level (2 or 3) or None.
    """
    t = text.strip()
    words = t.split()
    n = len(words)
    if n == 0 or n > 10:
        return None
    if t.endswith((".", "!", "?", ":", ";")):
        return None
    if not is_approx_title_case(t):
        return None
    return 2 if n <= 5 else 3


_QUOTE_OPEN = frozenset(('"', "\u201c", "\u2018", "\u00ab", "„"))
_QUOTE_CLOSE = frozenset(('"', "\u201d", "\u2019", "\u00bb"))


def paragraph_might_be_quote(text: str) -> bool:
    """
    Very conservative quote detection (wrapping punctuation only).
    """
    t = text.strip()
    if len(t) < 3:
        return False
    core = t.strip("*").strip("_").strip()
    if len(core) < 2:
        return False
    if core[0] in _QUOTE_OPEN and core[-1] in _QUOTE_CLOSE and core[0] != core[-1]:
        return True
    if core[0] == '"' and core[-1] == '"' and len(core) >= 4:
        return True
    return False


def is_soft_toc_cluster_line(text: str, page: int | None) -> bool:
    """Early-page TOC-ish rows without the strong dot-leader pattern."""
    if page is None or page > 5 or len(text) >= 100:
        return False
    if re.search(r"\.{3,}", text):
        return True
    if re.search(r"\s{2,}\d{1,4}\s*$", text):
        return True
    return False


def should_capture_as_toc_line(text: str, page: int | None) -> bool:
    """Whether a line should be stored in a toc block (when TOC structuring is on)."""
    if is_probable_toc_leader_line(text):
        return True
    return is_soft_toc_cluster_line(text, page)


def enrich_heading_item(item: dict) -> dict:
    """Return a shallow copy of a heading flow item with ``level`` set."""
    out = dict(item)
    if out.get("level") is None and out.get("text"):
        out["level"] = assign_heading_level(out["text"])
    elif out.get("level") is None:
        out["level"] = 3
    return out
