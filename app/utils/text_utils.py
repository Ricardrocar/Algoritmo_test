def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    return text.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

