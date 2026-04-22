import logging
import re

from core.semantics import (
    enrich_heading_item,
    paragraph_might_be_quote,
    paragraph_might_be_subheading,
    should_capture_as_toc_line,
)

logger = logging.getLogger(__name__)


def flush_toc_buffer(toc_buffer: list, cleaned: list, stats: dict | None) -> None:
    if not toc_buffer:
        return
    children = [
        {"type": "toc_line", "text": e["text"], "page": e.get("page")}
        for e in toc_buffer
    ]
    cleaned.append(
        {
            "type": "toc",
            "page": toc_buffer[0].get("page"),
            "children": children,
        }
    )
    toc_buffer.clear()
    if stats is not None:
        stats["toc_blocks_created"] = stats.get("toc_blocks_created", 0) + 1


def clean_flow(flow, return_stats=False, strip_toc_lines=False):
    cleaned = []
    buffer = []
    list_buffer = []
    toc_buffer = []

    stats = {
        "input_items": len(flow),
        "output_items": 0,
        "noise_removed": 0,
        "lists_created": 0,
        "list_items_created": 0,
        "paragraph_merges": 0,
        "toc_blocks_created": 0,
        "toc_lines_structured": 0,
    }

    for item in flow:
        if item["type"] != "paragraph":
            flush_toc_buffer(toc_buffer, cleaned, stats)
            flush_buffer(buffer, cleaned)
            flush_list(list_buffer, cleaned, stats)
            if item["type"] == "heading":
                cleaned.append(enrich_heading_item(dict(item)))
            else:
                cleaned.append(dict(item))
            continue

        text = normalize_text(item["text"])
        page = item.get("page")

        if strip_toc_lines:
            if toc_buffer and not should_capture_as_toc_line(text, page):
                flush_toc_buffer(toc_buffer, cleaned, stats)
            if should_capture_as_toc_line(text, page):
                flush_buffer(buffer, cleaned)
                flush_list(list_buffer, cleaned, stats)
                toc_buffer.append({"text": text, "page": page})
                stats["toc_lines_structured"] += 1
                continue

        if is_noise(text, page):
            stats["noise_removed"] += 1
            continue

        if is_list_item(text):
            items = split_inline_list(text)
            if not items:
                logger.warning(
                    "split_inline_list returned empty for list-like line: %r", text[:120]
                )
            for t in items:
                list_buffer.append(
                    {"type": "list_item", "text": t, "page": page}
                )
                stats["list_items_created"] += 1
            continue
        else:
            flush_list(list_buffer, cleaned, stats)

        if paragraph_might_be_quote(text):
            flush_buffer(buffer, cleaned)
            cleaned.append({"type": "quote", "text": text, "page": page})
            continue

        sub_lv = paragraph_might_be_subheading(text)
        if sub_lv is not None:
            flush_buffer(buffer, cleaned)
            cleaned.append(
                enrich_heading_item(
                    {"type": "heading", "text": text, "page": page, "level": sub_lv}
                )
            )
            continue

        if buffer:
            if should_merge(buffer[-1], text, buffer[-1].get("page"), page):
                buffer[-1]["text"] += " " + text
                stats["paragraph_merges"] += 1
            else:
                buffer.append({"type": "paragraph", "text": text, "page": page})
        else:
            buffer.append({"type": "paragraph", "text": text, "page": page})

    flush_toc_buffer(toc_buffer, cleaned, stats)
    flush_buffer(buffer, cleaned)
    flush_list(list_buffer, cleaned, stats)
    stats["output_items"] = len(cleaned)
    if return_stats:
        return cleaned, stats
    return cleaned


def flush_list(list_buffer, cleaned, stats=None):
    if not list_buffer:
        return

    cleaned.append(
        {
            "type": "list",
            "children": list_buffer.copy(),
        }
    )
    if stats is not None:
        stats["lists_created"] += 1
    list_buffer.clear()


def flush_buffer(buffer, cleaned):
    for b in buffer:
        cleaned.append(b)
    buffer.clear()


def normalize_text(text):
    text = re.sub(
        r"(?:\b[A-Z]\s+){2,}[A-Z]\b",
        lambda m: m.group(0).replace(" ", ""),
        text,
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_noise(text, page=None):
    if len(text) < 3:
        return True

    if re.match(r"^[^a-zA-Z]+$", text):
        return True

    if re.match(r"^[A-Z0-9\-]+$", text) and len(text) < 6:
        return True

    lowered = text.lower()

    if _looks_like_url_line(lowered, text):
        return True

    if _looks_like_copyright_imprint(lowered, text):
        return True

    if "catalog item" in lowered:
        return True

    if "world service office" in lowered and len(text) < 120:
        return True

    if page and page <= 3 and len(text) < 25:
        letters = sum(c.isalpha() for c in text)
        if letters == 0:
            return True
        lower_letters = sum(c.islower() for c in text)
        if letters >= 3 and lower_letters == 0:
            return True
        digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
        if digit_ratio >= 0.35:
            return True
        punct_ratio = sum(not c.isalnum() and not c.isspace() for c in text) / max(
            len(text), 1
        )
        if punct_ratio >= 0.4:
            return True
        return False

    return False


def _looks_like_url_line(lowered: str, text: str) -> bool:
    if "www." not in lowered and "http://" not in lowered and "https://" not in lowered:
        return False
    t = text.strip()
    if len(t) > 100:
        return False
    return True


def _looks_like_copyright_imprint(lowered: str, text: str) -> bool:
    if len(text) > 280 or len(text.split()) > 40:
        return False
    if "all rights reserved" in lowered:
        return True
    if "isbn" in lowered and len(text) < 200:
        return True
    if "cataloging" in lowered and "publication" in lowered:
        return True
    idx = lowered.find("copyright")
    if idx != -1 and idx < 30 and len(text) < 200:
        return True
    if "©" in text and len(text) < 160 and len(text.split()) < 25:
        return True
    return False


def is_list_item(text):
    t = text.strip()
    if re.match(r"^[\-\u2013\u2014•\*]\s+", t):
        return True
    if re.match(r"^\d+[\.\)]\s+", t):
        return True
    if re.match(r"^[a-zA-Z]\)\s+", t):
        return True
    return False


def should_merge(prev, current, prev_page, current_page):
    if prev_page != current_page:
        return False

    if not current or not str(current).strip():
        return False

    prev_txt = prev["text"].rstrip()
    if prev_txt.endswith((".", "!", "?")):
        return False

    if prev_txt.endswith("-") or prev_txt.endswith("\u2010"):
        return True

    if current[0].islower():
        return True

    return False


def split_inline_list(text):
    parts = re.split(r"(?<!\.)\s+(?=[A-Z][a-z])", text)
    merged = []
    for p in (x.strip() for x in parts):
        if not p:
            continue
        if len(p) <= 2 and merged:
            merged[-1] = (merged[-1] + " " + p).strip()
        else:
            merged.append(p)
    if not merged:
        return [text.strip()] if text.strip() else []
    return merged
