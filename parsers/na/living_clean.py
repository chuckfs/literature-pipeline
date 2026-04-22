from core.schema import create_node

def parse(flow: list) -> list:
    """
    Transforms a flat flow of Docling blocks into the nested Universal Schema for Living Clean.
    Builds a hierarchy of Chapter -> Section -> Paragraph.
    """
    chapters = []
    current_chapter = None
    current_section = None
    
    # State flag for 2-part chapter titles (e.g., "Chapter One" + "Keys to Freedom")
    awaiting_chapter_title = False

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
            img_node = create_node("image", src=item["src"], page=page_num)
            # Route image to the deepest active container
            if current_section:
                current_section["children"].append(img_node)
            elif current_chapter:
                current_chapter["children"].append(img_node)
            continue

        # 2. Trigger: New Chapter
        if upper_clean.startswith("CHAPTER "):
            close_chapter()
            # Initialize with the number (e.g., "Chapter One")
            current_chapter = create_node("chapter", title=clean_text.title())
            current_section = None # Reset the section state for the new chapter
            awaiting_chapter_title = True
            continue

        # Catch-all for Front-Matter (Title page, copyrights) before Chapter One
        if not current_chapter:
            current_chapter = create_node("chapter", title="Front Matter & Preface")

        # 3. Handle 2-part Chapter Titles
        if awaiting_chapter_title and item["type"] in ["heading", "paragraph"]:
            # Append the real title to the chapter node metadata
            current_chapter["title"] = f"{current_chapter['title']}: {clean_text.title()}"
            
            # Add it as a rendered heading inside the chapter body so the user sees it
            title_node = create_node("heading", text=raw_text, page=page_num)
            current_chapter["children"].append(title_node)
            
            awaiting_chapter_title = False
            continue

        # 4. Trigger: Sub-sections (Headings)
        # Docling identifies bold, standalone lines as "heading". 
        if item["type"] == "heading" and len(clean_text) > 3:
            # Create a new section bucket
            current_section = create_node("section", title=clean_text.title())
            
            # Attach this new section to the current chapter
            current_chapter["children"].append(current_section)
            
            # Also add the heading text visually inside the section
            heading_node = create_node("heading", text=raw_text, page=page_num)
            current_section["children"].append(heading_node)
            continue

        # 5. Build the Body Text
        if len(clean_text) > 2:  # Filter out tiny OCR noise
            para_node = create_node("paragraph", text=raw_text, page=page_num)
            
            # Routing logic: If we are inside a section, put the paragraph there.
            # If we haven't hit a section yet (e.g., chapter intro text), put it in the chapter.
            if current_section:
                current_section["children"].append(para_node)
            else:
                current_chapter["children"].append(para_node)

    # Push the final chapter when the loop ends
    close_chapter()

    return chapters
