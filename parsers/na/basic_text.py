from core.schema import create_node


def parse(flow: list) -> list:
    chapters = []
    current_chapter = None

    awaiting_chapter_title = False
    book_two_mode = False

    def close_chapter():
        if current_chapter and len(current_chapter["children"]) > 0:
            chapters.append(current_chapter)

    for item in flow:
        if item["type"] not in ["heading", "paragraph", "image"]:
            continue

        page_num = item.get("page")

        if item["type"] == "image":
            if current_chapter:
                current_chapter["children"].append(
                    create_node("image", src=item["src"], page=page_num))
            continue

        raw_text = item.get("text", "")

        # FIX: Nuke the OCR kerning nightmares before doing logic checks
        raw_text = raw_text.replace("O U R   S Y M B O L", "OUR SYMBOL")
        raw_text = raw_text.replace("O U R S Y M B O L", "OUR SYMBOL")
        raw_text = raw_text.replace("O URS YMBOL", "OUR SYMBOL")
        raw_text = raw_text.replace("O Urs Ymbol", "OUR SYMBOL")

        clean_text = raw_text.replace(
            "**", "").replace("*", "").replace("_", "").strip()
        upper_clean = clean_text.upper()

        # Trigger: Book Two Transition
        if upper_clean in ["BOOK TWO", "BOOK TWO: PERSONAL STORIES", "PERSONAL STORIES"]:
            close_chapter()
            current_chapter = create_node(
                "chapter", title="Book Two: Personal Stories")
            book_two_mode = True
            continue

        # Trigger: Standard Chapters
        if upper_clean.startswith("CHAPTER "):
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            awaiting_chapter_title = True
            continue

        # Trigger: Front Matter
        if upper_clean in ["OUR SYMBOL", "PREFACE", "INTRODUCTION"]:
            close_chapter()
            current_chapter = create_node("chapter", title=clean_text.title())
            continue

        # Trigger: Book Two Stories
        if book_two_mode and item["type"] == "heading" and len(clean_text) > 3:
            if not upper_clean.startswith(("STEP ", "TRADITION ")):
                close_chapter()
                current_chapter = create_node(
                    "chapter", title=clean_text.title())
                continue

        # Catch-all
        if not current_chapter:
            current_chapter = create_node(
                "chapter", title="Title Page & Copyright")

        # Merge 2-part chapter titles
        if awaiting_chapter_title and item["type"] in ["heading", "paragraph"]:
            current_chapter["title"] = f"{current_chapter['title']}: {clean_text.title()}"
            current_chapter["children"].append(
                create_node("heading", text=raw_text, page=page_num))
            awaiting_chapter_title = False
            continue

        # Body Text
        if len(clean_text) > 2:
            node_type = "heading" if item["type"] == "heading" else "paragraph"
            current_chapter["children"].append(
                create_node(node_type, text=raw_text, page=page_num))

    close_chapter()
    return chapters
