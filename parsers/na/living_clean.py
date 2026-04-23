import logging
import re

from core.schema import create_node

logger = logging.getLogger(__name__)


def _heading_text_plausible(clean_text: str) -> bool:
    """Reject obvious OCR junk for section / chapter titles; keep normal prose."""
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

_HANDLED = frozenset({"heading", "paragraph", "image", "list", "quote", "toc"})


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for Living Clean.
    Builds a hierarchy of Chapter -> Section -> Paragraph.
    """
    chapters = []
    current_chapter = None
    current_section = None

    awaiting_chapter_title = False

    def close_chapter():
        """Helper to save the current chapter before starting a new one."""
        if current_chapter and len(current_chapter["children"]) > 0:
            chapters.append(current_chapter)

    def append_body(node):
        if current_section:
            current_section["children"].append(node)
        else:
            current_chapter["children"].append(node)

    for item in flow:
        if item["type"] not in _HANDLED:
            logger.warning(
                "living_clean: unknown flow type %r — preserving text as paragraph",
                item.get("type"),
            )
            if not current_chapter:
                current_chapter = create_node("chapter", title="Front Matter & Preface")
            if item.get("text") is not None:
                meta = dict(_flow_meta(item) or {})
                meta["unknown_flow_type"] = item["type"]
                append_body(
                    create_node(
                        "paragraph",
                        text=item.get("text", ""),
                        page=item.get("page"),
                        meta=meta,
                    )
                )
            continue

        raw_text = item.get("text", "")
        clean_text = raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        upper_clean = clean_text.upper()
        page_num = item.get("page")

        if item["type"] == "image":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Front Matter & Preface")
            img_node = create_node(
                "image", src=item["src"], page=page_num, meta=_flow_meta(item)
            )
            if current_section:
                current_section["children"].append(img_node)
            else:
                current_chapter["children"].append(img_node)
            continue

        if item["type"] == "list":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Front Matter & Preface")
            child_nodes = [
                create_node("list_item", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "list_item"
            ]
            if child_nodes:
                list_node = create_node(
                    "list", children=child_nodes, meta=_flow_meta(item)
                )
                append_body(list_node)
            else:
                logger.warning("living_clean: empty list skipped")
            continue

        if item["type"] == "quote":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Front Matter & Preface")
            if len(clean_text) > 2:
                append_body(
                    create_node(
                        "quote", text=raw_text, page=page_num, meta=_flow_meta(item)
                    )
                )
            continue

        if item["type"] == "toc":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Front Matter & Preface")
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
            else:
                logger.warning("living_clean: empty toc skipped")
            continue

        if upper_clean.startswith("CHAPTER "):
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            current_section = None
            awaiting_chapter_title = True
            continue

        if not current_chapter:
            current_chapter = create_node("chapter", title="Front Matter & Preface")

        if awaiting_chapter_title and item["type"] in ["heading", "paragraph"]:
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
            current_chapter["title"] = f"{current_chapter['title']}: {clean_text.title()}"
            title_node = create_node(
                "heading",
                text=raw_text,
                page=page_num,
                level=item.get("level"),
                meta=_flow_meta(item),
            )
            current_chapter["children"].append(title_node)
            awaiting_chapter_title = False
            continue

        if item["type"] == "heading" and len(clean_text) > 3:
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
            current_section = create_node("section", title=clean_text.title())
            current_chapter["children"].append(current_section)
            heading_node = create_node(
                "heading",
                text=raw_text,
                page=page_num,
                level=item.get("level"),
                meta=_flow_meta(item),
            )
            current_section["children"].append(heading_node)
            continue

        if len(clean_text) > 2 and item["type"] == "paragraph":
            para_node = create_node(
                "paragraph", text=raw_text, page=page_num, meta=_flow_meta(item)
            )
            append_body(para_node)

    close_chapter()

    return chapters
