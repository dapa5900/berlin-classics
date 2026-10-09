from datetime import datetime

import pytest

from scrapers.babylon import resolve_screening_date
from scrapers.openair_kino import resolve_openair_date
from services.tmdb import TMDBService


class TestBabylonYearRollover:
    """Year-less DD.MM. dates in the past belong to next year."""

    def test_future_date_stays_this_year(self):
        now = datetime(2026, 10, 9, 12, 0)
        result = resolve_screening_date("20", "10", "20:00", now)
        assert result == datetime(2026, 10, 20, 20, 0)

    def test_past_date_rolls_to_next_year(self):
        # December program already listing January dates
        now = datetime(2026, 12, 15, 12, 0)
        result = resolve_screening_date("10", "01", "20:00", now)
        assert result == datetime(2027, 1, 10, 20, 0)

    def test_same_day_stays_this_year(self):
        now = datetime(2026, 10, 9, 21, 0)
        result = resolve_screening_date("09", "10", "18:00", now)
        assert result == datetime(2026, 10, 9, 18, 0)

    def test_impossible_date_raises(self):
        now = datetime(2026, 10, 9, 12, 0)
        with pytest.raises(ValueError):
            resolve_screening_date("31", "02", "20:00", now)


class TestOpenAirYearHandling:
    """No more hardcoded 2026 fallback; same rollover rule as Babylon."""

    def test_missing_year_uses_current_year(self):
        now = datetime(2026, 10, 9, 12, 0)
        result = resolve_openair_date(20, 10, None, 21, 0, now)
        assert result == datetime(2026, 10, 20, 21, 0)

    def test_missing_year_past_date_rolls_over(self):
        now = datetime(2026, 12, 15, 12, 0)
        result = resolve_openair_date(10, 1, None, 21, 0, now)
        assert result == datetime(2027, 1, 10, 21, 0)

    def test_explicit_year_is_kept(self):
        now = datetime(2026, 10, 9, 12, 0)
        result = resolve_openair_date(15, 1, "27", 21, 0, now)
        assert result == datetime(2027, 1, 15, 21, 0)

    def test_invalid_date_returns_none(self):
        now = datetime(2026, 10, 9, 12, 0)
        assert resolve_openair_date(29, 2, None, 21, 0, now) is None


class TestConfigTitlePrefixes:
    """Extra patterns from config extend the built-in defaults."""

    def test_custom_pattern_is_stripped(self):
        service = TMDBService(
            api_key="test_key", title_prefix_patterns=[r"My Fest:\s*"]
        )
        assert service._clean_title("My Fest: Jaws") == "Jaws"

    def test_defaults_still_apply_without_config(self):
        service = TMDBService(api_key="test_key")
        assert "SPECIAL" not in service._clean_title("SPECIAL: Jaws")
