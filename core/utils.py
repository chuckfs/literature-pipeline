def clean_text(text: str) -> str:
    if not text:
        return ""
    return text.strip()


def is_noise(text: str) -> bool:
    if not text:
        return True

    text = text.strip()

    if len(text) < 2:
        return True

    if text.isdigit():
        return True

    return False
