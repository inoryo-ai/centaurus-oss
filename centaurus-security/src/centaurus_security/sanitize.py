"""Input sanitization for user-facing chat / form inputs.

Detects:
  - HTML/script tags
  - Prompt injection markers ("ignore previous instructions", "system prompt", etc.)
  - Excessive length (default 2000 chars; configurable)
  - Control characters
  - Excessive newlines (DoS via huge prompts)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


HTML_TAG = re.compile(r'<[^>]{1,200}>')
CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
EXCESSIVE_NEWLINES = re.compile(r'\n{4,}')

PROMPT_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'disregard\s+(all\s+)?previous',
        r'system\s+prompt',
        r'###\s*system',
        r'\[\[\s*system\s*\]\]',
        r'前の指示を無視',
        r'これまでの指示を忘れて',
        r'システムプロンプト',
    )
]


@dataclass
class SanitizationResult:
    text: str
    original_length: int
    flags: list[str]
    truncated: bool

    @property
    def is_clean(self) -> bool:
        return not self.flags and not self.truncated


def sanitize_user_input(text: str, *, max_length: int = 2000) -> SanitizationResult:
    """Clean user input. Returns sanitized text + audit flags.

    Strategy: clean what's safe to clean (HTML, control chars), flag the
    rest (prompt injection) so the caller can decide how to handle.
    """
    if not isinstance(text, str):
        text = str(text)

    flags: list[str] = []
    original_len = len(text)

    truncated = original_len > max_length
    if truncated:
        text = text[:max_length]
        flags.append('truncated')

    if HTML_TAG.search(text):
        flags.append('html_stripped')
        text = HTML_TAG.sub('', text)

    if CONTROL_CHARS.search(text):
        flags.append('control_chars_removed')
        text = CONTROL_CHARS.sub('', text)

    if EXCESSIVE_NEWLINES.search(text):
        flags.append('newlines_collapsed')
        text = EXCESSIVE_NEWLINES.sub('\n\n\n', text)

    for pat in PROMPT_INJECTION_PATTERNS:
        if pat.search(text):
            flags.append('prompt_injection_suspected')
            break

    text = text.strip()

    return SanitizationResult(
        text=text,
        original_length=original_len,
        flags=flags,
        truncated=truncated,
    )
