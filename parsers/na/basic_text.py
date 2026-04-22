from core.schema import create_node

def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for the Basic Text.
    """
    chapters = []
    current_chapter = None
    
    # State flags
    awaiting_chapter_title = False
    book_two_mode = False

    def close_chapter():
        """Helper to save the current chapter before starting a new one."""
        if current_chapter and len(current_chapter["children"]) > 0:
            chapters.append(current_chapter)

    for item in flow:
        if item["type"] not in ["heading", "paragraph", "image"]:
            continue

        raw_text = item.get("text", "")
        clean_text = raw_text.replace("**", "").replace("*", "").replace("_", "").strip()
        upper_clean = clean_text.upper()
        page_num = item.get("page")

        # 1. Handle Images
        if item["type"] == "image":
            if current_chapter:
                current_chapter["children"].append(create_node("image", src=item["src"], page=page_num))
            continue

        # 2. Trigger: Book Two Transition
        if upper_clean in ["BOOK TWO", "BOOK TWO: PERSONAL STORIES", "PERSONAL STORIES"]:
            close_chapter()
            current_chapter = create_node("chapter", title="Book Two: Personal Stories")
            book_two_mode = True
            continue

        # 3. Trigger: Standard Chapters (e.g., "CHAPTER ONE")
        if upper_clean.startswith("CHAPTER "):
            close_chapter()
            # Initialize with the number (e.g., "Chapter One")
            current_chapter = create_node("chapter", title=clean_text.title())
            awaiting_chapter_title = True
            continue

        # 4. Trigger: Front Matter
        if upper_clean in ["OUR SYMBOL", "PREFACE", "INTRODUCTION"]:
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            continue

        # 5. Trigger: Book Two Stories
        # In Book Two, stories don't say "Chapter". We rely on Docling identifying a "heading"
        if book_two_mode and item["type"] == "heading" and len(clean_text) > 3:
            # Prevent false positives if a story contains a subhead like "Step One"
            if not upper_clean.startswith(("STEP ", "TRADITION ")):
                close_chapter()
                current_chapter = create_node("chapter", title=clean_text.title())
                continue

        # 6. Catch-all for Front-Matter (Title page, copyrights) before "Our Symbol"
        if not current_chapter:
            current_chapter = create_node("chapter", title="Title Page & Copyright")

        # 7. Merge two-part Chapter Titles
        # If the last block was "CHAPTER ONE", this block is "WHO IS AN ADDICT?"
        if awaiting_chapter_title and item["type"] in ["heading", "paragraph"]:
            # Append the real title to the chapter node
            current_chapter["title"] = f"{current_chapter['title']}: {clean_text.title()}"
            
            # Also add it as a rendered heading inside the chapter body
            title_node = create_node("heading", text=raw_text, page=page_num)
            current_chapter["children"].append(title_node)
            
            awaiting_chapter_title = False
            continue

        # 8. Build the Body Text
        if len(clean_text) > 2:  # Filter out tiny OCR artifacts
            # We preserve Docling's distinction between paragraphs and inner sub-headings
            node_type = "heading" if item["type"] == "heading" else "paragraph"
            body_node = create_node(node_type, text=raw_text, page=page_num)
            current_chapter["children"].append(body_node)

    # Push the final chapter when the loop ends
    close_chapter()

    return chapters
