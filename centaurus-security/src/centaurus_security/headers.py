"""Security headers (CSP, X-Frame-Options, HSTS, Referrer-Policy, etc.)."""
from __future__ import annotations


def build_security_headers(
    *,
    embedded_in_origin: str | None = None,
    allow_inline_script: bool = True,
) -> dict[str, str]:
    """Return a dict of security headers suitable for FastAPI middleware.

    embedded_in_origin: when the chat widget is embedded in an iframe on
        the parent site (e.g. https://example.com), pass that origin
        so X-Frame-Options/frame-ancestors is set correctly.
    allow_inline_script: kept on for v1 (widget uses inline init). Move to
        nonce-based CSP after v1 stabilizes.
    """
    csp_parts = [
        "default-src 'self'",
        "img-src 'self' data: https:",
        "style-src 'self' 'unsafe-inline'",
        ("script-src 'self' 'unsafe-inline'" if allow_inline_script
         else "script-src 'self'"),
        "connect-src 'self' https://api.openai.com https://*.supabase.co",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    if embedded_in_origin:
        csp_parts.append(f"frame-ancestors 'self' {embedded_in_origin}")
    else:
        csp_parts.append("frame-ancestors 'self'")

    headers = {
        'Content-Security-Policy': '; '.join(csp_parts),
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': (
            'geolocation=(), microphone=(), camera=(), payment=()'),
        'Strict-Transport-Security':
            'max-age=31536000; includeSubDomains',
    }
    return headers
