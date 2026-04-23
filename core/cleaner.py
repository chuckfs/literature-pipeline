import logging
import re

from core.semantics import (
    enrich_heading_item,
    is_approx_title_case,
    paragraph_might_be_quote as _quote_wrapped_punctuation,
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
        "inline_lists_promoted": 0,
    }

    for item in flow:
        if item["type"] != "paragraph":
            flush_toc_buffer(toc_buffer, cleaned, stats)
            flush_buffer(buffer, cleaned)
            flush_list(list_buffer, cleaned, stats)
            if item["type"] == "heading":
                h = dict(item)
                h["text"] = normalize_text(h.get("text") or "")
                cleaned.append(enrich_heading_item(h))
            else:
                cleaned.append(dict(item))
            continue

        text = normalize_text(item["text"])
        page = item.get("page")

        if strip_toc_lines:
            if toc_buffer and not should_capture_as_toc_line(text):
                flush_toc_buffer(toc_buffer, cleaned, stats)
            if should_capture_as_toc_line(text):
                flush_buffer(buffer, cleaned)
                flush_list(list_buffer, cleaned, stats)
                toc_buffer.append({"text": text, "page": page})
                stats["toc_lines_structured"] += 1
                continue

        if is_noise(text, page):
            stats["noise_removed"] += 1
            continue

        inline_phrases = try_promote_inline_title_list(text)
        if inline_phrases is not None:
            flush_buffer(buffer, cleaned)
            flush_list(list_buffer, cleaned, stats)
            for phrase in inline_phrases:
                list_buffer.append(
                    {"type": "list_item", "text": phrase, "page": page}
                )
                stats["list_items_created"] += 1
            flush_list(list_buffer, cleaned, stats)
            stats["inline_lists_promoted"] += 1
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

        if paragraph_might_be_quote_flow(text):
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
    """
    Collapse spaced capitals (e.g. ``L I V I N G   C L E A N`` → ``LIVING CLEAN``).
    Breaks between spaced-all-caps ``words`` when a new 3+ letter spaced run follows.
    """
    if not text:
        return ""
    s = text.strip()
    if not s:
        return ""
    parts: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break
        if i + 2 < n and s[i].isupper() and s[i + 1] == " " and s[i + 2].isupper():
            j = i
            count = 0
            while j < n:
                if s[j].isupper():
                    count += 1
                    j += 1
                    if j < n and s[j] == " ":
                        rest = s[j + 1 :].strip()
                        if count >= 6 and rest and re.match(
                            r"^(?:[A-Z]\s+){3}[A-Z](?:\s+[A-Z])*$", rest
                        ):
                            break
                        j += 1
                        continue
                break
            seg = s[i:j].strip()
            if count >= 3:
                parts.append(seg.replace(" ", ""))
            else:
                parts.append(seg)
            i = j
            while i < n and s[i].isspace():
                i += 1
            continue
        j = i + 1
        while j < n:
            if j + 2 < n and s[j].isupper() and s[j + 1] == " " and s[j + 2].isupper():
                break
            j += 1
        parts.append(s[i:j].strip())
        i = j
    t = " ".join(p for p in parts if p)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _ocr_garbage_line(text: str) -> bool:
    """
    True only for clearly non-language OCR / junk (conservative).
    """
    t = text.strip()
    if len(t) < 4:
        return False
    if "isbn" in t.lower():
        return False

    words = re.findall(r"\S+", t)
    for w in words:
        core = re.sub(r"^[^\w]+|[^\w]+$", "", w)
        if len(core) < 4:
            continue
        if not any(c.isalpha() for c in core) or not any(c.isdigit() for c in core):
            continue
        if re.search(r"[A-Za-z]\d[A-Za-z]", core) or re.search(r"[A-Za-z]{2,}\d", core):
            return True

    letters = [c for c in t if c.isalpha()]
    if len(letters) >= 10:
        low = [c.lower() for c in letters]
        vow = sum(1 for c in low if c in "aeiouy")
        if vow / len(low) < 0.12:
            return True

    if 8 <= len(t) <= 100:
        sym = sum(1 for c in t if not c.isalnum() and not c.isspace())
        up = sum(1 for c in t if c.isupper())
        let = sum(1 for c in t if c.isalpha())
        if let > 0 and sym / len(t) > 0.38 and up / let > 0.65:
            return True

    if 10 <= len(t) <= 140:
        non_latin = sum(1 for c in t if ord(c) > 127)
        latin = sum(1 for c in t if "A" <= c <= "Z" or "a" <= c <= "z")
        if latin >= 4 and non_latin / max(latin, 1) > 0.55:
            return True

    return False


def is_noise(text, page=None):
    """Paragraph noise filter. ``page`` is accepted for API compatibility but not used."""
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

    if _ocr_garbage_line(text):
        return True

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


def try_promote_inline_title_list(text: str) -> list[str] | None:
    """
    If a paragraph looks like a run of title-case section names / TOC row (no
    sentence punctuation), split on 2+ spaces into phrases and return list_item strings.
    """
    t = text.strip()
    if len(t) < 12 or len(t) > 360:
        return None
    if re.search(r"[.!?;:]", t):
        return None

    parts = [p.strip() for p in re.split(r"\s{2,}", t) if p.strip()]
    if len(parts) < 3:
        return None

    out = []
    for p in parts:
        if len(p) < 2 or len(p) > 80:
            return None
        if not is_approx_title_case(p):
            return None
        out.append(p)
    return out


def paragraph_might_be_quote_flow(text: str) -> bool:
    """Safe quote detection: wrappers, short emotional bursts, or leading open-quote."""
    if _quote_wrapped_punctuation(text):
        return True
    t = text.strip()
    if len(t) < 4 or len(t) >= 200:
        return False
    if t.count(".") > 1 or re.search(r"[.!?]\s+[A-Za-z]", t):
        return False
    lead = re.sub(r"^[\s*_]+", "", t)[:1]
    if lead in ('"', "\u201c", "\u2018"):
        return True
    if len(t) < 150 and re.search(r"[!?]{2,}", t):
        return True
    if len(t) <= 85 and t.count(" ") <= 14 and (t.endswith("!") or t.endswith("?")):
        if "." not in t[:-1]:
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
