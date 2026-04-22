# Allowed block/node types
BLOCK_TYPES = {
    "chapter",
    "section",
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
):
    """
    Creates a schema-compliant node.
    Headings always include ``level`` (1–3) in the output dict when type is ``heading``.
    """

    if type not in BLOCK_TYPES:
        raise ValueError(f"Invalid block type: {type}")

    node = {
        "id": id,
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
    return node
