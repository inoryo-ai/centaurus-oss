# centaurus-adapters

[![PyPI](https://img.shields.io/pypi/v/centaurus-adapters.svg)](https://pypi.org/project/centaurus-adapters/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pluggable external-service adapter framework for Python applications.
Designed for cross-project reuse across LMS / WordPress / GA4 / Slack / SNS integrations.

## Why

Building AI products that integrate with WordPress, GA4, LMSs, Slack, etc.
quickly leads to the same pattern:

- An external service may or may not be available yet (auth, API rollout, contract phase).
- Each integration needs the same plumbing: env-flag gating, dry-run, structured logging, error capture.

`centaurus-adapters` gives you a tiny ABC + registry that handles all of that.
Each adapter is **off by default**, becomes a no-op when disabled, and
captures structured call logs (`latency_ms`, `payload_size`, `ok`, `error`).

## Install

```bash
pip install centaurus-adapters
# Optional: GA4 support
pip install "centaurus-adapters[ga4]"
```

## Quick start

```python
from centaurus_adapters import FeedbackAdapter

# Disabled by default — all calls become safe no-ops.
fb = FeedbackAdapter()
result = fb.submit(target_id="msg-1", target_kind="chat_reply", rating="up")
assert result.ok and result.meta["reason"] == "disabled"

# Enable via env var or force_enabled
import os
os.environ["CTR_FEEDBACK_ENABLED"] = "1"

fb = FeedbackAdapter(persistence_writer=lambda payload: db.insert(payload))
fb.submit(target_id="msg-1", target_kind="chat_reply", rating="up")
# → AdapterCallResult(ok=True, latency_ms=12.3, ...)
```

## Adapters included

| Adapter | Env flag | Use case |
|---|---|---|
| `FeedbackAdapter` | `CTR_FEEDBACK_ENABLED` | 👍👎 / star ratings |
| `QuizAdapter` | `CTR_QUIZ_ENABLED` | LMS quiz / WordPress ACF |
| `RoadmapAdapter` | `CTR_ROADMAP_ENABLED` | Learning path progression |
| `GA4Adapter` | `CTR_GA4_ENABLED` | Google Analytics behavior signals |
| `WPUserAdapter` | `CTR_WPUSER_ENABLED` | WordPress user identity bridge |
| `NotifyAdapter` | `CTR_NOTIFY_ENABLED` | email / Slack / LINE Notify |
| `SNSPublishAdapter` | `CTR_SNS_ENABLED` | X / Threads / note / Instagram |

## Design principles

1. **Off by default.** Disabled adapters return no-op success.
2. **Dry-run support.** All adapters accept `dry_run=True` for side-effect-free verification.
3. **Structured logging.** Every call emits a JSON log line.
4. **Errors captured, not raised.** Caller decides how to handle.
5. **Project-agnostic.** No business logic in base.

## Build your own

```python
from centaurus_adapters import AdapterBase

class WebhookAdapter(AdapterBase):
    NAME = "webhook"
    ENV_FLAG = "CTR_WEBHOOK_ENABLED"

    def _ops(self):
        return ["post"]

    def post(self, *, url: str, payload: dict):
        return self._call("post", lambda: self._do_post(url, payload),
                          payload=payload)

    def _do_post(self, url, payload):
        import requests
        return requests.post(url, json=payload, timeout=5).json()
```

## Registry

```python
from centaurus_adapters import AdapterRegistry, FeedbackAdapter, NotifyAdapter

reg = AdapterRegistry()
reg.register(FeedbackAdapter())
reg.register(NotifyAdapter())

reg.health_all()
# [
#   {'name': 'feedback', 'enabled': False, 'env_flag': 'CTR_FEEDBACK_ENABLED', 'ops': [...]},
#   ...
# ]
```

## License

MIT — see [LICENSE](LICENSE).

## Author

[Centaurus Inc.](https://centaurus.example.com) — AI development house specializing in
LLM-free cognitive engines and human+AI collaborative products.
