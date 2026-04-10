import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from scrapers.base import BaseScraper, Screening
from services.tmdb import TMDBService

logger = logging.getLogger(__name__)


class BabylonScraper(BaseScraper):
    def __init__(
        self, cinema_name: str, url: str, tmdb_service: Optional[TMDBService] = None
    ):
        super().__init__(cinema_name, url)
        self.tmdb_service = tmdb_service

    def get_screenings(self) -> list[Screening]:
        soup = self.fetch_page(self.url)
        screenings = []

        for event in soup.select(".mix"):
            title_elem = event.select_one(".mix-title")
            date_elem = event.select_one(".mix-date")
            link_elem = event.select_one("a")
            img_elem = event.select_one("img")

            if not title_elem or not date_elem:
                continue

            movie_title = title_elem.get_text(strip=True)
            if not movie_title:
                movie_title = event.get("data-title", "")

            date_str = date_elem.get_text(strip=True)

            match = re.search(r"(\d{2})\.(\d{2})\.?\s*(\d{2}:\d{2})", date_str)
            if match:
                day, month, time_str = match.groups()
                year = datetime.now().year
                try:
                    screening_date = datetime.strptime(
                        f"{day}.{month}.{year} {time_str}", "%d.%m.%Y %H:%M"
                    )
                except ValueError:
                    screening_date = datetime.now().replace(hour=20, minute=0)
            else:
                screening_date = datetime.now().replace(hour=20, minute=0)

            url = link_elem.get("href") if link_elem else None
            if url and not url.startswith("http"):
                url = f"https://babylonberlin.eu{url}"

            poster_url = None
            if img_elem:
                poster_url = img_elem.get("src") or img_elem.get("data-src")

            babylon_year = None
            babylon_runtime = 0
            babylon_original_title = None
            if url:
                movie_info = self._fetch_movie_info(url)
                if movie_info:
                    movie_title = movie_info[0]
                    babylon_year = movie_info[1]
                    babylon_runtime = movie_info[2] if len(movie_info) > 2 else 0
                    babylon_original_title = (
                        movie_info[3] if len(movie_info) > 3 else None
                    )
                    if babylon_original_title:
                        logger.info(
                            f"Extracted original_title '{babylon_original_title}' for '{movie_title}'"
                        )

            year = babylon_year
            tmdb_url = None
            runtime = babylon_runtime
            keep_original_title = False

            if self.tmdb_service and movie_title:
                keep_original_title = self.tmdb_service._is_multi_part_title(
                    movie_title
                )
                tmdb_info = self.tmdb_service.get_movie_info(
                    movie_title,
                    babylon_year,
                    keep_original_title,
                    babylon_original_title,
                )
                if tmdb_info and len(tmdb_info) == 5:
                    tmdb_title, tmdb_year, tmdb_poster, tmdb_url, tmdb_runtime = (
                        tmdb_info
                    )
                    if not keep_original_title and tmdb_title:
                        movie_title = tmdb_title
                    if not babylon_year and tmdb_year:
                        year = tmdb_year
                    if tmdb_poster:
                        poster_url = tmdb_poster
                    if not runtime and tmdb_runtime:
                        runtime = tmdb_runtime

            screenings.append(
                Screening(
                    cinema_name=self.cinema_name,
                    movie_title=movie_title,
                    date=screening_date,
                    url=url,
                    poster_url=poster_url,
                    year=year,
                    tmdb_url=tmdb_url,
                    runtime=runtime,
                )
            )

        return screenings

    def _fetch_movie_info(
        self, url: str
    ) -> Optional[Tuple[str, Optional[int], int, Optional[str]]]:
        soup = self.fetch_page(url)
        if not soup:
            return None

        page_text = soup.get_text()

        # 1. Year: look for 4 digits that aren't part of a duration or range
        # Prioritize 4 digits that are clearly a year
        year = None
        year_match = re.search(r",\s*(\d{4})", page_text)
        if year_match:
            year = int(year_match.group(1))

        if not year:
            # Fallback: look for 4 digits that are not immediately followed by "Min"
            year_matches = re.finditer(r"\b(18\d{2}|19\d{2}|20\d{2})\b", page_text)
            for match in year_matches:
                potential_year = int(match.group(1))
                # Check next word is not "Min"
                after_match = page_text[match.end() : match.end() + 10]
                if "Min" not in after_match:
                    year = potential_year
                    break

        # 2. Runtime
        runtime = 0
        runtime_match = re.search(r",\s*(\d+)\s*Min", page_text)
        if not runtime_match:
            runtime_match = re.search(r"(\d+)\s*Min", page_text)
        if runtime_match:
            runtime = int(runtime_match.group(1))

        # 3. Original Title (ignore language/format tags)
        original_title = None
        # Get all bracketed contents
        bracket_contents = re.findall(r"\[([^\]]+)\]", page_text)
        for content in bracket_contents:
            content_clean = content.strip()
            # Ignore common language/format tags
            if content_clean.lower() not in ["omeu", "omu", "ov", "df", "english ov"]:
                original_title = content_clean
                break

        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if " - " in title_text:
                return (
                    title_text.split(" - ")[-1].strip(),
                    year,
                    runtime,
                    original_title,
                )

        title_elem = soup.select_one("h1")
        if title_elem:
            return (title_elem.get_text(strip=True), year, runtime, original_title)

        return None
