import logging

from core.schema import create_node

logger = logging.getLogger(__name__)


def _flow_meta(item):
    fk = item.get("flow_kind")
    return {"flow_kind": fk} if fk else None


def parse(flow):
    """
    Default parser: maps flow blocks to schema nodes (paragraph, heading, list, image, quote, toc).
    Unknown types are preserved as paragraphs with meta.unknown_flow_type.
    """

    content = []

    for item in flow:
        t = item.get("type")

        if t == "paragraph":
            content.append(
                create_node(
                    type="paragraph",
                    text=item["text"],
                    page=item.get("page"),
                    meta=_flow_meta(item),
                )
            )

        elif t == "heading":
            content.append(
                create_node(
                    type="heading",
                    text=item["text"],
                    page=item.get("page"),
                    level=item.get("level"),
                    meta=_flow_meta(item),
                )
            )

        elif t == "image":
            content.append(
                create_node(
                    type="image",
                    src=item["src"],
                    page=item.get("page"),
                    meta=_flow_meta(item),
                )
            )

        elif t == "list":
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
            if child_nodes:
                content.append(create_node(type="list", children=child_nodes))
            else:
                logger.warning("generic parser: empty list skipped (no list_item children)")

        elif t == "quote":
            content.append(
                create_node(
                    type="quote",
                    text=item.get("text", ""),
                    page=item.get("page"),
                    meta=_flow_meta(item),
                )
            )

        elif t == "toc":
            child_nodes = [
                create_node("toc_line", text=ch["text"], page=ch.get("page"))
                for ch in item.get("children", [])
                if ch.get("type") == "toc_line"
            ]
            if child_nodes:
                meta = _flow_meta(item) or {}
                content.append(
                    create_node(
                        type="toc",
                        children=child_nodes,
                        page=item.get("page"),
                        meta=meta,
                    )
                )
            else:
                logger.warning("generic parser: empty toc skipped")

        else:
            logger.warning(
                "generic parser: unknown flow type %r — preserving text as paragraph",
                t,
            )
            if item.get("text") is not None:
                m = dict(_flow_meta(item) or {})
                m["unknown_flow_type"] = t
                content.append(
                    create_node(
                        type="paragraph",
                        text=item.get("text", ""),
                        page=item.get("page"),
                        meta=m,
                    )
                )

    return content
