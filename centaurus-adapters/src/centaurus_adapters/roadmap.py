"""RoadmapAdapter — career roadmap progression.

Activates when section→lesson ordering API becomes available.
Until then, falls back to category-hierarchy inference.

ENV_FLAG: CTR_ROADMAP_ENABLED
Cross-business: any product with a learning/onboarding journey.
"""
from __future__ import annotations

from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class RoadmapAdapter(AdapterBase):
    NAME = 'roadmap'
    ENV_FLAG = 'CTR_ROADMAP_ENABLED'

    def __init__(self,
                 ordering_provider: Callable[[str], list[dict]] | None = None,
                 fallback_provider: Callable[[str], list[dict]] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._ordering = ordering_provider
        self._fallback = fallback_provider

    def _ops(self) -> list[str]:
        return ['next_sections', 'progress_summary']

    def next_sections(self, *, job_key: str, completed_lesson_ids: list[str],
                      limit: int = 5) -> AdapterCallResult:
        """Return next-recommended sections for a learner.

        Uses ordering_provider when enabled (precise),
        else fallback_provider (category-inference).
        """
        payload = {'job_key': job_key,
                   'completed_count': len(completed_lesson_ids),
                   'limit': limit}

        def go():
            if self.enabled and self._ordering:
                return self._ordering(job_key)[:limit]
            if self._fallback is None:
                raise RuntimeError('fallback_provider required when disabled')
            return self._fallback(job_key)[:limit]

        if not self.enabled:
            # Manually call fallback even when disabled — this adapter's
            # fallback is a v1 deliverable, not a no-op.
            try:
                if self._fallback is None:
                    raise RuntimeError('fallback_provider required')
                data = self._fallback(job_key)[:limit]
                return AdapterCallResult(
                    ok=True, adapter=self.NAME, op='next_sections',
                    latency_ms=0.0, data=data,
                    meta={'mode': 'fallback'})
            except Exception as e:
                return AdapterCallResult(
                    ok=False, adapter=self.NAME, op='next_sections',
                    latency_ms=0.0, error=str(e))

        return self._call('next_sections', go, payload=payload)

    def progress_summary(self, *, user_id: str,
                         summary_provider: Callable[[str], dict] | None = None,
                         ) -> AdapterCallResult:
        payload = {'user_id': user_id}

        def go():
            if summary_provider is None:
                raise RuntimeError('summary_provider required')
            return summary_provider(user_id)

        return self._call('progress_summary', go, payload=payload)
