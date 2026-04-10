from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup


@dataclass
class Screening:
    cinema_name: str
    movie_title: str
    date: datetime
    url: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    tmdb_url: Optional[str] = None
    skip_year_filter: bool = False
    runtime: int = 0


class BaseScraper:
    def __init__(self, cinema_name: str, url: str):
        self.cinema_name = cinema_name
        self.url = url
        self._last_request_time: Optional[datetime] = None

    def get_screenings(self) -> list[Screening]:
        raise NotImplementedError("Subclasses must implement get_screenings()")

    def fetch_page(self, url: str) -> BeautifulSoup:
        self._rate_limit()
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def fetch_text(self, url: str) -> str:
        self._rate_limit()
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return response.text

    def fetch_page_js(self, url: str) -> BeautifulSoup:
        from playwright.sync_api import sync_playwright

        self._rate_limit()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
        return BeautifulSoup(html, "lxml")

    def _rate_limit(self) -> None:
        import time

        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        self._last_request_time = datetime.now()
