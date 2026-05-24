"""QuizAdapter — LMS quiz integration.

Activates when ACF "Show in REST API" is enabled on your WordPress site
(or any compatible WordPress quiz plugin).

ENV_FLAG: CTR_QUIZ_ENABLED
Expected env (when enabled):
  CTR_QUIZ_API_BASE   — e.g. https://example.com/wp-json/wp/v2/quiz
  CTR_QUIZ_API_KEY    — bearer token (optional)

Cross-business: any LMS-style product needing quiz→remediation suggestion.
"""
from __future__ import annotations

import os
from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class QuizAdapter(AdapterBase):
    NAME = 'quiz'
    ENV_FLAG = 'CTR_QUIZ_ENABLED'

    def __init__(self,
                 fetcher: Callable[[str], Any] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._fetcher = fetcher

    def _ops(self) -> list[str]:
        return ['fetch_quiz', 'suggest_remediation']

    @property
    def api_base(self) -> str:
        return os.environ.get('CTR_QUIZ_API_BASE', '').strip()

    def fetch_quiz(self, quiz_id: str) -> AdapterCallResult:
        """Fetch quiz body (currently blocked by ACF; returns stub when not enabled)."""
        payload = {'quiz_id': quiz_id, 'api_base': self.api_base}

        def go():
            if self._fetcher is not None:
                return self._fetcher(quiz_id)
            if not self.api_base:
                raise RuntimeError('CTR_QUIZ_API_BASE not configured')
            import urllib.request
            url = f'{self.api_base.rstrip("/")}/{quiz_id}'
            req = urllib.request.Request(url)
            key = os.environ.get('CTR_QUIZ_API_KEY', '').strip()
            if key:
                req.add_header('Authorization', f'Bearer {key}')
            with urllib.request.urlopen(req, timeout=5) as resp:
                import json
                return json.loads(resp.read().decode('utf-8'))

        return self._call('fetch_quiz', go, payload=payload)

    def suggest_remediation(self, *, wrong_quiz_ids: list[str],
                            lesson_lookup: Callable[[str], list] | None = None,
                            ) -> AdapterCallResult:
        """Map wrong quizzes → review-recommended lessons.

        v1 stub: returns category-based suggestion via lesson_lookup.
        v2 (when ACF enabled): full quiz-content → topic-tagged remediation.
        """
        payload = {'wrong_quiz_ids': wrong_quiz_ids}

        def go():
            if lesson_lookup is None:
                raise RuntimeError('lesson_lookup required')
            results = []
            for qid in wrong_quiz_ids:
                lessons = lesson_lookup(qid)
                results.append({'quiz_id': qid, 'recommended_lessons': lessons})
            return results

        return self._call('suggest_remediation', go, payload=payload)
