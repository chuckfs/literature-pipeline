import re


def clean_flow(flow):
    cleaned = []
    buffer = []

    for item in flow:
        if item["type"] != "paragraph":
            flush_buffer(buffer, cleaned)
            cleaned.append(item)
            continue

        text = normalize_text(item["text"])

        if is_noise(text):
            continue

        if is_list_item(text):
            cleaned.append({
                "type": "list_item",
                "text": text,
                "page": item["page"]
            })
            continue

        # Merge broken paragraphs
        if buffer:
            if should_merge(buffer[-1], text):
                buffer[-1]["text"] += " " + text
            else:
                buffer.append(
                    {"type": "paragraph", "text": text, "page": item["page"]})
        else:
            buffer.append(
                {"type": "paragraph", "text": text, "page": item["page"]})

    flush_buffer(buffer, cleaned)
    return cleaned


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


def is_noise(text):
    if len(text) < 3:
        return True

    if re.match(r"^[^a-zA-Z]+$", text):
        return True

    if re.match(r"^[A-Z0-9\-]+$", text) and len(text) < 6:
        return True

    return False


def is_list_item(text):
    # short lines, no punctuation → likely list
    if len(text) < 80 and not re.search(r"[.!?]", text):
        return True
    return False


def should_merge(prev, current):
    if prev["text"].endswith((".", "!", "?")):
        return False

    if current[0].islower():
        return True

    return False
