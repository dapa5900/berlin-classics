import logging
import locale
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import Page
from scrapers.base import BaseScraper, Screening

logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, "German")
except locale.Error:
    pass


class ZooPalastScraper(BaseScraper):
    def __init__(
        self,
        cinema_name: str,
        url: str,
        page: Page,
        threshold_year: int,
    ):
        super().__init__(cinema_name, url)
        self.page = page
        self._cinema_domain = "zoopalast.premiumkino.de"
        self.threshold_year = threshold_year

    async def get_screenings(self) -> list[Screening]:
        program_data = await self._fetch_program_api()
        if not program_data:
            return []
        return self._extract_classic_screenings(
            program_data, self.cinema_name, self.threshold_year
        )

    async def _fetch_program_api(self) -> Optional[dict]:
        program_data: dict = {}

        async def handle_response(resp):
            if "/program" in resp.url and "premiumkino" in resp.url:
                try:
                    program_data.update(await resp.json())
                except Exception:
                    pass

        self.page.on("response", handle_response)
        await self.page.goto(f"https://{self._cinema_domain}/programm", wait_until="networkidle", timeout=30000)
        await self.page.wait_for_timeout(3000)
        self.page.remove_listener("response", handle_response)

        if not program_data:
            return None

        klassiker_slugs: set[str] = set()
        klassiker_names: set[str] = set()
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self.page.goto(
                    f"https://{self._cinema_domain}/specials/filmklassiker/filmklassiker",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await self.page.wait_for_timeout(5000)
                html = await self.page.content()
                soup = BeautifulSoup(html, "lxml")

                for h3 in soup.find_all("h3"):
                    name = h3.get_text(strip=True)
                    if name:
                        klassiker_names.add(name)

                movie_names_in_api = set(
                    m.get("name", "").strip()
                    for m in program_data.get("movies", [])
                    if m.get("name")
                )
                matched = klassiker_names & movie_names_in_api
                unmatched = klassiker_names - movie_names_in_api

                logger.info(
                    f"[Filmklassiker] h3 count={len(klassiker_names)}, "
                    f"matched={len(matched)}, unmatched={len(unmatched)}"
                )
                if unmatched:
                    logger.info(f"[Filmklassiker] Unmatched h3: {sorted(unmatched)}")

                for m in program_data.get("movies", []):
                    name = (m.get("name") or "").strip()
                    if name in klassiker_names:
                        slug = m.get("slug")
                        if slug:
                            klassiker_slugs.add(slug)

                logger.info(f"[Filmklassiker] klassiker_slugs: {sorted(klassiker_slugs)}")
                break
            except Exception as e:
                logger.warning(f"[Filmklassiker] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    await self.page.wait_for_timeout(2000)
                if attempt == max_retries:
                    logger.warning("[Filmklassiker] All retries failed, continuing without Filmklassiker data")

        program_data["_filmklassiker_slugs"] = klassiker_slugs

        return program_data

    def _extract_classic_screenings(
        self, program_data: dict, cinema_name: str, threshold_year: int
    ) -> list[Screening]:
        screenings = []

        movies = program_data.get("movies", [])
        performances = program_data.get("performances", [])
        klassiker_slugs = program_data.get("_filmklassiker_slugs", set())
        logger.info(f"[extract] klassiker_slugs count: {len(klassiker_slugs)}")

        movie_map = {m["id"]: m for m in movies}

        for perf in performances:
            movie_id = perf.get("movieId")
            if movie_id not in movie_map:
                continue

            movie = movie_map[movie_id]
            year = movie.get("year", 2026)
            movie_slug = movie.get("slug", "")

            is_klassiker = movie_slug in klassiker_slugs
            if not is_klassiker and year > threshold_year:
                continue

            title = movie.get("name", "Unknown")
            begin = perf.get("begin", "")
            perf_slug = perf.get("slug", "")

            try:
                screening_date = datetime.fromisoformat(begin.replace("Z", "+00:00"))
                if screening_date.tzinfo is not None:
                    screening_date = screening_date.replace(tzinfo=None)
            except Exception:
                continue

            poster_url = None
            if movie.get("poster"):
                poster_path = movie["poster"].get("src", "")
                if poster_path:
                    poster_url = f"https://cdn.premiumkino.de{poster_path}.jpg"

            url = None
            if perf_slug:
                url = f"https://{self._cinema_domain}/film/{perf_slug}"

            screenings.append(
                Screening(
                    cinema_name=cinema_name,
                    movie_title=title,
                    date=screening_date,
                    year=year,
                    poster_url=poster_url,
                    url=url,
                    runtime=0,
                    skip_year_filter=is_klassiker,
                    production_year=movie.get("year"),
                )
            )

        klassiker_count = sum(1 for s in screenings if s.skip_year_filter)
        logger.info(f"[extract] Total screenings: {len(screenings)}, Filmklassiker: {klassiker_count}")
        return screenings
