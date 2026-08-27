"""HTTP utility client with timeout, retry, and backoff (zero-dependency)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)


def fetch_url(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    retries: int = 3,
    backoff_factor: float = 1.5,
) -> str | None:
    """Fetch URL contents with timeout, retry, and exponential backoff."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # 429 Too Many Requests or 5xx server errors are worth retrying
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                time.sleep(sleep_time)
                continue
            # Other errors (e.g. 404, 403) are not retried
            break
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                time.sleep(sleep_time)
                continue
            break
    return None


def fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    retries: int = 3,
    backoff_factor: float = 1.5,
) -> object | None:
    """Fetch URL and parse as JSON."""
    content = fetch_url(url, headers, timeout, retries, backoff_factor)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None
