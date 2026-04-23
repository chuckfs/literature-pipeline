from core.schema import create_node


def parse(flow: list) -> list:
    entries = []
    current_entry = None
    months = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December")

    for item in flow:
        if item["type"] not in ["heading", "paragraph", "image"]:
            continue

        page_num = item.get("page")

        # 1. Handle Images
        if item["type"] == "image":
            if current_entry:
                current_entry["children"].append(create_node(
                    "image", src=item["src"], page=page_num))
            continue

        # 2. FIX: Docling smashed the text together. We MUST split it by newlines!
        lines = item.get("text", "").split('\n')

        for raw_text in lines:
            clean_text = raw_text.replace(
                "**", "").replace("*", "").replace("_", "").strip()
            if not clean_text:
                continue

            # Detect Date
            if any(clean_text.startswith(m) for m in months) and len(clean_text.split()) <= 4:
                if current_entry:
                    _clean_temp_meta(current_entry)
                    entries.append(current_entry)
                current_entry = create_node("entry", title=clean_text, meta={
                                            "has_quote": False, "has_title": False})
                continue

            if not current_entry:
                continue

            # Detect Title
            if not current_entry["meta"]["has_title"] and len(clean_text) > 2:
                current_entry["children"].append(create_node(
                    "heading", text=raw_text, page=page_num))
                current_entry["meta"]["has_title"] = True
                continue

            # Detect Quote
            if not current_entry["meta"]["has_quote"] and len(clean_text) > 5:
                current_entry["children"].append(
                    create_node("quote", text=raw_text, page=page_num))
                current_entry["meta"]["has_quote"] = True
                continue

            # Detect Affirmation
            if clean_text.lower().startswith("just for today:"):
                current_entry["children"].append(create_node(
                    "affirmation", text=raw_text, page=page_num))
                continue

            # Body Reflection
            if len(clean_text) > 3:
                current_entry["children"].append(create_node(
                    "paragraph", text=raw_text, page=page_num))

    if current_entry:
        _clean_temp_meta(current_entry)
        entries.append(current_entry)

    return entries


def _clean_temp_meta(entry_node):
    entry_node["meta"].pop("has_quote", None)
    entry_node["meta"].pop("has_title", None)
