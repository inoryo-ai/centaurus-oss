# centaurus-security

[![PyPI](https://img.shields.io/pypi/v/centaurus-security.svg)](https://pypi.org/project/centaurus-security/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

FastAPI/Starlette security utilities, focused on Japanese-market PII patterns
and AI/LLM-app threat models.

## Features

- **`sanitize_user_input`** — strips HTML, control chars, excessive newlines, and flags prompt-injection patterns (English + Japanese).
- **`mask_pii`** — masks email, JP phone (mobile/fixed), credit card, JP postal, my-number-like sequences.
- **`RateLimiter`** — thread-safe token bucket per key.
- **`build_security_headers`** — CSP, HSTS, X-Frame-Options, Permissions-Policy preset for AI chat widgets.

## Install

```bash
pip install centaurus-security
```

## Quick start

```python
from centaurus_security import sanitize_user_input, mask_pii, RateLimiter, build_security_headers

# Sanitize user input
result = sanitize_user_input('<script>alert(1)</script>SEOについて')
# result.text = 'SEOについて', result.flags = ['html_stripped']

# Mask PII before logging
masked, counts = mask_pii('連絡先: taro@example.com, 090-1234-5678')
# masked = '連絡先: [EMAIL], [PHONE]', counts = {'email': 1, 'jp_phone_mobile': 1}

# Rate limit per user
rl = RateLimiter(capacity=10, refill_seconds=60)
try:
    rl.check(user_id)
except RateLimitExceeded as e:
    return 429, f'retry in {e.retry_after_sec}s'

# Security headers for FastAPI
headers = build_security_headers(embedded_in_origin='https://your-site.com')
@app.middleware('http')
async def add_headers(request, call_next):
    response = await call_next(request)
    for k, v in headers.items():
        response.headers.setdefault(k, v)
    return response
```

## Why use this

If you're building AI chat widgets / RAG apps in Python:
- Stock `slowapi` doesn't have JP-phone PII patterns
- Stock `python-multipart` doesn't flag prompt injection
- CSP defaults from frameworks aren't tuned for AI-chat embed scenarios

`centaurus-security` packages opinionated defaults that we use across our own
production AI products.

## License

MIT
