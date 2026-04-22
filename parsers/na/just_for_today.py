import logging

from core.schema import create_node

logger = logging.getLogger(__name__)

_HANDLED = frozenset({"heading", "paragraph", "image", "list", "quote", "toc"})


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def _preface_node_from_item(item):
    """Turn a pre-first-date flow block into a schema node for the intro section."""
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
            logger.warning("just_for_today: empty toc in preface skipped")
            return None
        return create_node("toc", children=child_nodes, page=item.get("page"), meta=meta)
    logger.warning(
        "just_for_today: unknown preface flow type %r — preserving as paragraph", t
    )
    if item.get("text") is None:
        return None
    m = dict(meta or {})
    m["unknown_flow_type"] = t
    return create_node("paragraph", text=item.get("text", ""), page=pg, meta=m)


def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for Just For Today.
    """
    entries = []
    current_entry = None
    preface_buffer = []

    months = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )

    for item in flow:
        if item["type"] not in _HANDLED:
            logger.warning(
                "just_for_today: unknown flow type %r — preserving text as paragraph",
                item.get("type"),
            )
            if not current_entry:
                if item.get("text"):
                    preface_buffer.append(
                        create_node(
                            "paragraph",
                            text=item.get("text", ""),
                            page=item.get("page"),
                            meta={"unknown_flow_type": item.get("type")},
                        )
                    )
            else:
                if item.get("text"):
                    current_entry["children"].append(
                        create_node(
                            "paragraph",
                            text=item.get("text", ""),
                            page=item.get("page"),
                            meta={"unknown_flow_type": item.get("type")},
                        )
                    )
            continue

        raw_text = item.get("text", "")
        clean_text = raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        page_num = item.get("page")

        parts = clean_text.split()
        is_date = bool(parts) and parts[0] in months and len(parts) <= 4

        if is_date:
            if preface_buffer:
                entries.append(
                    create_node(
                        "section",
                        title="Introduction & Front Matter",
                        children=preface_buffer,
                    )
                )
                preface_buffer = []

            if current_entry:
                _clean_temp_meta(current_entry)
                entries.append(current_entry)

            current_entry = create_node(
                type="entry",
                title=clean_text,
                meta={"has_quote": False, "has_title": False},
            )
            continue

        if not current_entry:
            node = _preface_node_from_item(item)
            if node is not None:
                preface_buffer.append(node)
            continue

        if item["type"] == "list":
            child_nodes = [
                create_node("list_item", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "list_item"
            ]
            if child_nodes:
                current_entry["children"].append(
                    create_node("list", children=child_nodes, meta=_flow_meta(item))
                )
            else:
                logger.warning("just_for_today: empty list skipped inside entry")
            continue

        if item["type"] == "image":
            current_entry["children"].append(
                create_node(
                    type="image", src=item["src"], page=page_num, meta=_flow_meta(item)
                )
            )
            continue

        if item["type"] == "toc":
            child_nodes = [
                create_node("toc_line", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "toc_line"
            ]
            if child_nodes:
                current_entry["children"].append(
                    create_node(
                        "toc",
                        children=child_nodes,
                        page=item.get("page"),
                        meta=_flow_meta(item),
                    )
                )
            else:
                logger.warning("just_for_today: empty toc skipped")
            continue

        if item["type"] == "quote":
            current_entry["children"].append(
                create_node(
                    "quote",
                    text=raw_text,
                    page=page_num,
                    meta=_flow_meta(item),
                )
            )
            current_entry["meta"]["has_quote"] = True
            continue

        if item["type"] == "heading":
            current_entry["children"].append(
                create_node(
                    "heading",
                    text=raw_text,
                    page=page_num,
                    level=item.get("level"),
                    meta=_flow_meta(item),
                )
            )
            current_entry["meta"]["has_title"] = True
            continue

        if (
            not current_entry["meta"]["has_title"]
            and len(clean_text.split()) <= 6
            and not clean_text.endswith(".")
        ):
            title_node = create_node(
                type="heading",
                text=raw_text,
                page=page_num,
                level=2,
                meta=_flow_meta(item),
            )
            current_entry["children"].append(title_node)
            current_entry["meta"]["has_title"] = True
            continue

        if (
            not current_entry["meta"]["has_quote"]
            and (raw_text.startswith("*") or len(clean_text.split()) < 25)
        ):
            quote_node = create_node(
                type="quote",
                text=raw_text,
                page=page_num,
                meta=_flow_meta(item),
            )
            current_entry["children"].append(quote_node)
            current_entry["meta"]["has_quote"] = True
            continue

        if clean_text.lower().startswith("just for today:"):
            aff_node = create_node(
                type="affirmation", text=raw_text, page=page_num, meta=_flow_meta(item)
            )
            current_entry["children"].append(aff_node)
            current_entry["meta"]["done"] = True
            continue

        if len(clean_text) > 3:
            current_entry["children"].append(
                create_node(
                    type="paragraph",
                    text=raw_text,
                    page=page_num,
                    meta=_flow_meta(item),
                )
            )

    if preface_buffer:
        entries.insert(
            0,
            create_node(
                "section",
                title="Introduction & Front Matter",
                children=preface_buffer,
            ),
        )

    if current_entry:
        _clean_temp_meta(current_entry)
        entries.append(current_entry)

    return entries


def _clean_temp_meta(entry_node):
    """Removes the temporary tracking variables from the final JSON."""
    entry_node["meta"].pop("has_quote", None)
    entry_node["meta"].pop("has_title", None)
