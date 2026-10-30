"""Polite HTTP client: identifies itself, honours robots.txt, rate-limits per host,
bounded retries, timeouts. It never tries to evade access controls."""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

UA = "taiwan-agri-land-law-bot/1.0 (+https://github.com/ottoted34/taiwan-agri-land-law)"


class SourceError(Exception):
    kind = "error"


class RobotsDisallowed(SourceError):
    kind = "robots_disallowed"


class SourceUnavailable(SourceError):
    kind = "unavailable"


class BadContent(SourceError):
    kind = "bad_content"


@dataclass
class Response:
    url: str
    status: int
    content: bytes
    headers: dict
    text: str


class Client:
    def __init__(self, min_interval: float = 1.5, timeout: float = 30, retries: int = 2,
                 respect_robots: bool = True, session: requests.Session | None = None):
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "zh-TW,zh;q=0.9"})
        self.min_interval = min_interval
        self.timeout = timeout
        self.retries = retries
        self.respect_robots = respect_robots
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.requests_made = 0

    def robots_allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        p = urlparse(url)
        host = f"{p.scheme}://{p.netloc}"
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(host + "/robots.txt", timeout=self.timeout)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                elif r.status_code in (401, 403):
                    rp.disallow_all = True
                else:  # 404 etc. -> no restrictions published
                    rp.allow_all = True
            except requests.RequestException:
                rp = None  # unknown; treat as unavailable later
            self._robots[host] = rp
        rp = self._robots[host]
        if rp is None:
            raise SourceUnavailable(f"robots.txt unreachable for {host}")
        return rp.can_fetch(UA, url)

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            delta = time.monotonic() - last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
        self._last[host] = time.monotonic()

    def get(self, url: str, timeout: float | None = None, expect_html: bool = False) -> Response:
        if not self.robots_allowed(url):
            raise RobotsDisallowed(url)
        host = urlparse(url).netloc
        err: Exception | None = None
        for attempt in range(self.retries + 1):
            self._wait(host)
            try:
                r = self.s.get(url, timeout=timeout or self.timeout)
                self.requests_made += 1
                if r.status_code in (429, 500, 502, 503, 504):
                    err = SourceUnavailable(f"HTTP {r.status_code} {url}")
                    time.sleep(3 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    raise SourceUnavailable(f"HTTP {r.status_code} {url}")
                enc = r.encoding
                if not enc or enc.lower() == "iso-8859-1":
                    enc = r.apparent_encoding or "utf-8"
                text = r.content.decode(enc, "replace") if expect_html else ""
                if expect_html and "<html" not in text[:5000].lower():
                    raise BadContent(f"not HTML: {url}")
                return Response(r.url, r.status_code, r.content, dict(r.headers), text)
            except requests.RequestException as e:
                err = SourceUnavailable(f"{type(e).__name__}: {url}")
                time.sleep(3 * (attempt + 1))
        raise err or SourceUnavailable(url)
