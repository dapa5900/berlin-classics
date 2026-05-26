import logging
import re
from datetime import datetime
from typing import Optional

from bs4 import Tag
from scrapers.base import BaseScraper, Screening
from services.tmdb import TMDBService

logger = logging.getLogger(__name__)


class OpenAirKinoScraper(BaseScraper):
    def __init__(
        self,
        cinema_name: str,
        url: str,
        tmdb_service: Optional[TMDBService] = None,
        threshold_year: int = 2010,
    ):
        super().__init__(cinema_name, url, threshold_year)
        self.tmdb_service = tmdb_service

    async def get_screenings(self) -> list[Screening]:
        soup = await self.fetch_page(self.url)
        if not soup:
            return []

        screenings = []
        seen_titles = set()

        articles = soup.find_all("article", class_=re.compile(r"post|type-post"))

        for article in articles:
            screening = self._parse_entry(article)
            if not screening:
                continue

            key = (screening.movie_title.lower(), screening.date.strftime("%Y-%m-%d"))
            if key in seen_titles:
                continue
            seen_titles.add(key)

            title = screening.movie_title
            year = screening.year
            poster_url = screening.poster_url
            runtime = screening.runtime
            tmdb_url = screening.tmdb_url

            if self.tmdb_service and title:
                keep_original_title = self.tmdb_service._is_multi_part_title(title)
                tmdb_info = await self.tmdb_service.get_movie_info(
                    title, keep_original_title=keep_original_title
                )
                if tmdb_info and len(tmdb_info) == 5:
                    tmdb_title, tmdb_year, tmdb_poster, tmdb_url, tmdb_runtime = tmdb_info
                    if not keep_original_title and tmdb_title:
                        title = tmdb_title
                    if tmdb_year:
                        year = tmdb_year
                    if tmdb_poster:
                        poster_url = tmdb_poster
                    if tmdb_runtime:
                        runtime = tmdb_runtime

            if year and year > self.threshold_year:
                continue

            screenings.append(
                Screening(
                    cinema_name=self.cinema_name,
                    movie_title=title,
                    date=screening.date,
                    url=screening.url,
                    year=year,
                    poster_url=poster_url,
                    tmdb_url=tmdb_url,
                    runtime=runtime,
                    skip_year_filter=False,
                    venue_name=screening.venue_name,
                )
            )

        return screenings

    def _parse_entry(self, article: Tag) -> Optional[Screening]:
        date_str = None
        time_str = None
        title = None
        cinema_name = None
        url = None

        meta_kino = article.find_previous_sibling("div", class_="meta_kino")
        if not meta_kino:
            prev = article.find_previous_sibling()
            if prev and prev.get("class") and "meta_kino" in prev["class"]:
                meta_kino = prev

        if meta_kino:
            date_elem = meta_kino.find("div", class_="meta_date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            time_elem = meta_kino.find("div", class_="meta_time")
            if time_elem:
                time_str = time_elem.get_text(strip=True)

        if not date_str:
            date_elem = article.find("div", class_="meta_date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            time_elem = article.find("div", class_="meta_time")
            if time_elem:
                time_str = time_elem.get_text(strip=True)

        if not date_str:
            return None

        if not time_str:
            time_str = "21:00"

        date_match = re.search(
            r"(\d{1,2})\.\s*([\w.]+)\s*(\d{2})", date_str
        )
        if not date_match:
            date_match = re.search(
                r"(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?", date_str
            )

        month_map = {
            "Jan": 1, "Januar": 1,
            "Feb": 2, "Februar": 2,
            "Mär": 3, "März": 3,
            "Apr": 4, "April": 4,
            "Mai": 5,
            "Jun": 6, "Juni": 6,
            "Jul": 7, "Juli": 7,
            "Aug": 8, "August": 8,
            "Sep": 9, "Sept": 9, "September": 9,
            "Ok": 10, "Okt": 10, "Oktober": 10,
            "Nov": 11, "November": 11,
            "Dez": 12, "Dezember": 12,
        }

        if date_match:
            day = int(date_match.group(1))
            month_str = date_match.group(2)
            month = month_map.get(month_str)
            if not month:
                for k, v in month_map.items():
                    if month_str.lower().startswith(k.lower()):
                        month = v
                        break
            if not month:
                return None
            year_part = date_match.group(3)
            if year_part:
                year_int = int(year_part)
                if year_int < 100:
                    year_int += 2000
            else:
                year_int = 2026

            time_parts = time_str.strip().split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            screening_date = datetime(year_int, month, day, hour, minute)
        else:
            screening_date = datetime.now()

        title_link = article.find("h2", class_="entry-title")
        if title_link:
            a = title_link.find("a")
            if a:
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if href and href.startswith("http"):
                    url = href
                elif href and href.startswith("/"):
                    url = f"https://openair-kino.net{href}"

        if not title:
            title_link = article.select_one("a[href*='/20'][href*='/']")
            if title_link:
                title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                if href and not href.startswith("#"):
                    if href.startswith("http"):
                        url = href
                    elif href.startswith("/"):
                        url = f"https://openair-kino.net{href}"

        if not title:
            return None

        if not url:
            film_link = article.find("div", class_="meta_filminfo")
            if film_link:
                a = film_link.find("a")
                if a:
                    href = a.get("href", "")
                    if href and href.startswith("http"):
                        url = href

        cinema_elem = article.find("div", class_="kinos")
        if cinema_elem:
            a = cinema_elem.find("a")
            if a:
                cinema_name = a.get_text(strip=True)

        if not cinema_name:
            cinema_name = "Berlin"

        return Screening(
            cinema_name=cinema_name,
            movie_title=title,
            date=screening_date,
            url=url,
            year=None,
            poster_url=None,
            tmdb_url=None,
            runtime=0,
            venue_name=cinema_name,
        )
