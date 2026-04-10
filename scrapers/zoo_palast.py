import locale
from datetime import datetime
from typing import Optional

from playwright.async_api import Page
from scrapers.base import BaseScraper, Screening

try:
    locale.setlocale(locale.LC_TIME, "German")
except locale.Error:
    pass


class ZooPalastScraper(BaseScraper):
    def __init__(self, cinema_name: str, url: str, page: Page):
        super().__init__(cinema_name, url)
        self.page = page

    async def get_screenings(self) -> list[Screening]:
        program_data = await self._fetch_program_api("zoopalast")
        if not program_data:
            return []

        return self._extract_classic_screenings(program_data, "Zoo Palast")

    async def _fetch_program_api(self, cinema_slug: str) -> Optional[dict]:
        program_data = {}

        async def handle_response(resp):
            if "/program" in resp.url and "premiumkino" in resp.url:
                try:
                    program_data.update(await resp.json())
                except Exception:
                    pass

        self.page.on("response", handle_response)
        url = f"https://{cinema_slug}.premiumkino.de/programm"
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await self.page.wait_for_timeout(3000)
        self.page.remove_listener("response", handle_response)

        return program_data if program_data else None

    def _extract_classic_screenings(
        self, program_data: dict, cinema_name: str
    ) -> list[Screening]:
        screenings = []
        threshold_year = 2010

        movies = program_data.get("movies", [])
        performances = program_data.get("performances", [])

        movie_map = {m["id"]: m for m in movies}

        for perf in performances:
            movie_id = perf.get("movieId")
            if movie_id not in movie_map:
                continue

            movie = movie_map[movie_id]
            year = movie.get("year", 2026)

            if year > threshold_year:
                continue

            title = movie.get("name", "Unknown")
            begin = perf.get("begin", "")
            slug = perf.get("slug", "")

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
            if slug:
                cinema_domain = (
                    "zoopalast.premiumkino.de"
                    if cinema_name == "Zoo Palast"
                    else "berlin.premiumkino.de"
                )
                url = f"https://{cinema_domain}/film/{slug}"

            screenings.append(
                Screening(
                    cinema_name=cinema_name,
                    movie_title=title,
                    date=screening_date,
                    year=year,
                    poster_url=poster_url,
                    url=url,
                    runtime=0,
                )
            )

        return screenings


class AstorScraper(BaseScraper):
    def __init__(self, cinema_name: str, url: str, page: Page):
        super().__init__(cinema_name, url)
        self.page = page

    async def get_screenings(self) -> list[Screening]:
        program_data = await self._fetch_program_api("berlin")
        if not program_data:
            return []

        return self._extract_classic_screenings(program_data, "Astor Film Lounge")

    async def _fetch_program_api(self, cinema_slug: str) -> Optional[dict]:
        program_data = {}

        async def handle_response(resp):
            if "/program" in resp.url and "premiumkino" in resp.url:
                try:
                    program_data.update(await resp.json())
                except Exception:
                    pass

        self.page.on("response", handle_response)
        url = f"https://{cinema_slug}.premiumkino.de/programm"
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await self.page.wait_for_timeout(3000)
        self.page.remove_listener("response", handle_response)

        return program_data if program_data else None

    def _extract_classic_screenings(
        self, program_data: dict, cinema_name: str
    ) -> list[Screening]:
        screenings = []
        threshold_year = 2010

        movies = program_data.get("movies", [])
        performances = program_data.get("performances", [])

        movie_map = {m["id"]: m for m in movies}

        for perf in performances:
            movie_id = perf.get("movieId")
            if movie_id not in movie_map:
                continue

            movie = movie_map[movie_id]
            year = movie.get("year", 2026)

            if year > threshold_year:
                continue

            title = movie.get("name", "Unknown")
            begin = perf.get("begin", "")
            slug = perf.get("slug", "")

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
            if slug:
                cinema_domain = (
                    "zoopalast.premiumkino.de"
                    if cinema_name == "Zoo Palast"
                    else "berlin.premiumkino.de"
                )
                url = f"https://{cinema_domain}/film/{slug}"

            screenings.append(
                Screening(
                    cinema_name=cinema_name,
                    movie_title=title,
                    date=screening_date,
                    year=year,
                    poster_url=poster_url,
                    url=url,
                    runtime=0,
                )
            )

        return screenings
