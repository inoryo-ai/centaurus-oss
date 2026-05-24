"""SNSPublishAdapter — chat log → SNS post draft generator.

Phase 2 feature for Centaurus Adapters. dry_run by default.
ENV_FLAG: CTR_SNS_ENABLED

Channels (each independently activated):
  x       → CTR_X_BEARER_TOKEN
  threads → CTR_THREADS_TOKEN
  note    → CTR_NOTE_TOKEN
  instagram → CTR_IG_TOKEN

Cross-business: any product wanting AI-driven content publishing.
"""
from __future__ import annotations

import os
from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class SNSPublishAdapter(AdapterBase):
    NAME = 'sns'
    ENV_FLAG = 'CTR_SNS_ENABLED'

    SUPPORTED = ('x', 'threads', 'note', 'instagram')

    MAX_LEN = {
        'x': 280,
        'threads': 500,
        'note': 50000,
        'instagram': 2200,
    }

    def __init__(self,
                 publisher_overrides: dict[str, Callable[[str], Any]] | None = None,
                 *, dry_run: bool = True,  # default safe
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._overrides = publisher_overrides or {}

    def _ops(self) -> list[str]:
        return ['draft_from_chat', 'publish']

    def draft_from_chat(self, *, chat_excerpts: list[dict],
                        channel: str,
                        formatter: Callable[[list[dict], str, int], str] | None = None,
                        ) -> AdapterCallResult:
        """Generate a post draft from chat log excerpts.

        chat_excerpts: list of {role, content, intent} dicts.
        formatter: pluggable LLM-based formatter; default is naive concat.
        """
        if channel not in self.SUPPORTED:
            return AdapterCallResult(
                ok=False, adapter=self.NAME, op='draft_from_chat',
                latency_ms=0.0,
                error=f'unsupported channel: {channel}')
        max_len = self.MAX_LEN[channel]
        payload = {'channel': channel, 'excerpts': len(chat_excerpts),
                   'max_len': max_len}

        def go():
            if formatter is not None:
                return formatter(chat_excerpts, channel, max_len)
            # Naive default: take last assistant content, trimmed.
            for ex in reversed(chat_excerpts):
                if ex.get('role') == 'assistant':
                    return (ex.get('content') or '')[:max_len]
            return ''

        return self._call('draft_from_chat', go, payload=payload)

    def publish(self, *, channel: str, body: str) -> AdapterCallResult:
        """Publish to channel. Defaults to dry_run; flip dry_run=False to push."""
        if channel not in self.SUPPORTED:
            return AdapterCallResult(
                ok=False, adapter=self.NAME, op='publish', latency_ms=0.0,
                error=f'unsupported channel: {channel}')
        payload = {'channel': channel, 'body_len': len(body)}

        def go():
            fn = self._overrides.get(channel)
            if fn is None:
                raise RuntimeError(
                    f'publisher for "{channel}" not registered '
                    '(use publisher_overrides in __init__)')
            return fn(body)

        return self._call('publish', go, payload=payload)
