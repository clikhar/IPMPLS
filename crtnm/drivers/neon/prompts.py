"""Prompt recognition and pagination handling for NEON CLI."""
import re

PROMPT_PATTERN = re.compile(r"(?m)^(?P<hostname>[\w.-]+)(?P<mode>\(config(?:-[\w/]+)?\))?[>#]\s*$")
PAGINATION_MARKERS = ("--More--", "More:")
CONFIRMATION_PATTERN = re.compile(r"(are you sure|\[y/n\]|\(y/n\))", re.IGNORECASE)


def find_prompt(text: str) -> str | None:
    """Return the final recognized NEON prompt from terminal output."""
    matches = list(PROMPT_PATTERN.finditer(text.replace("\r", "")))
    return matches[-1].group(0).strip() if matches else None


def contains_confirmation(text: str) -> bool:
    """Identify a potentially destructive interactive confirmation."""
    return bool(CONFIRMATION_PATTERN.search(text))

