"""Security utilities — input sanitization, PII masking, rate limiting, headers.

All modules are framework-agnostic where possible. FastAPI-specific bits
live in middleware factories.
"""
from .sanitize import sanitize_user_input, SanitizationResult
from .pii import mask_pii, PIIPattern, DEFAULT_PII_PATTERNS
from .ratelimit import RateLimiter, RateLimitExceeded
from .headers import build_security_headers

__all__ = [
    'sanitize_user_input',
    'SanitizationResult',
    'mask_pii',
    'PIIPattern',
    'DEFAULT_PII_PATTERNS',
    'RateLimiter',
    'RateLimitExceeded',
    'build_security_headers',
]
