"""GA4Adapter — Google Analytics 4 read-only integration.

Activates when GA4 share is granted.
ENV_FLAG: CTR_GA4_ENABLED
Required env (when enabled):
  CTR_GA4_PROPERTY_ID
  GOOGLE_APPLICATION_CREDENTIALS — service account JSON path

Cross-business: any web product wanting behavior signals → AI personalization.
"""
from __future__ import annotations

import os
from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class GA4Adapter(AdapterBase):
    NAME = 'ga4'
    ENV_FLAG = 'CTR_GA4_ENABLED'

    def __init__(self,
                 client_factory: Callable[[], Any] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._client_factory = client_factory
        self._client: Any | None = None

    def _ops(self) -> list[str]:
        return ['recent_pageviews', 'top_videos', 'user_session_summary']

    @property
    def property_id(self) -> str:
        return os.environ.get('CTR_GA4_PROPERTY_ID', '').strip()

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory()
            return self._client
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
        except ImportError as e:
            raise RuntimeError(
                'google-analytics-data not installed. '
                'pip install google-analytics-data') from e
        self._client = BetaAnalyticsDataClient()
        return self._client

    def recent_pageviews(self, *, days: int = 7,
                         page_path_prefix: str | None = None,
                         ) -> AdapterCallResult:
        payload = {'days': days, 'prefix': page_path_prefix,
                   'property_id': self.property_id}

        def go():
            from google.analytics.data_v1beta.types import (
                DateRange, Dimension, Metric, RunReportRequest, FilterExpression,
                Filter,
            )
            client = self._get_client()
            req_args = dict(
                property=f'properties/{self.property_id}',
                dimensions=[Dimension(name='pagePath')],
                metrics=[Metric(name='screenPageViews')],
                date_ranges=[DateRange(start_date=f'{days}daysAgo',
                                       end_date='today')],
                limit=50,
            )
            if page_path_prefix:
                req_args['dimension_filter'] = FilterExpression(
                    filter=Filter(field_name='pagePath',
                                  string_filter=Filter.StringFilter(
                                      match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
                                      value=page_path_prefix)))
            resp = client.run_report(RunReportRequest(**req_args))
            return [
                {'page': row.dimension_values[0].value,
                 'views': int(row.metric_values[0].value)}
                for row in resp.rows
            ]

        return self._call('recent_pageviews', go, payload=payload)

    def user_session_summary(self, *, ga_client_id: str,
                             days: int = 30) -> AdapterCallResult:
        """Per-user behavior summary for RAG prompt enrichment."""
        payload = {'ga_client_id': ga_client_id, 'days': days}

        def go():
            # Placeholder; full impl depends on GA4 schema design with client.
            return {'ga_client_id': ga_client_id,
                    'sessions': 0, 'top_pages': []}

        return self._call('user_session_summary', go, payload=payload)
