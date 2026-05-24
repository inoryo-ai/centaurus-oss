"""Centaurus Adapter Framework.

Cross-business adapter base for plugging external services into Centaurus
products (various downstream products, etc.).

Design principles:
1. ABC interface fixed, concrete swappable via env flag.
2. ENV_FLAG ON/OFF: when off, adapter is no-op.
3. dry_run mode: log intent without calling external service.
4. Structured logging: latency, success, payload size emitted on every call.
5. Project-agnostic: no client-specific logic in base.
"""
from .base import AdapterBase, AdapterRegistry, AdapterCallResult, registry
from .feedback import FeedbackAdapter
from .quiz import QuizAdapter
from .roadmap import RoadmapAdapter
from .ga4 import GA4Adapter
from .wpuser import WPUserAdapter
from .notify import NotifyAdapter
from .sns import SNSPublishAdapter

__all__ = [
    'AdapterBase',
    'AdapterRegistry',
    'AdapterCallResult',
    'registry',
    'FeedbackAdapter',
    'QuizAdapter',
    'RoadmapAdapter',
    'GA4Adapter',
    'WPUserAdapter',
    'NotifyAdapter',
    'SNSPublishAdapter',
]
