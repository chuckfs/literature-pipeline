from core.schema import create_node


def parse(flow):
    """
    Default parser: wraps everything as paragraphs.
    """

    content = []

    for item in flow:
        if item["type"] == "paragraph":
            content.append(
                create_node(
                    type="paragraph",
                    text=item["text"],
                    page=item.get("page")
                )
            )

        elif item["type"] == "heading":
            content.append(
                create_node(
                    type="heading",
                    text=item["text"],
                    page=item.get("page")
                )
            )

        elif item["type"] == "image":
            content.append(
                create_node(
                    type="image",
                    src=item["src"],
                    page=item.get("page")
                )
            )

    return content
