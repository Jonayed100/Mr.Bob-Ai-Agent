import pytest

from app.ratelimit import LoginGuard


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_locks_after_too_many_wrong_passwords():
    clock = FakeClock()
    guard = LoginGuard(max_fails=3, window=60, lockout=120, clock=clock)
    for _ in range(2):
        guard.failed("1.2.3.4")
        assert guard.retry_after("1.2.3.4") == 0
    guard.failed("1.2.3.4")
    assert guard.retry_after("1.2.3.4") > 0
    assert guard.retry_after("5.6.7.8") == 0  # other people are not affected


def test_lockout_ends_after_waiting():
    clock = FakeClock()
    guard = LoginGuard(max_fails=2, window=60, lockout=120, clock=clock)
    guard.failed("ip")
    guard.failed("ip")
    clock.t += 121
    assert guard.retry_after("ip") == 0


def test_old_mistakes_are_forgotten():
    clock = FakeClock()
    guard = LoginGuard(max_fails=3, window=60, lockout=120, clock=clock)
    guard.failed("ip")
    guard.failed("ip")
    clock.t += 61
    guard.failed("ip")
    assert guard.retry_after("ip") == 0


def test_success_clears_mistakes():
    guard = LoginGuard(max_fails=2, window=60, lockout=120, clock=FakeClock())
    guard.failed("ip")
    guard.succeeded("ip")
    guard.failed("ip")
    assert guard.retry_after("ip") == 0


def test_changing_password_logs_out_old_sessions():
    pytest.importorskip("fastapi")
    pytest.importorskip("itsdangerous")
    from app.config import Settings
    from app.security import make_token, token_ok

    old = Settings(dashboard_password="first-password", secret_key="k" * 40)
    new = Settings(dashboard_password="second-password", secret_key="k" * 40)
    token = make_token(old)
    assert token_ok(token, old)
    assert not token_ok(token, new)
    assert not token_ok("forged-token", old)
