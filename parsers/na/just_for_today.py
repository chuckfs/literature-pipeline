from core.schema import create_node

def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for Just For Today.
    """
    entries = []
    current_entry = None

    # The trigger words that signal a new page/entry in JFT
    months = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    )

    for item in flow:
        # 1. Skip pure noise (Docling sometimes catches tiny artifacts or page numbers)
        if item["type"] not in ["heading", "paragraph", "image"]:
            continue

        raw_text = item.get("text", "")
        # Create a clean version of the text just for our logic checks 
        # (removes markdown bold/italics so we can easily check "startswith")
        clean_text = raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        page_num = item.get("page")

        # 2. Detect Date -> Initialize New Entry Node
        # We check if it starts with a month and is short (e.g., "January 1")
        if clean_text.split()[0] in months and len(clean_text.split()) <= 4:
            if current_entry:
                # Save the previous day before starting a new one
                _clean_temp_meta(current_entry)
                entries.append(current_entry)
            
            # Open a new entry container
            current_entry = create_node(
                type="entry",
                title=clean_text, 
                meta={"has_quote": False, "has_title": False} # Temp trackers
            )
            continue

        # If we haven't found our first date yet (like the intro pages), skip the text
        if not current_entry:
            continue

        # 3. Handle Images (if Docling caught any graphics on the page)
        if item["type"] == "image":
            img_node = create_node(type="image", src=item["src"], page=page_num)
            current_entry["children"].append(img_node)
            continue

        # 4. Detect Title (The very first short text block after the date)
        if (
            not current_entry["meta"]["has_title"]
            and len(clean_text.split()) <= 6
            and not clean_text.endswith(".")
        ):
            title_node = create_node(type="heading", text=raw_text, page=page_num)
            current_entry["children"].append(title_node)
            current_entry["meta"]["has_title"] = True
            continue

        # 5. Detect Quote (Typically italicized or shorter intro text)
        if (
            not current_entry["meta"]["has_quote"]
            and (raw_text.startswith("*") or len(clean_text.split()) < 25)
        ):
            quote_node = create_node(
                type="quote",
                text=raw_text,
                page=page_num
            )
            current_entry["children"].append(quote_node)
            current_entry["meta"]["has_quote"] = True
            continue

        # 6. Detect Affirmation (Always starts with "Just for today:")
        if clean_text.lower().startswith("just for today:"):
            aff_node = create_node(type="affirmation", text=raw_text, page=page_num)
            current_entry["children"].append(aff_node)
            current_entry["meta"]["done"] = True
            continue

        # 7. Build the Reflection Body
        # If it's not the title, quote, or affirmation, it's the main reading text.
        if len(clean_text) > 3:
            para_node = create_node(type="paragraph", text=raw_text, page=page_num)
            current_entry["children"].append(para_node)

    # Push the final entry (December 31st) when the loop ends
    if current_entry:
        _clean_temp_meta(current_entry)
        entries.append(current_entry)

    return entries

def _clean_temp_meta(entry_node):
    """Removes the temporary tracking variables from the final JSON."""
    entry_node["meta"].pop("has_quote", None)
    entry_node["meta"].pop("has_title", None)
