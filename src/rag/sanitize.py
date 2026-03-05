"""Sanitize retrieved context by treating it as untrusted text."""

from __future__ import annotations

BLOCKED_PHRASES: tuple[str, ...] = (
    "ignore previous",
    "system prompt",
    "tool call",
    "developer message",
)


def sanitize_untrusted_text(text: str) -> str:
    """Remove suspicious prompt-injection lines from untrusted retrieved text."""
    safe_lines: list[str] = []
    for line in text.splitlines():
        lowered_line = line.lower()
        if any(needle in lowered_line for needle in BLOCKED_PHRASES):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines)
