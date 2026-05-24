"""Adapter framework tests — verify gating, dry-run, error capture, and wiring."""
import os
import sys

import pytest


from centaurus_adapters import (  # noqa: E402
    FeedbackAdapter,
    QuizAdapter,
    RoadmapAdapter,
    GA4Adapter,
    WPUserAdapter,
    NotifyAdapter,
    SNSPublishAdapter,
    AdapterRegistry,
)


@pytest.fixture(autouse=True)
def clear_env():
    keys = [k for k in os.environ if k.startswith('CTR_')]
    saved = {k: os.environ[k] for k in keys}
    for k in keys:
        del os.environ[k]
    yield
    for k in keys:
        os.environ.pop(k, None)
    os.environ.update(saved)


class TestBaseGating:
    def test_disabled_by_default(self):
        a = FeedbackAdapter()
        assert a.enabled is False

    def test_enabled_via_env(self):
        os.environ['CTR_FEEDBACK_ENABLED'] = '1'
        a = FeedbackAdapter()
        assert a.enabled is True

    def test_force_enabled_overrides_env(self):
        a = FeedbackAdapter(force_enabled=True)
        assert a.enabled is True

    def test_dry_run_skips_writer(self):
        called = []
        a = FeedbackAdapter(persistence_writer=lambda p: called.append(p),
                            dry_run=True, force_enabled=True)
        r = a.submit(target_id='c1', target_kind='chat_reply', rating='up')
        assert r.ok is True
        assert r.dry_run is True
        assert called == []

    def test_disabled_returns_noop_ok(self):
        a = FeedbackAdapter()
        r = a.submit(target_id='c1', target_kind='chat_reply', rating='up')
        assert r.ok is True
        assert r.meta.get('reason') == 'disabled'


class TestFeedback:
    def test_submit_writes_payload(self):
        captured = []
        a = FeedbackAdapter(persistence_writer=lambda p: captured.append(p),
                            force_enabled=True)
        r = a.submit(target_id='msg-1', target_kind='chat_reply',
                     rating='up', user_id='u1',
                     context={'intent': 'ask_lesson'})
        assert r.ok is True
        assert len(captured) == 1
        assert captured[0]['rating'] == 'up'
        assert captured[0]['target_id'] == 'msg-1'

    def test_invalid_rating_rejected(self):
        a = FeedbackAdapter(force_enabled=True)
        r = a.submit(target_id='msg-1', target_kind='chat_reply',
                     rating='maybe')
        assert r.ok is False
        assert 'invalid rating' in r.error

    def test_writer_exception_captured_not_raised(self):
        def bad(_):
            raise RuntimeError('db down')
        a = FeedbackAdapter(persistence_writer=bad, force_enabled=True)
        r = a.submit(target_id='m', target_kind='chat_reply', rating='up')
        assert r.ok is False
        assert 'RuntimeError' in r.error


class TestRoadmapFallback:
    def test_disabled_uses_fallback_provider(self):
        fb_calls = []
        def fb(job):
            fb_calls.append(job)
            return [{'section': 's1'}, {'section': 's2'}]
        a = RoadmapAdapter(fallback_provider=fb)
        r = a.next_sections(job_key='ad', completed_lesson_ids=[], limit=5)
        assert r.ok is True
        assert len(r.data) == 2
        assert fb_calls == ['ad']
        assert r.meta.get('mode') == 'fallback'

    def test_enabled_uses_ordering(self):
        a = RoadmapAdapter(
            ordering_provider=lambda j: [{'section': f'{j}-1'}],
            fallback_provider=lambda j: [{'section': 'fb'}],
            force_enabled=True)
        r = a.next_sections(job_key='ad', completed_lesson_ids=[], limit=5)
        assert r.ok is True
        assert r.data[0]['section'] == 'ad-1'


class TestWPUserFallback:
    def test_anonymous_when_disabled(self):
        a = WPUserAdapter()
        r = a.resolve_session(anonymous_id='abc-123')
        assert r.ok is True
        assert r.data['user_id'] == 'anon:abc-123'
        assert r.data['kind'] == 'anonymous'


class TestNotify:
    def test_send_uses_overrides_when_enabled(self):
        seen = []
        def slack_fn(s, b):
            seen.append(('slack', s, b))
        a = NotifyAdapter(channel_overrides={'slack': slack_fn},
                          force_enabled=True)
        r = a.send(subject='t', body='b', channels=['slack'],
                   severity='warning')
        assert r.ok is True
        assert r.data['slack']['ok'] is True
        assert seen[0][1].startswith('⚠ ')


class TestSNSDryRun:
    def test_dry_run_default(self):
        a = SNSPublishAdapter(force_enabled=True)
        r = a.publish(channel='x', body='hello')
        # default dry_run=True for safety
        assert r.dry_run is True

    def test_unsupported_channel(self):
        a = SNSPublishAdapter(force_enabled=True, dry_run=False)
        r = a.publish(channel='myspace', body='x')
        assert r.ok is False
        assert 'unsupported' in r.error

    def test_draft_naive_default(self):
        a = SNSPublishAdapter(force_enabled=True, dry_run=False)
        excerpts = [{'role': 'user', 'content': 'q'},
                    {'role': 'assistant', 'content': '答えです'}]
        r = a.draft_from_chat(chat_excerpts=excerpts, channel='x')
        assert r.ok is True
        assert r.data == '答えです'

    def test_draft_truncates_to_max_len(self):
        a = SNSPublishAdapter(force_enabled=True, dry_run=False)
        long = 'あ' * 1000
        excerpts = [{'role': 'assistant', 'content': long}]
        r = a.draft_from_chat(chat_excerpts=excerpts, channel='x')
        assert len(r.data) == 280


class TestQuizStub:
    def test_disabled_noop(self):
        a = QuizAdapter()
        r = a.fetch_quiz('q1')
        assert r.ok is True
        assert r.meta.get('reason') == 'disabled'

    def test_remediation_via_lookup(self):
        a = QuizAdapter(force_enabled=True)
        r = a.suggest_remediation(
            wrong_quiz_ids=['q1', 'q2'],
            lesson_lookup=lambda q: [f'lesson-for-{q}'])
        assert r.ok is True
        assert len(r.data) == 2
        assert r.data[0]['recommended_lessons'] == ['lesson-for-q1']


class TestRegistry:
    def test_register_and_health(self):
        reg = AdapterRegistry()
        reg.register(FeedbackAdapter())
        reg.register(NotifyAdapter())
        h = reg.health_all()
        names = {x['name'] for x in h}
        assert 'feedback' in names
        assert 'notify' in names
        for entry in h:
            assert 'enabled' in entry
            assert 'env_flag' in entry
            assert 'ops' in entry
