import logging
import re

from core.schema import create_node

logger = logging.getLogger(__name__)

_HANDLED = frozenset({"heading", "paragraph", "image", "list", "quote", "toc"})


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def _ocr_fix_title(s: str) -> str:
    if not s:
        return s
    t = s
    t = re.sub(r"(?i)CHAPTE\s+R\b", "CHAPTER", t)
    t = re.sub(r"(?i)CHAPT\s+ER\b", "CHAPTER", t)
    t = re.sub(r"(?i)CHAP\s+TER\b", "CHAPTER", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _heading_text_plausible(clean_text: str) -> bool:
    t = clean_text.strip()
    if len(t) < 3:
        return False
    for w in re.findall(r"\S+", t):
        core = re.sub(r"^[^\w]+|[^\w]+$", "", w)
        if len(core) < 4:
            continue
        if any(c.isdigit() for c in core) and any(c.isalpha() for c in core):
            if re.search(r"[A-Za-z]\d[A-Za-z]", core) or re.search(r"[A-Za-z]{2,}\d", core):
                return False
    letters = [c.lower() for c in t if c.isalpha()]
    if len(letters) >= 8:
        vow = sum(1 for c in letters if c in "aeiouy")
        if vow / len(letters) < 0.12:
            return False
    return True


def _contains_chapter_word(text: str) -> bool:
    return bool(re.search(r"\bCHAPTER\b", text, re.I))


def _is_standalone_caps_chapter_heading(clean: str) -> bool:
    u = clean.strip().upper()
    if "CHAPTER" in u:
        return False
    if len(u) < 10 or len(u) > 120:
        return False
    if clean.strip() != u:
        return False
    words = u.split()
    if len(words) < 3 or len(words) > 14:
        return False
    letters = sum(c.isalpha() for c in u)
    if letters < 8:
        return False
    return True


def _is_toc_pipe_paragraph(text: str) -> bool:
    if text.count("|") < 2:
        return False
    return bool(re.search(r"\d+\s*$", text.strip()))


def _parse_toc_paragraph(text: str, source_page) -> list:
    entries = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.count("|") < 1:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        tail = parts[-1]
        m = re.search(r"(\d+)\s*$", tail)
        if not m:
            continue
        pg = int(m.group(1))
        title = " | ".join(parts[:-1]).strip() or parts[0]
        title = _ocr_fix_title(title)
        if title:
            entries.append(create_node("toc_entry", title=title, page=pg))
    if not entries and text.count("|") >= 2:
        m = re.search(r"(\d+)\s*$", text.strip())
        pg = int(m.group(1)) if m else source_page
        title = re.sub(r"\s*\d+\s*$", "", text.strip()).strip("| ").strip()
        if title:
            entries.append(create_node("toc_entry", title=_ocr_fix_title(title), page=pg))
    return entries


def _merge_adjacent_headings(flow: list) -> list:
    out = []
    i = 0
    n = len(flow)
    while i < n:
        it = flow[i]
        if it.get("type") != "heading":
            out.append(it)
            i += 1
            continue
        texts = [_ocr_fix_title(it.get("text") or "")]
        j = i + 1
        while j < n and flow[j].get("type") == "heading":
            texts.append(_ocr_fix_title(flow[j].get("text") or ""))
            j += 1
        merged = dict(it)
        merged["text"] = ": ".join(t for t in texts if t)
        merged["page"] = it.get("page")
        out.append(merged)
        i = j
    return out


def parse(flow: list) -> list:
    flow = _merge_adjacent_headings(list(flow))

    chapters = []
    cur_ch = None
    cur_sec = None
    cur_sub = None
    awaiting_chapter_title = False
    book_two_mode = False

    def close_chapter():
        nonlocal cur_ch, cur_sec, cur_sub
        if cur_ch is not None:
            chapters.append(cur_ch)
        cur_ch = None
        cur_sec = None
        cur_sub = None

    def ensure_chapter(title="Preface"):
        nonlocal cur_ch, cur_sec, cur_sub, awaiting_chapter_title
        if cur_ch is None:
            cur_ch = create_node("chapter", title=title, children=[])
            cur_sec = None
            cur_sub = None
            awaiting_chapter_title = False

    def start_chapter(title: str):
        nonlocal cur_ch, cur_sec, cur_sub, awaiting_chapter_title, book_two_mode
        close_chapter()
        cur_ch = create_node("chapter", title=_ocr_fix_title(title), children=[])
        cur_sec = None
        cur_sub = None
        awaiting_chapter_title = False

    def start_section(title: str):
        nonlocal cur_sec, cur_sub
        ensure_chapter()
        cur_sub = None
        cur_sec = create_node("section", title=_ocr_fix_title(title), children=[])
        cur_ch["children"].append(cur_sec)

    def append_body(node):
        nonlocal cur_ch, cur_sec, cur_sub
        if node is None:
            return
        ensure_chapter()
        target = cur_sub or cur_sec or cur_ch
        target["children"].append(node)

    def heading_level(item):
        lv = item.get("level")
        try:
            return int(lv) if lv is not None else None
        except (TypeError, ValueError):
            return None

    for item in flow:
        if item.get("type") not in _HANDLED:
            logger.warning(
                "basic_text: unknown flow type %r — preserving as paragraph",
                item.get("type"),
            )
            if item.get("text") is not None:
                append_body(
                    create_node(
                        "paragraph",
                        text=item.get("text", ""),
                        page=item.get("page"),
                        meta={**(_flow_meta(item) or {}), "unknown_flow_type": item["type"]},
                    )
                )
            continue

        raw_text = item.get("text", "")
        clean_text = raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        clean_text = _ocr_fix_title(clean_text)
        upper_clean = clean_text.upper()
        page_num = item.get("page")

        if item["type"] == "image":
            append_body(
                create_node("image", src=item["src"], page=page_num, meta=_flow_meta(item))
            )
            continue

        if item["type"] == "list":
            child_nodes = [
                create_node("list_item", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "list_item"
            ]
            if child_nodes:
                append_body(create_node("list", children=child_nodes, meta=_flow_meta(item)))
            else:
                logger.warning("basic_text: empty list skipped")
            continue

        if item["type"] == "quote":
            if len(clean_text) > 2:
                append_body(
                    create_node("quote", text=raw_text, page=page_num, meta=_flow_meta(item))
                )
            continue

        if item["type"] == "toc":
            child_nodes = [
                create_node("toc_line", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "toc_line"
            ]
            if child_nodes:
                append_body(
                    create_node(
                        "toc",
                        children=child_nodes,
                        page=item.get("page"),
                        meta=_flow_meta(item),
                    )
                )
            continue

        if upper_clean in ["BOOK TWO", "BOOK TWO: PERSONAL STORIES", "PERSONAL STORIES"]:
            start_chapter("Book Two: Personal Stories")
            book_two_mode = True
            continue

        is_chapter_heading = item["type"] == "heading" and _contains_chapter_word(clean_text)
        is_chapter_para = (
            item["type"] == "paragraph"
            and len(clean_text) < 90
            and upper_clean.strip().startswith("CHAPTER")
        )
        is_caps_chapter = item["type"] in ("heading", "paragraph") and _is_standalone_caps_chapter_heading(
            clean_text
        )

        if upper_clean.startswith("CHAPTER ") or is_chapter_heading or is_chapter_para or is_caps_chapter:
            start_chapter(clean_text.title())
            if upper_clean.startswith("CHAPTER ") or is_chapter_para:
                awaiting_chapter_title = True
            continue

        if upper_clean in ["OUR SYMBOL", "PREFACE", "INTRODUCTION"]:
            start_chapter(clean_text.title())
            continue

        if book_two_mode and item["type"] == "heading" and len(clean_text) > 3:
            if not upper_clean.startswith(("STEP ", "TRADITION ")):
                if not _heading_text_plausible(clean_text):
                    append_body(
                        create_node(
                            "paragraph",
                            text=raw_text,
                            page=page_num,
                            meta=_flow_meta(item),
                        )
                    )
                    continue
                start_chapter(clean_text.title())
                continue

        if item["type"] == "paragraph" and _is_toc_pipe_paragraph(raw_text):
            toc_nodes = _parse_toc_paragraph(raw_text, page_num)
            if toc_nodes:
                ensure_chapter()
                cur_sec = None
                cur_sub = None
                cur_ch["children"].append(
                    create_node("section", title="Table of Contents", children=toc_nodes)
                )
            continue

        ensure_chapter()

        if awaiting_chapter_title and item["type"] in ("heading", "paragraph"):
            if not _heading_text_plausible(clean_text):
                awaiting_chapter_title = False
                append_body(
                    create_node(
                        "paragraph",
                        text=raw_text,
                        page=page_num,
                        meta=_flow_meta(item),
                    )
                )
                continue
            cur_ch["title"] = f"{cur_ch['title']}: {clean_text.title()}"
            append_body(
                create_node(
                    "heading",
                    text=raw_text,
                    page=page_num,
                    level=item.get("level"),
                    meta=_flow_meta(item),
                )
            )
            awaiting_chapter_title = False
            continue

        if item["type"] == "heading":
            lv = heading_level(item)
            if lv == 2:
                start_section(clean_text)
                continue
            if lv == 3:
                if cur_sec is None:
                    cur_sec = create_node("section", title="", children=[])
                    cur_ch["children"].append(cur_sec)
                cur_sub = create_node("subsection", title=clean_text, children=[])
                cur_sec["children"].append(cur_sub)
                continue
            if not _heading_text_plausible(clean_text):
                append_body(
                    create_node(
                        "paragraph",
                        text=raw_text,
                        page=page_num,
                        meta=_flow_meta(item),
                    )
                )
                continue
            append_body(
                create_node(
                    "heading",
                    text=raw_text,
                    page=page_num,
                    level=item.get("level"),
                    meta=_flow_meta(item),
                )
            )
            continue

        if len(clean_text) > 2 and item["type"] == "paragraph":
            append_body(
                create_node(
                    "paragraph",
                    text=raw_text,
                    page=page_num,
                    meta=_flow_meta(item),
                )
            )

    close_chapter()

    if not chapters:
        chapters.append(create_node("chapter", title="Preface", children=[]))

    return chapters
