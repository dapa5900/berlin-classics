import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page


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

    async def get_screenings(self) -> list[Screening]:
        raise NotImplementedError("Subclasses must implement get_screenings()")

    async def fetch_page(self, url: str) -> BeautifulSoup:
        await self._rate_limit_async()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")

    async def fetch_text(self, url: str) -> str:
        await self._rate_limit_async()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text

    async def fetch_page_js(self, url: str, page: Page) -> BeautifulSoup:
        await self._rate_limit_async()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        html = await page.content()
        return BeautifulSoup(html, "lxml")

    async def _rate_limit_async(self) -> None:
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        self._last_request_time = datetime.now()
