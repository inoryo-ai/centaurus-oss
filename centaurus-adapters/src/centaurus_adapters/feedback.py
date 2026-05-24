"""FeedbackAdapter — 👍👎 / star ratings → learning data store.

Cross-business uses:
- Centaurus Adapters: chat reply usefulness (thumb up/down)
- downstream product feedback
- downstream product: transcription quality rating
- downstream product: meal recommendation rating

Storage: Supabase by default. Pluggable via persistence_writer callable.
ENV_FLAG: CTR_FEEDBACK_ENABLED
"""
from __future__ import annotations

from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class FeedbackAdapter(AdapterBase):
    NAME = 'feedback'
    ENV_FLAG = 'CTR_FEEDBACK_ENABLED'

    VALID_RATINGS = {'up', 'down', 1, 2, 3, 4, 5}

    def __init__(self,
                 persistence_writer: Callable[[dict], Any] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._writer = persistence_writer

    def _ops(self) -> list[str]:
        return ['submit', 'aggregate']

    def submit(self, *, target_id: str, target_kind: str,
               rating: str | int, user_id: str | None = None,
               context: dict | None = None) -> AdapterCallResult:
        """Record a single feedback event.

        target_kind: e.g. 'chat_reply', 'suggestion', 'lesson'
        rating: 'up'/'down' or 1-5 int
        context: free-form metadata (intent, source_book, etc.)
        """
        if rating not in self.VALID_RATINGS:
            return AdapterCallResult(
                ok=False, adapter=self.NAME, op='submit',
                latency_ms=0.0,
                error=f'invalid rating: {rating!r}')

        payload = {
            'target_id': target_id,
            'target_kind': target_kind,
            'rating': rating,
            'user_id': user_id,
            'context': context or {},
        }

        def go():
            if self._writer is None:
                raise RuntimeError('persistence_writer not configured')
            return self._writer(payload)

        return self._call('submit', go, payload=payload)

    def aggregate(self, *, target_kind: str, since_iso: str | None = None,
                  reader: Callable[[dict], Any] | None = None) -> AdapterCallResult:
        """Aggregate feedback by target_kind. Reader is injected to avoid
        coupling to a specific persistence layer."""
        payload = {'target_kind': target_kind, 'since_iso': since_iso}

        def go():
            if reader is None:
                raise RuntimeError('reader callable required')
            return reader(payload)

        return self._call('aggregate', go, payload=payload)
