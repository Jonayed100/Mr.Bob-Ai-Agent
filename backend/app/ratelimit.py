"""Small in-memory limiter that stops password guessing.

After `max_fails` wrong passwords from one address inside `window` seconds,
that address is locked out for `lockout` seconds. Mr. Bob runs as a single
process, so keeping this in memory is enough.
"""
import threading
import time


class LoginGuard:
    def __init__(self, max_fails: int = 5, window: int = 15 * 60, lockout: int = 15 * 60, clock=time.monotonic):
        self.max_fails = max_fails
        self.window = window
        self.lockout = lockout
        self._clock = clock
        self._fails: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Seconds until this address may try again (0 means it may try now)."""
        with self._lock:
            until = self._locked_until.get(key, 0)
            left = until - self._clock()
            if left <= 0:
                self._locked_until.pop(key, None)
                return 0
            return int(left) + 1

    def failed(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            recent = [t for t in self._fails.get(key, []) if now - t < self.window]
            recent.append(now)
            if len(recent) >= self.max_fails:
                self._locked_until[key] = now + self.lockout
                recent = []
            self._fails[key] = recent
            if len(self._fails) > 5000:  # keep memory bounded
                self._fails = {k: v for k, v in self._fails.items() if v and now - v[-1] < self.window}

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)
            self._locked_until.pop(key, None)


login_guard = LoginGuard()
