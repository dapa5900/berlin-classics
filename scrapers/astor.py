import locale
import re
from datetime import datetime

from scrapers.base import BaseScraper, Screening

try:
    locale.setlocale(locale.LC_TIME, "German")
except locale.Error:
    pass


class AstorScraper(BaseScraper):
    def get_screenings(self) -> list[Screening]:
        soup = self.fetch_page_js(self.url)
        text = soup.get_text()
        screenings = []

        day_map = {
            "Mo": "Montag",
            "Di": "Dienstag",
            "Mi": "Mittwoch",
            "Do": "Donnerstag",
            "Fr": "Freitag",
            "Sa": "Samstag",
            "So": "Sonntag",
        }

        date_pattern = r"([A-Za-z]+)\.?\s*(\d+)\.(\d+)\.?"
        date_matches = list(re.finditer(date_pattern, text))

        for i, match in enumerate(date_matches):
            day_abbr = match.group(1)
            day_num = match.group(2)
            month = match.group(3)

            full_day = day_map.get(day_abbr, day_abbr)
            year = datetime.now().year

            date_str = f"{full_day} {day_num}.{month}.{year}"

            try:
                screening_date = datetime.strptime(date_str, "%A %d.%m.%Y")
            except ValueError:
                continue

            if i + 1 < len(date_matches):
                next_pos = date_matches[i + 1].start()
                section = text[match.end() : next_pos]
            else:
                section = text[match.end() : match.end() + 800]

            match_time = re.search(r"(\d{2}):(\d{2})", section)
            if match_time:
                hour = int(match_time.group(1))
                minute = int(match_time.group(2))
                screening_date = screening_date.replace(hour=hour, minute=minute)

            movie_title = None

            action_match = re.search(r"\| Action (.+)", section)
            if action_match:
                content = action_match.group(1).strip()
                movie_title = content.split("Minuten")[0].strip()
                movie_title = movie_title.split("  ")[0].strip()

            if not movie_title:
                genre_match = re.search(
                    r"\| (?:Drama|Western|Komöde|Thriller|Horror) (.+)", section
                )
                if genre_match:
                    content = genre_match.group(1).strip()
                    movie_title = content.split("Minuten")[0].strip()
                    movie_title = movie_title.split("  ")[0].strip()

            if movie_title and len(movie_title) > 2:
                if len(movie_title) > 100:
                    movie_title = movie_title[:100].rsplit(" ", 1)[0]

                screenings.append(
                    Screening(
                        cinema_name=self.cinema_name,
                        movie_title=movie_title,
                        date=screening_date,
                        url=self.url,
                    )
                )

        return screenings
