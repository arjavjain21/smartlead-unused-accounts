import json
import random
import time
from collections import deque
from typing import Optional, Dict, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener


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
        self.opener = build_opener()
        self.timeout = timeout

    def _build_url(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        if not params:
            return url
        query = urlencode(params)
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{query}"

    def _read_error_body(self, exc: HTTPError) -> str:
        try:
            return exc.read().decode("utf-8", errors="replace")[:250]
        except Exception:
            return str(exc)

    def get_json(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None,
                 retries: int = 5, backoff_base: float = 0.8) -> Any:
        attempt = 0
        while True:
            self.rate_limiter.wait()
            request_url = self._build_url(url, params)
            request = Request(request_url, headers=headers or {}, method="GET")
            try:
                with self.opener.open(request, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    try:
                        return json.loads(body)
                    except Exception as exc:
                        raise RuntimeError(f"Invalid JSON from {url}: {exc}")
            except HTTPError as e:
                attempt += 1
                retryable = e.code == 429 or e.code >= 500
                if not retryable or attempt > retries:
                    body = self._read_error_body(e)
                    raise RuntimeError(f"HTTP {e.code}: {body}") from e
                delay = (backoff_base * (2 ** (attempt - 1))) + random.uniform(0.05, 0.25)
                self.logger.warning(
                    f"Request error on {url}. Attempt {attempt}/{retries}. Sleeping {delay:.2f}s. Error: HTTP {e.code}"
                )
                time.sleep(delay)
            except (URLError, TimeoutError, RuntimeError) as e:
                attempt += 1
                if attempt > retries:
                    raise
                delay = (backoff_base * (2 ** (attempt - 1))) + random.uniform(0.05, 0.25)
                self.logger.warning(f"Request error on {url}. Attempt {attempt}/{retries}. Sleeping {delay:.2f}s. Error: {e}")
                time.sleep(delay)
