from pathlib import Path

from docling_core.types.doc.document import TableItem
from docling_core.types.doc.labels import DocItemLabel

from core.reading_quality import normalize_reader_heading


def build_flow(doc, image_dir: Path):
    """
    Converts a Docling document into a flat, ordered flow of blocks.
    Includes text, tables / document index, and images in reading order.
    """

    flow = []
    image_dir.mkdir(parents=True, exist_ok=True)

    for i, (item, level) in enumerate(doc.iterate_items()):
        page = item.prov[0].page_no if item.prov else None

        # TEXT BLOCKS
        if hasattr(item, "text") and item.text:
            if hasattr(item, "export_to_markdown"):
                text = item.export_to_markdown().strip()
            else:
                text = item.text.strip()

            if not text:
                continue

            is_header = item.label in [
                DocItemLabel.TITLE,
                DocItemLabel.SECTION_HEADER,
                DocItemLabel.PAGE_HEADER,
            ]

            if is_header:
                text = normalize_reader_heading(text)

            node = {
                "type": "heading" if is_header else "paragraph",
                "text": text,
                "page": page,
            }
            lbl = getattr(item, "label", None)
            if lbl == DocItemLabel.CAPTION:
                node["flow_kind"] = "caption"
            elif lbl == DocItemLabel.FOOTNOTE:
                node["flow_kind"] = "footnote"
            flow.append(node)

        # TABLES & INDEX (Docling TableItem covers TABLE + DOCUMENT_INDEX)
        elif isinstance(item, TableItem):
            try:
                text = item.export_to_markdown().strip()
            except Exception as e:
                print(f"Table export failed: {e}")
                text = ""
            if not text:
                continue
            kind = (
                "document_index"
                if item.label == DocItemLabel.DOCUMENT_INDEX
                else "table"
            )
            flow.append(
                {
                    "type": "paragraph",
                    "text": text,
                    "page": page,
                    "flow_kind": kind,
                }
            )

        # IMAGE BLOCKS
        elif hasattr(item, "image") and item.image:
            filename = f"image_page{page}_{i}.png"
            path = image_dir / filename

            try:
                item.image.pil_image.save(path, "PNG")
            except Exception as e:
                print(f"Image save failed: {e}")
                continue

            flow.append(
                {
                    "type": "image",
                    "src": str(path),
                    "page": page,
                }
            )

    return flow
