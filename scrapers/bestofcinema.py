import logging
import re
from datetime import datetime
from typing import Optional

from scrapers.base import BaseScraper, Screening
from services.tmdb import TMDBService

logger = logging.getLogger(__name__)


class BestOfCinemaScraper(BaseScraper):
    def __init__(
        self, cinema_name: str, url: str, tmdb_service: Optional[TMDBService] = None
    ):
        super().__init__(cinema_name, url)
        self.tmdb_service = tmdb_service

    async def get_screenings(self) -> list[Screening]:
        soup = await self.fetch_page(self.url)
        screenings = []

        movie_links = []
        for link in soup.select("a[href^='/']"):
            href = link.get("href", "")
            if href and self._is_movie_link(href):
                full_url = f"https://www.bestofcinema.de{href}"
                if full_url not in movie_links:
                    movie_links.append(full_url)

        for movie_url in movie_links:
            movie_data = await self._fetch_movie_info(movie_url)
            if not movie_data:
                continue

            movie_title, year, poster_url, screening_date, bocruntime = movie_data[:5]

            tmdb_url = None
            runtime = bocruntime
            if self.tmdb_service and movie_title:
                keep_original_title = self.tmdb_service._is_multi_part_title(
                    movie_title
                )
                tmdb_info = await self.tmdb_service.get_movie_info(
                    movie_title, year, keep_original_title
                )
                if tmdb_info and len(tmdb_info) == 5:
                    tmdb_title, tmdb_year, tmdb_poster, tmdb_url, tmdb_runtime = (
                        tmdb_info
                    )
                    if not keep_original_title and tmdb_title:
                        movie_title = tmdb_title
                    if tmdb_year:
                        year = tmdb_year
                    if tmdb_poster:
                        poster_url = tmdb_poster
                    if tmdb_runtime:
                        runtime = tmdb_runtime

            screenings.append(
                Screening(
                    cinema_name=self.cinema_name,
                    movie_title=movie_title,
                    date=screening_date,
                    url=movie_url,
                    poster_url=poster_url,
                    year=year,
                    tmdb_url=tmdb_url,
                    skip_year_filter=True,
                    runtime=runtime,
                )
            )

        return screenings

    def _is_movie_link(self, href: str) -> bool:
        if "#" in href:
            return False
        if href.startswith("//"):
            return False
        if href.startswith("/kinobetreiber"):
            return False
        if href.startswith("/bisherige_filme"):
            return False
        if href.startswith("/impressum"):
            return False
        if href.startswith("/datenschutz"):
            return False
        if href in ["/", "/index.html"]:
            return False
        if "_" not in href and not any(c.isdigit() for c in href):
            return False
        return True

    async def _fetch_movie_info(self, url: str):
        soup = await self.fetch_page(url)
        if not soup:
            return None

        title_elem = soup.select_one("h1")
        if not title_elem:
            return None

        movie_title = title_elem.get_text(strip=True)

        page_text = soup.get_text()
        year = None
        year_match = re.search(r"Produktionsjahr:\s*(\d{4})", page_text)
        if year_match:
            year = int(year_match.group(1))

        runtime = 0
        runtime_match = re.search(r"Lauflänge\s*(\d+)\s*min", page_text, re.IGNORECASE)
        if runtime_match:
            runtime = int(runtime_match.group(1))

        poster_url = None
        poster_img = soup.select_one(".detail_cover img")
        if poster_img:
            poster_url = poster_img.get("data-src") or poster_img.get("src")

        date_str = None
        date_elem = soup.select_one(".detail_headline p b")
        if date_elem:
            date_str = date_elem.get_text(strip=True)

        screening_date = None
        if date_str:
            match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})", date_str)
            if match:
                day, month, short_year = match.groups()
                full_year = 2000 + int(short_year)
                try:
                    screening_date = datetime.strptime(
                        f"{day}.{month}.{full_year}", "%d.%m.%Y"
                    )
                except ValueError:
                    screening_date = datetime.now()

        if not screening_date:
            screening_date = datetime.now()

        return movie_title, year, poster_url, screening_date, runtime
