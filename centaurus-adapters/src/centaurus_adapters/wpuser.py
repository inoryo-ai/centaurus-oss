"""WPUserAdapter — WordPress user identity bridge.

Resolves WordPress user ID into platform user_id.
Activates when WP admin access is granted.

ENV_FLAG: CTR_WPUSER_ENABLED
Required env (when enabled):
  CTR_WP_API_BASE
  CTR_WP_APP_PASSWORD or CTR_WP_JWT

Fallback: pass-through using localStorage-issued anonymous id.

Cross-business: any product running on WordPress that needs identity.
"""
from __future__ import annotations

import os
from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class WPUserAdapter(AdapterBase):
    NAME = 'wpuser'
    ENV_FLAG = 'CTR_WPUSER_ENABLED'

    def __init__(self,
                 resolver: Callable[[str], dict] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._resolver = resolver

    def _ops(self) -> list[str]:
        return ['resolve_session', 'link_anonymous']

    @property
    def api_base(self) -> str:
        return os.environ.get('CTR_WP_API_BASE', '').strip()

    def resolve_session(self, *, wp_session_token: str | None = None,
                        anonymous_id: str | None = None) -> AdapterCallResult:
        """Resolve a session into a stable user_id.

        Order:
          1. wp_session_token + WP API → real WP user ID
          2. fallback: anonymous_id (localStorage-issued)
        """
        payload = {'wp_session_token_present': bool(wp_session_token),
                   'anonymous_id_present': bool(anonymous_id)}

        def go():
            if self._resolver is not None and wp_session_token:
                return self._resolver(wp_session_token)
            if not self.api_base or not wp_session_token:
                if anonymous_id:
                    return {'user_id': f'anon:{anonymous_id}',
                            'kind': 'anonymous',
                            'wp_user_id': None}
                raise RuntimeError('no resolver configured and no anonymous_id')
            import urllib.request
            import json as _json
            req = urllib.request.Request(
                f'{self.api_base.rstrip("/")}/wp-json/wp/v2/users/me')
            req.add_header('Cookie',
                           f'wordpress_logged_in={wp_session_token}')
            with urllib.request.urlopen(req, timeout=5) as resp:
                me = _json.loads(resp.read().decode('utf-8'))
            return {'user_id': f'wp:{me["id"]}', 'kind': 'wp',
                    'wp_user_id': me['id']}

        if not self.enabled:
            # When disabled: graceful anonymous fallback (still functional v1).
            try:
                if anonymous_id:
                    data = {'user_id': f'anon:{anonymous_id}',
                            'kind': 'anonymous',
                            'wp_user_id': None}
                else:
                    data = {'user_id': 'anon:unknown', 'kind': 'anonymous',
                            'wp_user_id': None}
                return AdapterCallResult(
                    ok=True, adapter=self.NAME, op='resolve_session',
                    latency_ms=0.0, data=data,
                    meta={'mode': 'fallback_anonymous'})
            except Exception as e:
                return AdapterCallResult(
                    ok=False, adapter=self.NAME, op='resolve_session',
                    latency_ms=0.0, error=str(e))

        return self._call('resolve_session', go, payload=payload)

    def link_anonymous(self, *, anonymous_id: str, wp_user_id: int,
                       linker: Callable[[dict], Any] | None = None,
                       ) -> AdapterCallResult:
        """Merge an anonymous identity into a WP user."""
        payload = {'anonymous_id': anonymous_id, 'wp_user_id': wp_user_id}

        def go():
            if linker is None:
                raise RuntimeError('linker callable required')
            return linker(payload)

        return self._call('link_anonymous', go, payload=payload)
