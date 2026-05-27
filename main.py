import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from scrapers.babylon import BabylonScraper
from scrapers.base import BaseScraper, Screening
from scrapers.bestofcinema import BestOfCinemaScraper
from scrapers.filmrausch import FilmrauschScraper
from scrapers.openair_kino import OpenAirKinoScraper
from scrapers.zoo_palast import ZooPalastScraper
from services.newsletter import NewsletterGenerator
from services.tmdb import TMDBService

load_dotenv()

LOG_DIR = Path("logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
LOG_DIR.mkdir(exist_ok=True)
file_handler = logging.FileHandler(
    str(LOG_DIR / "latest_run.log"), mode="w", encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "babylon": BabylonScraper,
    "zoo_palast": ZooPalastScraper,
    "bestofcinema": BestOfCinemaScraper,
    "openair_kino": OpenAirKinoScraper,
    "filmrausch": FilmrauschScraper,
}


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_scraper(cinema_config: dict, page=None) -> Optional[BaseScraper]:
    cinema_type = cinema_config.get("type")
    scraper_class = SCRAPER_MAP.get(cinema_type)
    if not scraper_class:
        logger.warning(f"No scraper found for type: {cinema_type}")
        return None
    kwargs = {
        "cinema_name": cinema_config["name"],
        "url": cinema_config["url"],
    }
    if cinema_type == "zoo_palast" and page:
        kwargs["page"] = page
    return scraper_class(**kwargs)


def filter_no_tmdb(screenings: list[Screening]) -> list[Screening]:
    return [s for s in screenings if s.tmdb_url]


async def enrich_screenings(
    screenings: list[Screening],
    tmdb_service: TMDBService,
) -> list[Screening]:
    groups: dict[tuple, list[Screening]] = {}
    for s in screenings:
        key = (s.movie_title, s.production_year, s.original_title)
        groups.setdefault(key, []).append(s)

    async def enrich_group(group: list[Screening]) -> None:
        s = group[0]
        keep_original_title = tmdb_service._is_multi_part_title(s.movie_title)
        info = await tmdb_service.get_movie_info(
            s.movie_title,
            expected_year=s.production_year,
            keep_original_title=keep_original_title,
            original_title=s.original_title,
        )
        if info:
            tmdb_title, tmdb_year, tmdb_poster, tmdb_url, runtime = info
            for member in group:
                if not keep_original_title and tmdb_title:
                    member.movie_title = tmdb_title
                if tmdb_year:
                    member.year = tmdb_year
                if tmdb_poster:
                    member.poster_url = tmdb_poster
                if tmdb_url:
                    member.tmdb_url = tmdb_url
                if runtime:
                    member.runtime = runtime
                if not member.runtime:
                    member.runtime = 90
        else:
            for member in group:
                if not member.runtime:
                    member.runtime = 90

    tasks = [enrich_group(group) for group in groups.values()]
    await asyncio.gather(*tasks)
    return screenings


CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "screenings.json"
CACHE_ENRICHED_FILE = CACHE_DIR / "screenings_enriched.json"


def _cleanup_old_newsletters(output_dir: str) -> None:
    output_path = Path(output_dir)
    if not output_path.exists():
        return
    for old_file in output_path.glob("newsletter_*.html"):
        old_file.unlink()
        logger.info(f"Removed old newsletter: {old_file.name}")


def save_screenings_to_cache(screenings: list[Screening]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    data = []
    for s in screenings:
        data.append({
            "cinema_name": s.cinema_name,
            "movie_title": s.movie_title,
            "date": s.date.isoformat(),
            "url": s.url,
            "year": s.year,
            "poster_url": s.poster_url,
            "tmdb_url": s.tmdb_url,
            "runtime": s.runtime,
            "skip_year_filter": s.skip_year_filter,
            "production_year": s.production_year,
            "venue_name": s.venue_name,
            "original_title": s.original_title,
        })
    CACHE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"Saved {len(screenings)} raw screenings to cache")


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
                    production_year=item.get("production_year"),
                    venue_name=item.get("venue_name"),
                    original_title=item.get("original_title"),
                )
            )
        logger.info(f"Loaded {len(screenings)} raw screenings from cache")
        return screenings
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def save_enriched_cache(screenings: list[Screening]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    data = []
    for s in screenings:
        data.append({
            "cinema_name": s.cinema_name,
            "movie_title": s.movie_title,
            "date": s.date.isoformat(),
            "url": s.url,
            "year": s.year,
            "poster_url": s.poster_url,
            "tmdb_url": s.tmdb_url,
            "runtime": s.runtime,
            "skip_year_filter": s.skip_year_filter,
            "production_year": s.production_year,
            "venue_name": s.venue_name,
            "original_title": s.original_title,
        })
    CACHE_ENRICHED_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"Saved {len(screenings)} enriched screenings to cache")


def load_enriched_cache() -> Optional[list[Screening]]:
    if not CACHE_ENRICHED_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_ENRICHED_FILE.read_text(encoding="utf-8"))
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
                    production_year=item.get("production_year"),
                    venue_name=item.get("venue_name"),
                    original_title=item.get("original_title"),
                )
            )
        logger.info(f"Loaded {len(screenings)} enriched screenings from cache")
        return screenings
    except Exception as e:
        logger.warning(f"Failed to load enriched cache: {e}")
        return None


async def scrape_cinema(cinema, context) -> list[Screening]:
    page = await context.new_page()
    scraper = get_scraper(cinema, page)
    if not scraper:
        await page.close()
        return []
    logger.info(f"Scraping {cinema['name']}...")
    try:
        screenings = await scraper.get_screenings()
        logger.info(f"Found {len(screenings)} screenings at {cinema['name']}")
        return screenings
    except Exception as e:
        logger.error(f"Error scraping {cinema['name']}: {e}")
        return []
    finally:
        await page.close()


async def scrape_all_raw(cinemas, context) -> list[Screening]:
    tasks = [scrape_cinema(c, context) for c in cinemas]
    results = await asyncio.gather(*tasks)
    all_raw = []
    for r in results:
        all_raw.extend(r)
    return all_raw


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


def _apply_title_filters(
    screenings: list[Screening], config: dict
) -> list[Screening]:
    cinema_configs = config.get("cinemas", [])
    result = []
    for s in screenings:
        cinema_cfg = next((c for c in cinema_configs if c["name"] == s.cinema_name), None)
        cinema_filters = cinema_cfg.get("title_filters", []) if cinema_cfg else []
        if not any(f.lower() in s.movie_title.lower() for f in cinema_filters):
            result.append(s)
    return result


def _apply_year_filter(
    screenings: list[Screening], threshold_year: int
) -> list[Screening]:
    return [
        s for s in screenings
        if s.year is not None and (s.year <= threshold_year or s.skip_year_filter)
    ]


def _render_newsletter(
    screenings: list[Screening], config: dict, threshold_year: int
) -> None:
    output_config = config.get("output", {})
    output_dir = output_config.get("directory", "output")
    filename_template = output_config.get("filename_template", "newsletter_{date}.html")
    _cleanup_old_newsletters(output_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    output_filename = filename_template.format(date=today)
    output_path = Path(output_dir) / output_filename

    cinema_config = {"cinemas": []}
    for cinema in config.get("cinemas", []):
        cinema_config["cinemas"].append({
            "name": cinema["name"],
            "url": cinema["url"],
            "google_maps_url": cinema.get("google_maps_url"),
        })

    generator = NewsletterGenerator()
    generator.generate(
        screenings=screenings,
        output_path=str(output_path),
        threshold_year=threshold_year,
        cinema_config=cinema_config,
    )


async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-cache", action="store_true", help="Force fresh scrape, ignore cache"
    )
    parser.add_argument(
        "--re-enrich", action="store_true",
        help="Re-run TMDB enrichment on cached raw data (no scraping)"
    )
    parser.add_argument(
        "--cinema", type=str, default=None,
        help="Scrape only this cinema type (babylon, zoo_palast, bestofcinema, openair_kino, filmrausch)"
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Skip TMDB enrichment, use enriched cache (for iterating on title/year filters)"
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

    # --- Fast path: skip TMDB, use enriched cache ---
    if args.fast:
        logger.info("Fast mode: loading enriched cache...")
        enriched = load_enriched_cache()
        if not enriched:
            logger.error("No enriched cache found. Run without --fast first.")
            return
        filtered = _apply_title_filters(enriched, config)
        classical = _apply_year_filter(filtered, threshold)
        _render_newsletter(classical, config, threshold)
        logger.info(f"Newsletter generated with {len(classical)} screenings (fast)")
        return

    all_raw = []

    if args.re_enrich:
        logger.info("Re-enriching from cache...")
        cached = load_screenings_from_cache()
        if not cached:
            logger.error("No cached screenings found for re-enrichment")
            return
        all_raw = cached
        tmdb_service._cache.clear()
    elif args.cinema:
        cinema_type_to_name = {c["type"]: c["name"] for c in config.get("cinemas", [])}
        cinema_name = cinema_type_to_name.get(args.cinema, args.cinema)
        if not args.no_cache:
            cached = load_screenings_from_cache()
            if cached:
                all_raw = [s for s in cached if s.cinema_name != cinema_name]
                logger.info(f"Loaded {len(all_raw)} from cache (excluding {cinema_name})")
        cinemas_to_scrape = [c for c in config.get("cinemas", []) if c.get("type") == args.cinema]
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            scraped = await scrape_all_raw(cinemas_to_scrape, context)
            all_raw.extend(scraped)
            await browser.close()
    elif args.no_cache:
        logger.info("Cache disabled, scraping fresh...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            all_raw = await scrape_all_raw(config.get("cinemas", []), context)
            await browser.close()
    else:
        cached = load_screenings_from_cache()
        if cached:
            all_raw = cached
            logger.info(f"Using {len(all_raw)} raw screenings from cache")
        else:
            logger.info("No cache found, scraping fresh...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                all_raw = await scrape_all_raw(config.get("cinemas", []), context)
                await browser.close()

    if not all_raw:
        logger.warning("No screenings found")
        return

    save_screenings_to_cache(all_raw)

    filtered_raw = _apply_title_filters(all_raw, config)
    logger.info(f"After title filter: {len(filtered_raw)} screenings")

    enriched = await enrich_screenings(filtered_raw, tmdb_service)
    logger.info(f"After TMDB enrichment: {len(enriched)} screenings")

    with_tmdb = filter_no_tmdb(enriched)
    logger.info(f"After no-TMDB filter: {len(with_tmdb)} screenings")

    save_enriched_cache(with_tmdb)

    classical = _apply_year_filter(with_tmdb, threshold)
    logger.info(f"After year filter (≤{threshold}): {len(classical)} screenings")

    classical.sort(key=lambda s: s.date.replace(tzinfo=None))

    _render_newsletter(classical, config, threshold)

    logger.info(f"Newsletter generated with {len(classical)} screenings")


if __name__ == "__main__":
    asyncio.run(main_async())
