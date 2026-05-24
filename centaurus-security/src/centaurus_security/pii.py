"""PII masking — detect & redact personal info before logging.

Patterns covered (ja-JP focus):
  - email
  - jp phone numbers (mobile + fixed line)
  - credit-card-like 13-19 digit sequences
  - 7-digit jp postal code
  - my-number-ish 12-digit sequences (best-effort)

NOT covered (intentionally): full names, free-text addresses.
Reason: false-positive rate too high; route through paid PII service if
this becomes a hard requirement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PIIPattern:
    name: str
    pattern: re.Pattern
    placeholder: str


DEFAULT_PII_PATTERNS: list[PIIPattern] = [
    PIIPattern('email',
               re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
               '[EMAIL]'),
    PIIPattern('jp_phone_mobile',
               re.compile(r'(?:(?:\+81|0)\s?[7-9]0[-\s]?\d{4}[-\s]?\d{4})'),
               '[PHONE]'),
    PIIPattern('jp_phone_fixed',
               re.compile(r'\b0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}\b'),
               '[PHONE]'),
    PIIPattern('credit_card',
               re.compile(r'\b(?:\d[ -]?){13,19}\b'),
               '[CARD]'),
    PIIPattern('jp_postal',
               re.compile(r'\b\d{3}-\d{4}\b'),
               '[POSTAL]'),
    PIIPattern('my_number_like',
               re.compile(r'\b\d{12}\b'),
               '[MYNUMBER?]'),
]


def mask_pii(text: str,
             patterns: list[PIIPattern] | None = None,
             ) -> tuple[str, dict[str, int]]:
    """Replace matched PII with placeholders.

    Returns (masked_text, counts_by_pattern).
    Order matters: email & phone are checked before generic digit runs.
    """
    if not isinstance(text, str) or not text:
        return text, {}

    pats = patterns if patterns is not None else DEFAULT_PII_PATTERNS
    counts: dict[str, int] = {}

    for p in pats:
        def repl(m, _p=p):
            counts[_p.name] = counts.get(_p.name, 0) + 1
            return _p.placeholder
        text = p.pattern.sub(repl, text)

    return text, counts
