# Allowed block/node types
import uuid

BLOCK_TYPES = {
    "chapter",
    "section",
    "subsection",
    "entry",
    "heading",
    "paragraph",
    "quote",
    "affirmation",
    "list",
    "list_item",
    "image",
    "divider",
    "toc",
    "toc_line",
    "toc_entry",
}


def create_node(
    type: str,
    text: str = None,
    title: str = None,
    children: list = None,
    meta: dict = None,
    src: str = None,
    page: int = None,
    id: str = None,
    level: int = None,
    entry_date: str = None,
    entry_quote: str = None,
    entry_body: list = None,
    entry_reflection: str = None,
):
    """
    Creates a schema-compliant node. Assigns a stable ``id`` when omitted.
    For ``entry``, optional ``entry_*`` fields map to ``date``, ``quote``, ``body``, ``reflection``.
    """

    if type not in BLOCK_TYPES:
        raise ValueError(f"Invalid block type: {type}")

    nid = id if id is not None else str(uuid.uuid4())

    node = {
        "id": nid,
        "type": type,
        "title": title,
        "text": text,
        "src": src,
        "page": page,
        "meta": meta or {},
        "children": children or [],
    }
    if type == "heading":
        node["level"] = level if level is not None else 3
    if type == "entry":
        if entry_date is not None:
            node["date"] = entry_date
        if entry_quote is not None:
            node["quote"] = entry_quote
        if entry_body is not None:
            node["body"] = entry_body
        if entry_reflection is not None:
            node["reflection"] = entry_reflection
    return node
