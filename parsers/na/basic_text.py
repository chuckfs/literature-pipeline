import logging

from core.schema import create_node

logger = logging.getLogger(__name__)

_HANDLED = frozenset({"heading", "paragraph", "image", "list", "quote", "toc"})


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for the Basic Text.
    """
    chapters = []
    current_chapter = None

    awaiting_chapter_title = False
    book_two_mode = False

    def close_chapter():
        """Helper to save the current chapter before starting a new one."""
        if current_chapter and len(current_chapter["children"]) > 0:
            chapters.append(current_chapter)

    for item in flow:
        if item["type"] not in _HANDLED:
            logger.warning(
                "basic_text: unknown flow type %r — preserving text as paragraph",
                item.get("type"),
            )
            if not current_chapter:
                current_chapter = create_node("chapter", title="Title Page & Copyright")
            if item.get("text") is not None:
                meta = dict(_flow_meta(item) or {})
                meta["unknown_flow_type"] = item["type"]
                current_chapter["children"].append(
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
                current_chapter = create_node("chapter", title="Title Page & Copyright")
            current_chapter["children"].append(
                create_node("image", src=item["src"], page=page_num, meta=_flow_meta(item))
            )
            continue

        if item["type"] == "list":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Title Page & Copyright")
            child_nodes = [
                create_node("list_item", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "list_item"
            ]
            if child_nodes:
                current_chapter["children"].append(
                    create_node("list", children=child_nodes, meta=_flow_meta(item))
                )
            else:
                logger.warning("basic_text: empty list skipped")
            continue

        if item["type"] == "quote":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Title Page & Copyright")
            if len(clean_text) > 2:
                current_chapter["children"].append(
                    create_node(
                        "quote", text=raw_text, page=page_num, meta=_flow_meta(item)
                    )
                )
            continue

        if item["type"] == "toc":
            if not current_chapter:
                current_chapter = create_node("chapter", title="Title Page & Copyright")
            child_nodes = [
                create_node("toc_line", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "toc_line"
            ]
            if child_nodes:
                current_chapter["children"].append(
                    create_node(
                        "toc",
                        children=child_nodes,
                        page=item.get("page"),
                        meta=_flow_meta(item),
                    )
                )
            else:
                logger.warning("basic_text: empty toc skipped")
            continue

        if upper_clean in ["BOOK TWO", "BOOK TWO: PERSONAL STORIES", "PERSONAL STORIES"]:
            close_chapter()
            current_chapter = create_node("chapter", title="Book Two: Personal Stories")
            book_two_mode = True
            continue

        if upper_clean.startswith("CHAPTER "):
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            awaiting_chapter_title = True
            continue

        if upper_clean in ["OUR SYMBOL", "PREFACE", "INTRODUCTION"]:
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            continue

        if book_two_mode and item["type"] == "heading" and len(clean_text) > 3:
            if not upper_clean.startswith(("STEP ", "TRADITION ")):
                close_chapter()
                current_chapter = create_node("chapter", title=clean_text.title())
                continue

        if not current_chapter:
            current_chapter = create_node("chapter", title="Title Page & Copyright")

        if awaiting_chapter_title and item["type"] in ["heading", "paragraph"]:
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

        if len(clean_text) > 2:
            if item["type"] == "heading":
                body_node = create_node(
                    "heading",
                    text=raw_text,
                    page=page_num,
                    level=item.get("level"),
                    meta=_flow_meta(item),
                )
            else:
                body_node = create_node(
                    "paragraph",
                    text=raw_text,
                    page=page_num,
                    meta=_flow_meta(item),
                )
            current_chapter["children"].append(body_node)

    close_chapter()

    return chapters
