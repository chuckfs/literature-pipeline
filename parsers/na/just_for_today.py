import logging
import re

from core.schema import create_node

logger = logging.getLogger(__name__)

_HANDLED = frozenset({"heading", "paragraph", "image", "list", "quote", "toc"})

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def _ocr_fix_line(s: str) -> str:
    if not s:
        return s
    return re.sub(r"\s+", " ", s).strip()


def _is_ignored_jft_header(clean: str) -> bool:
    """Repeated book / section headers that should not become body content."""
    t = clean.strip()
    if re.match(r"^just\s+for\s+today:?\s*$", t, re.I):
        return True
    if t.lower() in ("just for today", "jft"):
        return True
    return False


def _preface_node_from_item(item):
    t = item["type"]
    pg = item.get("page")
    meta = _flow_meta(item)
    if t == "paragraph":
        return create_node("paragraph", text=item.get("text", ""), page=pg, meta=meta)
    if t == "heading":
        return create_node(
            "heading",
            text=item.get("text", ""),
            page=pg,
            level=item.get("level"),
            meta=meta,
        )
    if t == "image":
        return create_node("image", src=item["src"], page=pg, meta=meta)
    if t == "list":
        child_nodes = [
            create_node("list_item", text=ch["text"], page=ch.get("page"))
            for ch in item.get("children", [])
            if ch.get("type") == "list_item"
        ]
        if not child_nodes:
            logger.warning("just_for_today: empty list in preface skipped")
            return None
        return create_node("list", children=child_nodes, meta=meta)
    if t == "quote":
        return create_node("quote", text=item.get("text", ""), page=pg, meta=meta)
    if t == "toc":
        child_nodes = [
            create_node("toc_line", text=ch["text"], page=ch.get("page"))
            for ch in item.get("children", [])
            if ch.get("type") == "toc_line"
        ]
        if not child_nodes:
            return None
        return create_node("toc", children=child_nodes, page=item.get("page"), meta=meta)
    if item.get("text") is None:
        return None
    m = dict(meta or {})
    m["unknown_flow_type"] = t
    return create_node("paragraph", text=item.get("text", ""), page=pg, meta=m)


class _EntryWork:
    __slots__ = ("date", "page", "title", "quote", "body", "reflection")

    def __init__(self, date_str: str, page):
        self.date = date_str
        self.page = page
        self.title = None
        self.quote = None
        self.body = []
        self.reflection = None

    def finalize(self):
        kw = dict(
            type="entry",
            title=self.title or self.date,
            entry_date=self.date,
            page=self.page,
            meta={},
            children=[],
        )
        if self.quote is not None:
            kw["entry_quote"] = self.quote
        if self.reflection is not None:
            kw["entry_reflection"] = self.reflection
        kw["entry_body"] = list(self.body)
        return create_node(**kw)


def parse(flow: list) -> list:
    """
    Just For Today: one entry per calendar line; structured date, title, quote, body, reflection.
    """
    entries = []
    cur: _EntryWork | None = None
    preface_buffer = []

    for item in flow:
        if item.get("type") not in _HANDLED:
            logger.warning(
                "just_for_today: unknown flow type %r — preserving as paragraph",
                item.get("type"),
            )
            if item.get("text") is None:
                continue
            node = create_node(
                "paragraph",
                text=item.get("text", ""),
                page=item.get("page"),
                meta={"unknown_flow_type": item.get("type")},
            )
            if cur is None:
                preface_buffer.append(node)
            else:
                cur.body.append(node)
            continue

        raw_text = item.get("text", "")
        clean_text = _ocr_fix_line(
            raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        )
        page_num = item.get("page")

        parts = clean_text.split()
        is_date = bool(parts) and parts[0] in _MONTHS and len(parts) <= 4

        if is_date:
            if preface_buffer:
                entries.append(
                    create_node("section", title="Introduction", children=preface_buffer)
                )
                preface_buffer = []
            if cur is not None:
                entries.append(cur.finalize())
            cur = _EntryWork(clean_text, page_num)
            continue

        if cur is None:
            node = _preface_node_from_item(item)
            if node is not None:
                preface_buffer.append(node)
            continue

        if _is_ignored_jft_header(clean_text):
            continue

        if item["type"] == "list":
            child_nodes = [
                create_node("list_item", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "list_item"
            ]
            if child_nodes:
                cur.body.append(create_node("list", children=child_nodes, meta=_flow_meta(item)))
            continue

        if item["type"] == "image":
            cur.body.append(
                create_node("image", src=item["src"], page=page_num, meta=_flow_meta(item))
            )
            continue

        if item["type"] == "toc":
            child_nodes = [
                create_node("toc_line", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "toc_line"
            ]
            if child_nodes:
                cur.body.append(
                    create_node(
                        "toc",
                        children=child_nodes,
                        page=item.get("page"),
                        meta=_flow_meta(item),
                    )
                )
            continue

        if clean_text.lower().startswith("just for today:"):
            cur.reflection = raw_text.strip()
            continue

        if item["type"] == "quote":
            if cur.quote is None:
                cur.quote = raw_text.strip()
            else:
                cur.body.append(
                    create_node("quote", text=raw_text, page=page_num, meta=_flow_meta(item))
                )
            continue

        if item["type"] == "heading":
            if cur.title is None:
                cur.title = raw_text.strip()
            else:
                cur.body.append(
                    create_node(
                        "heading",
                        text=raw_text,
                        page=page_num,
                        level=item.get("level"),
                        meta=_flow_meta(item),
                    )
                )
            continue

        if (
            cur.title is None
            and len(clean_text.split()) <= 6
            and not clean_text.endswith(".")
        ):
            cur.title = raw_text.strip()
            continue

        if cur.quote is None and (
            raw_text.strip().startswith("*")
            or (len(clean_text.split()) < 25 and len(clean_text) > 2)
        ):
            cur.quote = raw_text.strip()
            continue

        if len(clean_text) > 3:
            cur.body.append(
                create_node(
                    "paragraph",
                    text=raw_text,
                    page=page_num,
                    meta=_flow_meta(item),
                )
            )

    if preface_buffer:
        entries.insert(
            0,
            create_node("section", title="Introduction", children=preface_buffer),
        )

    if cur is not None:
        entries.append(cur.finalize())

    return entries
