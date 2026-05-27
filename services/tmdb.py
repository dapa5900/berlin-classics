import logging
import re
import unicodedata
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class TMDBService:
    def __init__(self, api_key: str, language: str = "de-DE"):
        self.api_key = api_key
        self.language = language
        self._cache: dict[str, Optional[Tuple[str, int, str, str, int]]] = {}

    def _is_multi_part_title(self, title: str) -> bool:
        keywords = ["trilogie", "trilogy", "marathon", r"\d+-hour", r"\d{1,2}\s*hour"]
        title_lower = title.lower()
        return any(re.search(kw, title_lower) for kw in keywords)

    def _extract_base_title(self, title: str) -> str:
        cleaned = re.sub(r"\s*\[.*?\]", "", title)
        cleaned = re.sub(r"\s*trilogie\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*trilogy\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*trilogy\s+.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*part\s*\d+.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*marathon\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*marathon\s+.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"24.?hour\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\d+-hour\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        title1 = title1.lower().strip()
        title2 = title2.lower().strip()

        if title1 == title2:
            return 1.0

        if title1 in title2 or title2 in title1:
            return 0.8

        common_words = set(title1.split()) & set(title2.split())
        if common_words:
            max_len = max(len(title1.split()), len(title2.split()))
            return len(common_words) / max_len if max_len > 0 else 0

        return 0.0

    def _clean_title(self, title: str) -> str:
        cleaned = unicodedata.normalize("NFD", title)
        cleaned = "".join(c for c in cleaned if not unicodedata.combining(c))
        cleaned = re.sub(r"\s*\(.*?\)\s*", " ", cleaned)
        cleaned = re.sub(r"\s*LIVE\s*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(?<=\s)-\s.*$", "", cleaned)
        cleaned = re.sub(r"\s*Babylon\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Greek Film Festival:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Unsere Besten:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Clockwork Kubrick:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"Stummfilm um Mitternacht:\s*", "", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"CinemAperitivo:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Kinderwagenkino:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"MoMo Berlin:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"Modern Times\s*.*$", "Modern Times", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r"City Lights\s*.*$", "City Lights", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"Free Friday:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Juliette Binoche:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Luchino Visconti:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Achtung Berlin:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Cicle Gaudí:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"80 Jahre DEFA:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"VIETNAM:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"THREE AMIGOS:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"INDOGERMAN FILMWEEK:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\[.*?\]", "", cleaned)
        cleaned = re.sub(r"\s*with\s+Guests.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    async def _get_movie_runtime(self, tmdb_id: int) -> Optional[int]:
        try:
            details_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": self.api_key}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(details_url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("runtime")
        except Exception as e:
            logger.error(f"Error getting runtime for TMDB ID {tmdb_id}: {e}")
            return None

    async def get_movie_info(
        self,
        movie_title: str,
        expected_year: Optional[int] = None,
        keep_original_title: bool = False,
        original_title: Optional[str] = None,
    ) -> Optional[Tuple[str, int, str, str, int]]:
        cache_key = (
            f"{movie_title}|{expected_year}|{keep_original_title}|{original_title}"
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.api_key:
            logger.warning("TMDB API key not configured")
            return None

        cleaned_title = self._clean_title(movie_title)

        if self._is_multi_part_title(movie_title):
            base_title = self._extract_base_title(movie_title)
            cleaned_title = self._clean_title(base_title)

        try:
            search_url = "https://api.themoviedb.org/3/search/movie"
            languages_to_try = [self.language, "en-US"]

            movie = None

            # --- PREFER ORIGINAL TITLE SEARCH ---
            if original_title and expected_year:
                original_cleaned = self._clean_title(original_title)
                logger.info(
                    f"Trying prioritized original title search: '{original_cleaned}' for year {expected_year}"
                )
                for orig_lang in languages_to_try:
                    orig_params = {
                        "api_key": self.api_key,
                        "query": original_cleaned,
                        "language": orig_lang,
                    }
                    async with httpx.AsyncClient(timeout=10) as client:
                        orig_response = await client.get(search_url, params=orig_params)
                    orig_response.raise_for_status()
                    orig_data = orig_response.json()

                    if not orig_data.get("results"):
                        continue

                    for m in orig_data["results"]:
                        release_date = m.get("release_date", "")
                        year = int(release_date[:4]) if release_date else None
                        if year == expected_year:
                            movie = m
                            logger.info(
                                f"  FOUND via prioritized original title: {m.get('title')} ({year})"
                            )
                            break
                    if movie:
                        break

            # --- FALLBACK TO MAIN SEARCH ---
            if not movie:
                for lang in languages_to_try:
                    params = {
                        "api_key": self.api_key,
                        "query": cleaned_title,
                        "language": lang,
                    }
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(search_url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if not data.get("results"):
                        continue

                    results = data["results"]

                    matched_movie = None
                    if expected_year is not None:
                        # 1. Exact year match
                        for m in results:
                            release_date = m.get("release_date", "")
                            year = int(release_date[:4]) if release_date else None
                            if year == expected_year:
                                matched_movie = m
                                break

                        # 1.5. Extended year match (±3 years, lower similarity threshold)
                        if not matched_movie:
                            for m in results:
                                release_date = m.get("release_date", "")
                                year = int(release_date[:4]) if release_date else None
                                tmdb_title = m.get("title", "")
                                title_similarity = self._calculate_title_similarity(
                                    cleaned_title, tmdb_title
                                )
                                if (
                                    year
                                    and abs(year - expected_year) <= 3
                                    and title_similarity >= 0.3
                                ):
                                    matched_movie = m
                                    logger.info(
                                        f"  MATCH (±3yr): {tmdb_title} ({year}), "
                                        f"similarity={title_similarity:.2f}, "
                                        f"year_diff={abs(year - expected_year)}"
                                    )
                                    break

                        # 2. Similarity/Year fallback
                        if not matched_movie:
                            for m in results:
                                release_date = m.get("release_date", "")
                                year = int(release_date[:4]) if release_date else None
                                tmdb_title = m.get("title", "")
                                title_similarity = self._calculate_title_similarity(
                                    cleaned_title, tmdb_title
                                )
                                if (
                                    year
                                    and abs(year - expected_year) <= 2
                                    and title_similarity >= 0.5
                                ):
                                    matched_movie = m
                                    break

                        # 3. Best Similarity fallback
                        if not matched_movie:
                            best_match = None
                            best_similarity = 0
                            best_year_diff = float("inf")

                            for m in results:
                                release_date = m.get("release_date", "")
                                year = int(release_date[:4]) if release_date else None
                                tmdb_title = m.get("title", "")
                                title_similarity = self._calculate_title_similarity(
                                    cleaned_title, tmdb_title
                                )

                                if title_similarity >= 0.7:
                                    if year and expected_year:
                                        year_diff = abs(year - expected_year)
                                        if year_diff < best_year_diff:
                                            best_year_diff = year_diff
                                            best_similarity = title_similarity
                                            best_match = m
                                    elif title_similarity > best_similarity:
                                        best_similarity = title_similarity
                                        best_match = m
                            matched_movie = best_match

                        if matched_movie:
                            movie = matched_movie
                    else:
                        movie = results[0]

                    if movie:
                        break

            if not movie:
                logger.warning(
                    f"Could not find TMDB match for '{movie_title}' (year {expected_year})"
                )
                self._cache[cache_key] = None
                return None

            full_title = movie.get("title", movie_title)
            release_date = movie.get("release_date", "")
            year = int(release_date[:4]) if release_date else None
            poster_path = movie.get("poster_path")
            poster_url = (
                f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            )
            tmdb_id = movie.get("id")
            tmdb_url = (
                f"https://www.themoviedb.org/movie/{tmdb_id}" if tmdb_id else None
            )

            runtime = movie.get("runtime")
            if not runtime and tmdb_id:
                runtime = await self._get_movie_runtime(tmdb_id)

            result = (full_title, year, poster_url, tmdb_url, runtime)
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Error looking up TMDB for '{movie_title}': {e}")

        self._cache[cache_key] = None
        return None
