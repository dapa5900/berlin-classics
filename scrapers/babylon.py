import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper, Screening

logger = logging.getLogger(__name__)

# Override mappings for festival categories where the display name
# does not match the actual title prefix on the page.
FESTIVAL_PREFIX_OVERRIDES = {
    "cat-DEFA-80": "80 Jahre DEFA: ",
}


def _strip_festival_prefix(movie_title: str, event) -> str:
    cat_classes_raw = event.get("class", "")
    if isinstance(cat_classes_raw, list):
        cat_classes_raw = " ".join(cat_classes_raw)
    cat_classes = [c for c in cat_classes_raw.split() if c.startswith("cat-")]
    if not cat_classes:
        return movie_title
    cat_slug = cat_classes[0]

    # Explicit overrides first
    if cat_slug in FESTIVAL_PREFIX_OVERRIDES:
        prefix = FESTIVAL_PREFIX_OVERRIDES[cat_slug]
        if movie_title.lower().startswith(prefix.lower()):
            return movie_title[len(prefix):].strip()
        return movie_title

    # Auto-detect for festival sections using the category link URL
    cat_link = event.select_one(".mix-category a")
    if not cat_link:
        return movie_title
    cat_url = cat_link.get("href", "")

    if "/festivals/" not in cat_url:
        return movie_title

    cat_name = cat_link.get_text(strip=True)
    if ": " in cat_name:
        prefix = cat_name.split(":")[0].strip() + ": "
    else:
        prefix = cat_name.strip() + ": "

    if movie_title.lower().startswith(prefix.lower()):
        return movie_title[len(prefix):].strip()
    return movie_title


class BabylonScraper(BaseScraper):
    def __init__(
        self,
        cinema_name: str,
        url: str,
    ):
        super().__init__(cinema_name, url)

    async def get_screenings(self) -> list[Screening]:
        soup = await self.fetch_page(self.url)
        screenings = []

        for event in soup.select(".mix"):
            title_elem = event.select_one(".right-mix .mix-title")
            if not title_elem:
                title_elem = event.select_one(".mix-title")

            date_elem = event.select_one(".right-mix .mix-date")
            if not date_elem:
                date_elem = event.select_one(".mix-date")

            link_elem = event.select_one("a")
            img_elem = event.select_one("img")

            if not title_elem or not date_elem:
                continue

            movie_title = title_elem.get_text(strip=True)
            if not movie_title:
                movie_title = event.get("data-title", "")
            movie_title = _strip_festival_prefix(movie_title, event)

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

            introtext_elem = event.select_one(".mix-introtext")
            production_year = None
            original_title = None
            if introtext_elem:
                introtext = introtext_elem.get_text(strip=True)

                year_match = re.search(r",\s*(\d{4})", introtext)
                if year_match:
                    production_year = int(year_match.group(1))

                if not production_year:
                    year_matches = re.finditer(
                        r"\b(18\d{2}|19\d{2}|20\d{2})\b", introtext
                    )
                    for m in year_matches:
                        potential_year = int(m.group(1))
                        after_match = introtext[m.end() : m.end() + 10]
                        if "Min" not in after_match and "min" not in after_match:
                            production_year = potential_year
                            break

                bracket_contents = re.findall(r"\[([^\]]+)\]", introtext)
                for content in bracket_contents:
                    content_clean = content.strip()
                    if content_clean.lower() not in [
                        "omeu",
                        "omu",
                        "ov",
                        "df",
                        "english ov",
                    ]:
                        original_title = content_clean
                        break

            runtime_elem = event.select_one(".right-mix .runtime")
            runtime = 0
            if runtime_elem:
                runtime_text = runtime_elem.get_text(strip=True)
                runtime_match = re.search(r"(\d+)", runtime_text)
                if runtime_match:
                    runtime = int(runtime_match.group(1))

            screenings.append(
                Screening(
                    cinema_name=self.cinema_name,
                    movie_title=movie_title,
                    date=screening_date,
                    url=url,
                    poster_url=poster_url,
                    runtime=runtime,
                    production_year=production_year,
                    original_title=original_title,
                )
            )

        return screenings
