
from main import filter_screenings, filter_no_tmdb
from scrapers.base import Screening
from datetime import datetime


class TestFilterScreenings:
    """Tests for the title filter logic."""

    def _make_screening(self, title: str) -> Screening:
        return Screening(
            cinema_name="Test",
            movie_title=title,
            date=datetime(2026, 5, 20, 20, 0),
        )

    def test_no_filters_returns_all(self):
        screenings = [
            self._make_screening("Film A"),
            self._make_screening("Film B"),
        ]
        result = filter_screenings(screenings, [])
        assert len(result) == 2

    def test_filters_out_matching_titles(self):
        screenings = [
            self._make_screening("Film A"),
            self._make_screening("Horror Night"),
            self._make_screening("Film B"),
        ]
        result = filter_screenings(screenings, ["Horror"])
        assert len(result) == 2
        assert all("Horror" not in s.movie_title for s in result)

    def test_case_insensitive_filter(self):
        screenings = [
            self._make_screening("Film A"),
            self._make_screening("HORROR NIGHT"),
            self._make_screening("Film B"),
        ]
        result = filter_screenings(screenings, ["horror"])
        assert len(result) == 2

    def test_multiple_filters_any_match(self):
        screenings = [
            self._make_screening("Horror Night"),
            self._make_screening("Comedy Gold"),
            self._make_screening("Film B"),
        ]
        result = filter_screenings(screenings, ["Horror", "Comedy"])
        assert len(result) == 1
        assert result[0].movie_title == "Film B"

    def test_empty_title_not_filtered(self):
        screenings = [self._make_screening("")]
        result = filter_screenings(screenings, [])
        assert len(result) == 1


class TestFilterNoTmdb:
    """Tests for the TMDB filter logic."""

    def _make_screening(self, tmdb_url=None) -> Screening:
        return Screening(
            cinema_name="Test",
            movie_title="Film",
            date=datetime(2026, 5, 20, 20, 0),
            tmdb_url=tmdb_url,
        )

    def test_keeps_screenings_with_tmdb_url(self):
        screenings = [self._make_screening("https://www.themoviedb.org/movie/1")]
        result = filter_no_tmdb(screenings)
        assert len(result) == 1

    def test_removes_screenings_without_tmdb_url(self):
        screenings = [self._make_screening(None), self._make_screening("")]
        result = filter_no_tmdb(screenings)
        assert len(result) == 0

    def test_mixed_results(self):
        screenings = [
            self._make_screening("https://www.themoviedb.org/movie/1"),
            self._make_screening(None),
            self._make_screening("https://www.themoviedb.org/movie/2"),
        ]
        result = filter_no_tmdb(screenings)
        assert len(result) == 2
