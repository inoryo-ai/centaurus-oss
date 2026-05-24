"""NotifyAdapter — email / Slack / LINE notification fanout.

Channels are pluggable. Default channels: email (SMTP), slack (webhook), line.
Set CTR_NOTIFY_CHANNELS=email,slack to enable.

ENV_FLAG: CTR_NOTIFY_ENABLED
Per-channel env:
  email  → CTR_SMTP_HOST / CTR_SMTP_USER / CTR_SMTP_PASSWORD / CTR_SMTP_FROM / CTR_SMTP_TO
  slack  → CTR_SLACK_WEBHOOK_URL
  line   → CTR_LINE_NOTIFY_TOKEN

Cross-business: every product (various downstream products) needs ops alerts.
"""
from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText
from typing import Callable, Any

from .base import AdapterBase, AdapterCallResult


class NotifyAdapter(AdapterBase):
    NAME = 'notify'
    ENV_FLAG = 'CTR_NOTIFY_ENABLED'

    SUPPORTED_CHANNELS = ('email', 'slack', 'line')

    def __init__(self,
                 channel_overrides: dict[str, Callable[[str, str], Any]] | None = None,
                 *, dry_run: bool = False,
                 force_enabled: bool | None = None):
        super().__init__(dry_run=dry_run, force_enabled=force_enabled)
        self._channel_overrides = channel_overrides or {}

    def _ops(self) -> list[str]:
        return ['send', 'configured_channels']

    @property
    def configured_channels(self) -> list[str]:
        raw = os.environ.get('CTR_NOTIFY_CHANNELS', '').strip()
        if not raw:
            return []
        return [c.strip() for c in raw.split(',')
                if c.strip() in self.SUPPORTED_CHANNELS]

    def send(self, *, subject: str, body: str,
             channels: list[str] | None = None,
             severity: str = 'info') -> AdapterCallResult:
        """Send a notification across channels.

        severity: info | warning | critical (used for prefix only)
        """
        targets = channels or self.configured_channels
        payload = {'subject': subject, 'body_len': len(body),
                   'channels': targets, 'severity': severity}

        def go():
            results = {}
            prefix = {'info': '', 'warning': '⚠ ',
                      'critical': '🚨 '}.get(severity, '')
            full_subject = f'{prefix}{subject}'
            for ch in targets:
                fn = self._channel_overrides.get(ch) \
                    or getattr(self, f'_send_{ch}', None)
                if fn is None:
                    results[ch] = {'ok': False, 'error': 'unknown channel'}
                    continue
                try:
                    fn(full_subject, body)
                    results[ch] = {'ok': True}
                except Exception as e:
                    results[ch] = {'ok': False, 'error': str(e)}
            return results

        return self._call('send', go, payload=payload)

    def _send_email(self, subject: str, body: str) -> None:
        host = os.environ['CTR_SMTP_HOST']
        port = int(os.environ.get('CTR_SMTP_PORT', '587'))
        user = os.environ['CTR_SMTP_USER']
        pwd = os.environ['CTR_SMTP_PASSWORD']
        from_addr = os.environ['CTR_SMTP_FROM']
        to_addrs = [a.strip() for a in
                    os.environ['CTR_SMTP_TO'].split(',') if a.strip()]
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.login(user, pwd)
            s.sendmail(from_addr, to_addrs, msg.as_string())

    def _send_slack(self, subject: str, body: str) -> None:
        import urllib.request
        url = os.environ['CTR_SLACK_WEBHOOK_URL']
        data = json.dumps({'text': f'*{subject}*\n{body}'}).encode('utf-8')
        req = urllib.request.Request(
            url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()

    def _send_line(self, subject: str, body: str) -> None:
        import urllib.request
        import urllib.parse
        token = os.environ['CTR_LINE_NOTIFY_TOKEN']
        msg = f'\n{subject}\n{body}'[:1000]
        data = urllib.parse.urlencode({'message': msg}).encode('utf-8')
        req = urllib.request.Request(
            'https://notify-api.line.me/api/notify', data=data,
            headers={'Authorization': f'Bearer {token}',
                     'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
