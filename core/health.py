"""
Pipeline health checks: detect abnormal shrinkage and unknown flow types.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def flow_text_char_count(flow: list[dict[str, Any]]) -> int:
    """Approximate character volume for text-bearing flow blocks."""
    n = 0
    for item in flow:
        t = item.get("type")
        if t in ("paragraph", "heading", "quote"):
            n += len(item.get("text") or "")
        elif t == "list":
            for ch in item.get("children") or []:
                if ch.get("type") == "list_item":
                    n += len(ch.get("text") or "")
        elif t == "toc":
            for ch in item.get("children") or []:
                if ch.get("type") == "toc_line":
                    n += len(ch.get("text") or "")
    return n


def check_cleaner_stats(stats: dict[str, int], logger_: logging.Logger | None = None) -> None:
    """Warn when the cleaner removes an unusually large fraction of blocks."""
    log = logger_ or logger
    inp = max(stats.get("input_items", 0), 1)
    out = stats.get("output_items", 0)
    removed = stats.get("noise_removed", 0)

    if out < 0.3 * inp:
        log.warning(
            "Cleaner output_items (%s) < 30%% of input_items (%s) — possible over-stripping.",
            out,
            inp,
        )

    if removed > 0.5 * inp:
        log.warning(
            "noise_removed (%s) > 50%% of input_items (%s) — review is_noise / TOC options.",
            removed,
            inp,
        )


def check_cleaner_char_shrinkage(
    chars_in: int,
    chars_out: int,
    logger_: logging.Logger | None = None,
) -> None:
    """Character-level guard: catches cases where block count is stable but text vanished."""
    log = logger_ or logger
    if chars_in <= 0:
        return
    if chars_out < 0.25 * chars_in:
        log.warning(
            "Paragraph character volume after clean (%s) < 25%% of before (%s) — investigate.",
            chars_out,
            chars_in,
        )


def scan_unknown_flow_types(
    flow: list[dict[str, Any]],
    allowed: frozenset[str],
) -> list[str]:
    """Return sorted unique types present in flow but not in allowed."""
    seen: set[str] = set()
    for item in flow:
        t = item.get("type")
        if isinstance(t, str) and t not in allowed:
            seen.add(t)
    return sorted(seen)
