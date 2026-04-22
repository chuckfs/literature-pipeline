import re


def clean_flow(flow, return_stats=False):
    cleaned = []
    buffer = []
    list_buffer = []

    stats = {
        "input_items": len(flow),
        "output_items": 0,
        "noise_removed": 0,
        "lists_created": 0,
        "list_items_created": 0,
        "paragraph_merges": 0
    }

    for item in flow:
        if item["type"] != "paragraph":
            flush_buffer(buffer, cleaned)
            flush_list(list_buffer, cleaned, stats)
            cleaned.append(item)
            continue

        text = normalize_text(item["text"])
        page = item.get("page")

        # HARD FILTER front matter (first 3 pages are junk for NA books)
        if page and page <= 3:
            continue
        if is_noise(text, page):
            stats["noise_removed"] += 1
            continue

        if is_list_item(text):
            items = split_inline_list(text)
            for t in items:
                list_buffer.append({
                    "type": "list_item",
                    "text": t,
                    "page": page
                })
                stats["list_items_created"] += 1
            continue
        else:
            flush_list(list_buffer, cleaned, stats)

        # Merge broken paragraphs
        if buffer:
            if should_merge(buffer[-1], text, buffer[-1].get("page"), page):
                buffer[-1]["text"] += " " + text
                stats["paragraph_merges"] += 1
            else:
                buffer.append(
                    {"type": "paragraph", "text": text, "page": page})
        else:
            buffer.append({"type": "paragraph", "text": text, "page": page})

    flush_buffer(buffer, cleaned)
    flush_list(list_buffer, cleaned, stats)
    stats["output_items"] = len(cleaned)
    if return_stats:
        return cleaned, stats
    return cleaned


def flush_list(list_buffer, cleaned, stats=None):
    if not list_buffer:
        return

    cleaned.append({
        "type": "list",
        "children": list_buffer.copy()
    })
    if stats is not None:
        stats["lists_created"] += 1
    list_buffer.clear()


def flush_buffer(buffer, cleaned):
    for b in buffer:
        cleaned.append(b)
    buffer.clear()


def normalize_text(text):
    # Remove weird spacing like: L I V I N G
    text = re.sub(r"(?:\b[A-Z]\s+){2,}[A-Z]\b",
                  lambda m: m.group(0).replace(" ", ""), text)

    # Fix spacing issues
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_noise(text, page=None):
    if len(text) < 3:
        return True

    if re.match(r"^[^a-zA-Z]+$", text):
        return True

    if re.match(r"^[A-Z0-9\-]+$", text) and len(text) < 6:
        return True

    # Aggressive filtering for early pages (front matter junk)
    if page and page <= 3 and len(text) < 25:
        return True

    lowered = text.lower()

    # Remove metadata / publishing noise
    if "www." in lowered:
        return True

    if "copyright" in lowered:
        return True

    if "catalog item" in lowered:
        return True

    if "world service office" in lowered:
        return True

    # Kill long weird OCR / multilingual junk
    if len(text.split()) > 12 and not text.islower():
        return True

    return False


def is_list_item(text):
    words = text.split()

    if len(words) <= 6 and not any(p in text for p in ".!?"):
        return True

    return False


def should_merge(prev, current, prev_page, current_page):
    # NEVER merge across pages (you want page accuracy)
    if prev_page != current_page:
        return False

    if prev["text"].endswith((".", "!", "?")):
        return False

    if current[0].islower():
        return True

    return False


def split_inline_list(text):
    parts = re.split(r'(?<!\\.)\\s+(?=[A-Z][a-z])', text)
    return [p.strip() for p in parts if len(p.strip()) > 2]
