import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import yaml
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from yaml import Loader

from scrapers.babylon import BabylonScraper
from scrapers.base import BaseScraper, Screening
from scrapers.bestofcinema import BestOfCinemaScraper
from scrapers.zoo_palast import AstorScraper, ZooPalastScraper
from services.newsletter import NewsletterGenerator
from services.tmdb import TMDBService

# Load .env file if it exists (TMDB_API_KEY, etc.)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "babylon": BabylonScraper,
    "zoo_palast": ZooPalastScraper,
    "astor": AstorScraper,
    "bestofcinema": BestOfCinemaScraper,
}


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_scraper(
    cinema_config: dict,
    tmdb_service: Optional[TMDBService] = None,
    page=None,
    threshold_year: int = 2010,
) -> Optional[BaseScraper]:
    cinema_type = cinema_config.get("type")
    scraper_class = SCRAPER_MAP.get(cinema_type)

    if not scraper_class:
        logger.warning(f"No scraper found for type: {cinema_type}")
        return None

    kwargs = {
        "cinema_name": cinema_config["name"],
        "url": cinema_config["url"],
        "threshold_year": threshold_year,
    }

    if cinema_type in ("babylon", "bestofcinema") and tmdb_service:
        kwargs["tmdb_service"] = tmdb_service
    if cinema_type in ("zoo_palast", "astor") and page:
        kwargs["page"] = page

    return scraper_class(**kwargs)


def filter_screenings(
    screenings: list[Screening], title_filters: list[str]
) -> list[Screening]:
    if not title_filters:
        return screenings
    filtered = []
    for screening in screenings:
        should_filter = any(
            filter_str.lower() in screening.movie_title.lower()
            for filter_str in title_filters
        )
        if not should_filter:
            filtered.append(screening)
    return filtered


def filter_no_tmdb(screenings: list[Screening]) -> list[Screening]:
    return [s for s in screenings if s.tmdb_url]


async def _check_image_accessible(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.head(url)
            return response.status_code == 200
    except Exception:
        return False


async def _validate_and_fix_posters(
    screenings: list[Screening], tmdb_service: TMDBService
) -> list[Screening]:
    fixed = 0
    for screening in screenings:
        if not screening.poster_url:
            continue
        if not await _check_image_accessible(screening.poster_url):
            logger.info(f"Stale poster for '{screening.movie_title}', re-fetching...")
            info = await tmdb_service.get_movie_info(screening.movie_title)
            if info and info[2]:
                screening.poster_url = info[2]
                fixed += 1
                logger.info(f"  Fixed: {screening.poster_url}")
            else:
                screening.poster_url = None
                logger.warning(f"  Could not fix poster for '{screening.movie_title}'")
    if fixed:
        logger.info(f"Fixed {fixed} stale poster(s)")
    return screenings


async def enrich_screenings(
    screenings: list[Screening],
    tmdb_service: TMDBService,
    skip_if_enriched: bool = False,
) -> list[Screening]:
    async def enrich_one(screening: Screening) -> Screening:
        should_skip = skip_if_enriched and screening.tmdb_url
        if should_skip:
            return screening

        keep_original_title = tmdb_service._is_multi_part_title(
            screening.movie_title
        )
        info = await tmdb_service.get_movie_info(
            screening.movie_title, keep_original_title=keep_original_title
        )
        if info:
            tmdb_title, tmdb_year, tmdb_poster, tmdb_url, runtime = info
            if not keep_original_title and tmdb_title:
                screening.movie_title = tmdb_title
            if tmdb_year:
                screening.year = tmdb_year
            if tmdb_poster:
                screening.poster_url = tmdb_poster
            if tmdb_url:
                screening.tmdb_url = tmdb_url
            if runtime:
                screening.runtime = runtime
        if not screening.runtime:
            screening.runtime = 90
        return screening

    tasks = [enrich_one(s) for s in screenings]
    results = await asyncio.gather(*tasks)
    return list(results)


CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "screenings.json"


def _cleanup_old_newsletters(output_dir: str) -> None:
    output_path = Path(output_dir)
    if not output_path.exists():
        return

    newsletter_files = sorted(output_path.glob("newsletter_*.html"), reverse=True)
    if len(newsletter_files) > 1:
        for old_file in newsletter_files[1:]:
            old_file.unlink()
            logger.info(f"Removed old newsletter: {old_file.name}")


def save_screenings_to_cache(screenings: list[Screening]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    data = []
    for s in screenings:
        data.append(
            {
                "cinema_name": s.cinema_name,
                "movie_title": s.movie_title,
                "date": s.date.isoformat(),
                "url": s.url,
                "year": s.year,
                "poster_url": s.poster_url,
                "tmdb_url": s.tmdb_url,
                "runtime": s.runtime,
                "skip_year_filter": s.skip_year_filter,
            }
        )
    CACHE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"Saved {len(screenings)} screenings to cache")


def load_screenings_from_cache() -> Optional[list[Screening]]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        screenings = []
        for item in data:
            screenings.append(
                Screening(
                    cinema_name=item["cinema_name"],
                    movie_title=item["movie_title"],
                    date=datetime.fromisoformat(item["date"]),
                    url=item.get("url"),
                    year=item.get("year"),
                    poster_url=item.get("poster_url"),
                    tmdb_url=item.get("tmdb_url"),
                    runtime=item.get("runtime"),
                    skip_year_filter=item.get("skip_year_filter", False),
                )
            )
        logger.info(f"Loaded {len(screenings)} screenings from cache")
        return screenings
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


async def scrape_cinema(cinema, tmdb_service, context, threshold_year: int = 2010):
    page = await context.new_page()
    scraper = get_scraper(cinema, tmdb_service, page, threshold_year)
    if not scraper:
        await page.close()
        return []

    logger.info(f"Scraping {cinema['name']}...")
    try:
        screenings = await scraper.get_screenings()
        logger.info(f"Found {len(screenings)} screenings at {cinema['name']}")

        title_filters = cinema.get("title_filters", [])
        screenings = filter_screenings(screenings, title_filters)
        logger.info(f"After filtering: {len(screenings)} screenings")

        skip_enriched = cinema.get("type") in ("babylon", "bestofcinema")
        screenings = await enrich_screenings(
            screenings, tmdb_service, skip_if_enriched=skip_enriched
        )
        screenings = filter_no_tmdb(screenings)
        logger.info(f"After TMDB filter: {len(screenings)} screenings")
        return screenings
    except Exception as e:
        logger.error(f"Error scraping {cinema['name']}: {e}")
        return []
    finally:
        await page.close()


async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-cache", action="store_true", help="Force fresh scraping, ignore cache"
    )
    args = parser.parse_args()

    logger.info("Starting Berlin Classics Newsletter generation")

    config = load_config()
    threshold = config.get("newsletter", {}).get("classical_year_threshold", 2010)

    tmdb_config = config.get("tmdb", {})
    language = tmdb_config.get("language", "de-DE")
    api_key = os.environ.get("TMDB_API_KEY", "")

    if not api_key:
        logger.error(
            "TMDB_API_KEY environment variable is not set. "
            "Copy .env.example to .env and add your API key."
        )
        return

    tmdb_service = TMDBService(api_key=api_key, language=language)

    all_screenings = []

    if not args.no_cache:
        cached = load_screenings_from_cache()
        if cached:
            all_screenings = cached
            logger.info(f"Using {len(all_screenings)} screenings from cache")
            all_screenings = await _validate_and_fix_posters(
                all_screenings, tmdb_service
            )

    if not all_screenings:
        logger.info("Cache not found or disabled, scraping fresh...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            tasks = [
                scrape_cinema(cinema, tmdb_service, context, threshold)
                for cinema in config.get("cinemas", [])
            ]
            results = await asyncio.gather(*tasks)
            for screenings in results:
                all_screenings.extend(screenings)

            await browser.close()

    if all_screenings:
        save_screenings_to_cache(all_screenings)

    # Clean up old newsletters before generating a new one
    _cleanup_old_newsletters(output_dir)

    all_screenings.sort(key=lambda s: s.date)

    output_config = config.get("output", {})
    output_dir = output_config.get("directory", "output")
    filename_template = output_config.get("filename_template", "newsletter_{date}.html")

    today = datetime.now().strftime("%Y-%m-%d")
    output_filename = filename_template.format(date=today)
    output_path = Path(output_dir) / output_filename

    cinema_config = {"cinemas": []}
    for cinema in config.get("cinemas", []):
        cinema_config["cinemas"].append(
            {
                "name": cinema["name"],
                "url": cinema["url"],
                "google_maps_url": cinema.get("google_maps_url"),
            }
        )

    generator = NewsletterGenerator()
    generator.generate(
        screenings=all_screenings,
        output_path=str(output_path),
        threshold_year=threshold,
        cinema_config=cinema_config,
    )

    logger.info(f"Newsletter generated with {len(all_screenings)} screenings")


if __name__ == "__main__":
    asyncio.run(main_async())
