from pathlib import Path
from docling_core.types.doc.labels import DocItemLabel


def build_flow(doc, image_dir: Path):
    """
    Converts a Docling document into a flat, ordered flow of blocks.
    Includes text + images in correct reading order.
    """

    flow = []
    image_dir.mkdir(parents=True, exist_ok=True)

    for i, (item, level) in enumerate(doc.iterate_items()):
        page = item.prov[0].page_no if item.prov else None

        # TEXT BLOCKS
        if hasattr(item, "text") and item.text:
            text = item.export_to_markdown().strip()

            if not text:
                continue

            is_header = item.label in [
                DocItemLabel.TITLE,
                DocItemLabel.SECTION_HEADER,
                DocItemLabel.PAGE_HEADER
            ]

            flow.append({
                "type": "heading" if is_header else "paragraph",
                "text": text,
                "page": page
            })

        # IMAGE BLOCKS
        elif hasattr(item, "image") and item.image:
            filename = f"image_page{page}_{i}.png"
            path = image_dir / filename

            try:
                item.image.pil_image.save(path, "PNG")
            except Exception as e:
                print(f"Image save failed: {e}")
                continue

            flow.append({
                "type": "image",
                "src": str(path),
                "page": page
            })

    return flow
