import json
import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper, Screening

logger = logging.getLogger(__name__)


def _clean_movie_title(title: str) -> str:
    cleaned = title.strip()
    while True:
        original = cleaned
        cleaned = re.sub(r"^SPECIAL:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"^(Klimareihe|OPEN AIR|OFFENE LEINWAND|REEL LOVE):\s*",
            "", cleaned, flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^MONDO VIDEO\s+(?:I+V?):\s*", "", cleaned, flags=re.IGNORECASE)
        if cleaned == original:
            break
    return cleaned.strip()


class FilmrauschScraper(BaseScraper):
    def __init__(self, cinema_name: str, url: str):
        super().__init__(cinema_name, url)

    async def get_screenings(self) -> list[Screening]:
        soup = await self.fetch_page(self.url)

        script_tag = soup.find("script", id="programm-script-config-js-extra")
        if not script_tag:
            logger.error("Could not find embedded program data script tag")
            return []

        script_text = script_tag.string
        if not script_text:
            logger.error("Script tag has no content")
            return []

        match = re.search(
            r"var filmrausch_php_vars\s*=\s*({.*?});", script_text, re.DOTALL
        )
        if not match:
            logger.error("Could not find filmrausch_php_vars in script")
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse filmrausch_php_vars JSON: {e}")
            return []

        cached = data.get("cached_data", {})
        shows = cached.get("shows", [])
        movies = cached.get("movies", {})

        if not shows:
            logger.warning("No shows found in Filmrausch cached data")
            return []

        screenings = []
        for show in shows:
            movie_id = str(show.get("movieId", ""))
            movie = movies.get(movie_id, {})

            movie_title = show.get("name", "").strip()
            if not movie_title:
                continue

            beginning = show.get("beginning", {})
            iso_full = beginning.get("isoFull")
            if not iso_full:
                continue

            try:
                screening_date = datetime.fromisoformat(iso_full)
            except (ValueError, TypeError):
                continue

            production_year = None
            released = movie.get("released", "")
            if released:
                year_match = re.search(r"(\d{4})", released)
                if year_match:
                    production_year = int(year_match.group(1))

            runtime = show.get("duration", 0) or movie.get("duration", 0) or 0

            poster_url = movie.get("largeImage")

            original_title = movie.get("title_orig") or None

            clean_title = _clean_movie_title(movie_title)

            screenings.append(
                Screening(
                    cinema_name=self.cinema_name,
                    movie_title=clean_title,
                    date=screening_date,
                    url=self.url,
                    poster_url=poster_url,
                    runtime=runtime,
                    production_year=production_year,
                    original_title=original_title,
                )
            )

        return screenings
