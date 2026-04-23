import logging

from core.schema import create_node

logger = logging.getLogger(__name__)


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def _material_node_from_item(item):
    """Map a non-heading flow block to a leaf/container schema node (no hierarchy)."""
    t = item.get("type")
    if t == "paragraph":
        return create_node(
            type="paragraph",
            text=item["text"],
            page=item.get("page"),
            meta=_flow_meta(item),
        )
    if t == "image":
        return create_node(
            type="image",
            src=item["src"],
            page=item.get("page"),
            meta=_flow_meta(item),
        )
    if t == "list":
        child_nodes = []
        for ch in item.get("children", []):
            if ch.get("type") == "list_item":
                child_nodes.append(
                    create_node(
                        type="list_item",
                        text=ch["text"],
                        page=ch.get("page"),
                    )
                )
        if not child_nodes:
            logger.warning("generic parser: empty list skipped (no list_item children)")
            return None
        return create_node(type="list", children=child_nodes)
    if t == "quote":
        return create_node(
            type="quote",
            text=item.get("text", ""),
            page=item.get("page"),
            meta=_flow_meta(item),
        )
    if t == "toc":
        child_nodes = [
            create_node("toc_line", text=ch["text"], page=ch.get("page"))
            for ch in item.get("children", [])
            if ch.get("type") == "toc_line"
        ]
        if not child_nodes:
            logger.warning("generic parser: empty toc skipped")
            return None
        meta = _flow_meta(item) or {}
        return create_node(
            type="toc",
            children=child_nodes,
            page=item.get("page"),
            meta=meta,
        )
    logger.warning(
        "generic parser: unknown flow type %r — preserving text as paragraph",
        t,
    )
    if item.get("text") is None:
        return None
    m = dict(_flow_meta(item) or {})
    m["unknown_flow_type"] = t
    return create_node(
        type="paragraph",
        text=item.get("text", ""),
        page=item.get("page"),
        meta=m,
    )


def parse(flow):
    """
    Build a book hierarchy from flat flow: level 1 → chapter, 2 → section, 3 → subsection.
    Material (paragraph, list, image, quote, toc) attaches to the deepest open container.
    """
    chapters = []
    cur_ch = None
    cur_sec = None
    cur_sub = None

    def ensure_chapter():
        nonlocal cur_ch, cur_sec, cur_sub
        if cur_ch is None:
            cur_ch = create_node("chapter", title="Preface", children=[])
            chapters.append(cur_ch)
            cur_sec = None
            cur_sub = None

    def append_material(node):
        nonlocal cur_ch, cur_sec, cur_sub
        if node is None:
            return
        ensure_chapter()
        target = cur_sub or cur_sec or cur_ch
        target["children"].append(node)

    for item in flow:
        t = item.get("type")

        if t == "heading":
            text = (item.get("text") or "").strip()
            title = text if text else "Untitled"
            lvl = item.get("level")
            try:
                lvl = int(lvl) if lvl is not None else 3
            except (TypeError, ValueError):
                lvl = 3
            if lvl < 1:
                lvl = 1
            if lvl > 3:
                lvl = 3

            if lvl == 1:
                cur_ch = create_node("chapter", title=title, children=[])
                chapters.append(cur_ch)
                cur_sec = None
                cur_sub = None
            elif lvl == 2:
                ensure_chapter()
                cur_sub = None
                cur_sec = create_node("section", title=title, children=[])
                cur_ch["children"].append(cur_sec)
            else:
                ensure_chapter()
                if cur_sec is None:
                    cur_sec = create_node("section", title="", children=[])
                    cur_ch["children"].append(cur_sec)
                cur_sub = create_node("subsection", title=title, children=[])
                cur_sec["children"].append(cur_sub)
            continue

        node = _material_node_from_item(item)
        append_material(node)

    if not chapters:
        chapters.append(create_node("chapter", title="Preface", children=[]))

    return chapters
