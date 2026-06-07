import random
import time
from collections import deque
from typing import Optional, Dict, Any
import requests


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 Smartlead-Unused-Accounts-Toolkit/1.0",
}


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls = deque()

    def wait(self):
        now = time.time()
        while self.calls and now - self.calls[0] > self.period:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            sleep_for = self.period - (now - self.calls[0]) + 0.001
            time.sleep(max(0.0, sleep_for))
        self.calls.append(time.time())


class HTTPClient:
    def __init__(self, logger, max_calls_per_window=10, window_seconds=2.0, timeout=30):
        self.logger = logger
        self.rate_limiter = RateLimiter(max_calls_per_window, window_seconds)
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = timeout

    def get_json(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None,
                 retries: int = 5, backoff_base: float = 0.8) -> Any:
        attempt = 0
        while True:
            self.rate_limiter.wait()
            try:
                resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {resp.status_code}: {resp.text[:250]}", response=resp)
                resp.raise_for_status()
                try:
                    return resp.json()
                except Exception as exc:
                    raise RuntimeError(f"Invalid JSON from {url}: {exc}")
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    raise
                delay = (backoff_base * (2 ** (attempt - 1))) + random.uniform(0.05, 0.25)
                self.logger.warning(f"Request error on {url}. Attempt {attempt}/{retries}. Sleeping {delay:.2f}s. Error: {e}")
                time.sleep(delay)
