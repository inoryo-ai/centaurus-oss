# centaurus-oss

Cross-project Python utility packages extracted from production AI products.

| Package | Purpose |
|---|---|
| [`centaurus-adapters`](./centaurus-adapters) | Pluggable external-service adapter framework (Quiz / GA4 / WordPress / Slack / SNS, env-flag gated, dry-run safe) |
| [`centaurus-cache`](./centaurus-cache) | TTL in-memory response cache with size + idempotency keying |
| [`centaurus-security`](./centaurus-security) | FastAPI-oriented sanitization, PII redaction, rate limiting, and security-header helpers |

Each package is independently versioned and packaged with `pyproject.toml`.

## Why monorepo?

These three libraries co-evolved across several internal AI products and share testing/release tooling. Publishing them together avoids version-skew when used in combination.

## Status

Source published for review. PyPI release pending.

Note: This public mirror was exported after stripping internal references,
so the commit history is squashed. Each package keeps its own tests and
changelog, which carry the actual evolution.

## License

MIT — see each package's `LICENSE`.
