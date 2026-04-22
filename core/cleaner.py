import re


def clean_flow(flow):
    cleaned = []
    buffer = []
    list_buffer = []

    for item in flow:
        if item["type"] != "paragraph":
            flush_buffer(buffer, cleaned)
            flush_list(list_buffer, cleaned)
            cleaned.append(item)
            continue

        text = normalize_text(item["text"])
        page = item.get("page")

        if is_noise(text, page):
            continue

        if is_list_item(text):
            list_buffer.append({
                "type": "list_item",
                "text": text,
                "page": page
            })
            continue
        else:
            flush_list(list_buffer, cleaned)

        # Merge broken paragraphs
        if buffer:
            if should_merge(buffer[-1], text):
                buffer[-1]["text"] += " " + text
            else:
                buffer.append(
                    {"type": "paragraph", "text": text, "page": page})
        else:
            buffer.append({"type": "paragraph", "text": text, "page": page})

    flush_buffer(buffer, cleaned)
    flush_list(list_buffer, cleaned)
    return cleaned


def flush_list(list_buffer, cleaned):
    if not list_buffer:
        return

    cleaned.append({
        "type": "list",
        "children": list_buffer.copy()
    })
    list_buffer.clear()


def flush_buffer(buffer, cleaned):
    for b in buffer:
        cleaned.append(b)
    buffer.clear()


def normalize_text(text):
    # Remove weird spacing like: L I V I N G
    text = re.sub(r"(?:\b[A-Z]\s+){3,}[A-Z]\b",
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

    return False


def is_list_item(text):
    words = text.split()

    if len(words) <= 6 and not any(p in text for p in ".!?"):
        return True

    return False


def should_merge(prev, current):
    if prev["text"].endswith((".", "!", "?")):
        return False

    if current[0].islower():
        return True

    return False
