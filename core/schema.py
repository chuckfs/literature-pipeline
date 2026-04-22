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
    "divider"
}


def create_node(
    type: str,
    text: str = None,
    title: str = None,
    children: list = None,
    meta: dict = None,
    src: str = None,
    page: int = None,
    id: str = None
):
    """
    Creates a schema-compliant node.
    """

    if type not in BLOCK_TYPES:
        raise ValueError(f"Invalid block type: {type}")

    return {
        "id": id,
        "type": type,
        "title": title,
        "text": text,
        "src": src,
        "page": page,
        "meta": meta or {},
        "children": children or []
    }
