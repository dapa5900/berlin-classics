import asyncio
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
        self._request_semaphore = asyncio.Semaphore(5)

    async def _request_tmdb(
        self, url: str, params: dict, max_retries: int = 3
    ) -> httpx.Response:
        for attempt in range(max_retries):
            async with self._request_semaphore:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 429 and attempt < max_retries - 1:
                        pass
                    else:
                        response.raise_for_status()
                        return response
            if response.status_code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"TMDB 429 on {url.rsplit('/', 1)[-1]}, "
                    f"retry {attempt + 1}/{max_retries} in {wait}s"
                )
                await asyncio.sleep(wait)
        raise httpx.HTTPStatusError(
            f"429 Too Many Requests after {max_retries} retries",
            request=None,
            response=response,
        )

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

    def _any_title_matches(self, movie: dict, search_title: str) -> bool:
        s = search_title.lower().strip()
        return (
            movie.get("title", "").lower().strip() == s
            or movie.get("original_title", "").lower().strip() == s
        )

    def _best_title_similarity(self, movie: dict, search_title: str) -> float:
        sim_title = self._calculate_title_similarity(
            search_title, movie.get("title", "")
        )
        sim_original = self._calculate_title_similarity(
            search_title, movie.get("original_title", "")
        )
        return max(sim_title, sim_original)

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
        cleaned = re.sub(
            r"^[^:]+?am\s+(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag):\s*",
            "", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"VIETNAM:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"THREE AMIGOS:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"INDOGERMAN FILMWEEK:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"SPECIAL:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(Klimareihe|OPEN AIR|OFFENE LEINWAND|REEL LOVE):\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"MONDO VIDEO\s+(?:I+V?):\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\[.*?\]", "", cleaned)
        cleaned = re.sub(r"\s*with\s+Guests.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    async def _get_movie_runtime(self, tmdb_id: int) -> Optional[int]:
        try:
            details_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            params = {"api_key": self.api_key}
            response = await self._request_tmdb(details_url, params)
            data = response.json()
            return data.get("runtime")
        except Exception as e:
            logger.error(f"Error getting runtime for TMDB ID {tmdb_id}: {e}")
            return None

    async def _pick_by_runtime(
        self, candidates: list, scraped_runtime: int
    ) -> Optional[dict]:
        if not scraped_runtime or len(candidates) <= 1:
            return candidates[0] if candidates else None
        tasks = [self._get_movie_runtime(m["id"]) for m in candidates]
        runtimes = await asyncio.gather(*tasks)
        scored = [
            (abs(scraped_runtime - r), m)
            for m, r in zip(candidates, runtimes)
            if r
        ]
        if scored:
            scored.sort(key=lambda x: x[0])
            logger.info(
                f"  Runtime match: '{scored[0][1].get('title')}' "
                f"(diff={scored[0][0]} min) from {len(candidates)} candidates"
            )
            return scored[0][1]
        return candidates[0]

    async def get_movie_info(
        self,
        movie_title: str,
        expected_year: Optional[int] = None,
        keep_original_title: bool = False,
        original_title: Optional[str] = None,
        scraped_runtime: int = 0,
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
                    orig_response = await self._request_tmdb(search_url, orig_params)
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
                # Gather results from all languages
                all_results = []
                for lang in languages_to_try:
                    params = {
                        "api_key": self.api_key,
                        "query": cleaned_title,
                        "language": lang,
                    }
                    response = await self._request_tmdb(search_url, params)
                    data = response.json()
                    if data.get("results"):
                        all_results.extend(data["results"])

                if all_results:
                    # Deduplicate by TMDB ID
                    seen_ids = set()
                    results = []
                    for m in all_results:
                        mid = m.get("id")
                        if mid and mid not in seen_ids:
                            seen_ids.add(mid)
                            results.append(m)

                    if expected_year is not None:
                        matched_movie = None

                        # 1. Exact title + exact year match (strongest signal)
                        candidates = [
                            m
                            for m in results
                            if self._any_title_matches(m, cleaned_title)
                            and m.get("release_date", "")[:4]
                            and int(m.get("release_date", "")[:4]) == expected_year
                        ]
                        if candidates:
                            matched_movie = (
                                candidates[0]
                                if len(candidates) == 1
                                else await self._pick_by_runtime(
                                    candidates, scraped_runtime
                                )
                            )
                            logger.info(
                                f"  MATCH (exact title + year): "
                                f"{matched_movie.get('title')} "
                                f"({matched_movie.get('release_date', '')[:4]})"
                            )

                        # 2. Exact title match (within ±3 years of expected_year)
                        if not matched_movie:
                            candidates = [
                                m
                                for m in results
                                if self._any_title_matches(m, cleaned_title)
                                and m.get("release_date", "")[:4]
                                and abs(
                                    int(m.get("release_date", "")[:4])
                                    - expected_year
                                )
                                <= 3
                            ]
                            if candidates:
                                matched_movie = (
                                    candidates[0]
                                    if len(candidates) == 1
                                    else await self._pick_by_runtime(
                                        candidates, scraped_runtime
                                    )
                                )
                                logger.info(
                                    f"  MATCH (exact title): "
                                    f"{matched_movie.get('title')} "
                                    f"({matched_movie.get('release_date', '')[:4]}), "
                                    f"year_diff="
                                    f"{abs(int(matched_movie.get('release_date', '')[:4]) - expected_year)}"
                                )

                        # 3. Exact year match
                        if not matched_movie:
                            for m in results:
                                release_date = m.get("release_date", "")
                                year = (
                                    int(release_date[:4]) if release_date else None
                                )
                                if year == expected_year:
                                    matched_movie = m
                                    break

                        # 4. Extended year match (±3 years, similarity threshold)
                        if not matched_movie:
                            for m in results:
                                release_date = m.get("release_date", "")
                                year = (
                                    int(release_date[:4]) if release_date else None
                                )
                                title_similarity = (
                                    self._best_title_similarity(
                                        m, cleaned_title
                                    )
                                )
                                if (
                                    year
                                    and abs(year - expected_year) <= 3
                                    and title_similarity >= 0.8
                                ):
                                    matched_movie = m
                                    logger.info(
                                        f"  MATCH (±3yr): {m.get('title')} ({year}), "
                                        f"similarity={title_similarity:.2f}, "
                                        f"year_diff={abs(year - expected_year)}"
                                    )
                                    break

                        # 5. Similarity/Year fallback
                        if not matched_movie:
                            for m in results:
                                release_date = m.get("release_date", "")
                                year = (
                                    int(release_date[:4]) if release_date else None
                                )
                                title_similarity = (
                                    self._best_title_similarity(
                                        m, cleaned_title
                                    )
                                )
                                if (
                                    year
                                    and abs(year - expected_year) <= 2
                                    and title_similarity >= 0.5
                                ):
                                    matched_movie = m
                                    break

                        # 6. Best similarity fallback
                        if not matched_movie:
                            best_match = None
                            best_similarity = 0
                            best_year_diff = float("inf")

                            for m in results:
                                release_date = m.get("release_date", "")
                                year = (
                                    int(release_date[:4]) if release_date else None
                                )
                                title_similarity = (
                                    self._best_title_similarity(
                                        m, cleaned_title
                                    )
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
                            if best_match:
                                matched_movie = best_match

                        if matched_movie:
                            movie = matched_movie
                    else:
                        # No year hint — search all languages and combine results
                        exact_matches = [
                            m
                            for m in results
                            if self._any_title_matches(m, cleaned_title)
                        ]
                        if exact_matches:
                            if len(exact_matches) > 1 and scraped_runtime:
                                movie = await self._pick_by_runtime(
                                    exact_matches, scraped_runtime
                                )
                            else:
                                movie = max(
                                    exact_matches,
                                    key=lambda x: x.get("popularity", 0) or 0,
                                )
                        else:
                            movie = max(
                                results,
                                key=lambda m: self._best_title_similarity(
                                    m, cleaned_title
                                ),
                            ) or results[0]

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
