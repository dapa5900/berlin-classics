
import json
import re
from datetime import datetime

from main import filter_screenings, filter_no_tmdb
from scrapers.base import Screening
from scrapers.filmrausch import _clean_movie_title


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


class TestFilmrauschCleanTitle:
    def test_regular_title_unchanged(self):
        assert _clean_movie_title("TOP GUN") == "TOP GUN"
        assert _clean_movie_title("ROYA") == "ROYA"

    def test_strips_special_prefix(self):
        assert _clean_movie_title("SPECIAL: Klimareihe: EARTH'S GREATEST ENEMY") == "EARTH'S GREATEST ENEMY"

    def test_strips_open_air_prefix(self):
        result = _clean_movie_title("SPECIAL: OPEN AIR: REEL LOVE: BRIDGET JONES - SCHOKOLADE ZUM FRÜHSTÜCK")
        assert result == "BRIDGET JONES - SCHOKOLADE ZUM FRÜHSTÜCK"

    def test_strips_offene_leinwand(self):
        assert _clean_movie_title("SPECIAL: OFFENE LEINWAND: BABA KUSH") == "BABA KUSH"

    def test_strips_mondo_video(self):
        result = _clean_movie_title("SPECIAL: Mondo Video II: STORY OF RICKY (DF) & MEN BEHIND THE SUN")
        assert result == "STORY OF RICKY (DF) & MEN BEHIND THE SUN"


class TestFilmrauschJsonParsing:
    def test_parse_embedded_json(self, filmrausch_embedded_json):
        match = re.search(r"var filmrausch_php_vars\s*=\s*({.*?});", filmrausch_embedded_json, re.DOTALL)
        assert match is not None
        data = json.loads(match.group(1))
        cached = data.get("cached_data", {})
        shows = cached.get("shows", [])
        movies = cached.get("movies", {})
        assert len(shows) == 2
        assert shows[0]["name"] == "TOP GUN"
        assert shows[0]["beginning"]["isoFull"] == "2026-06-01T20:15:00+02:00"
        assert movies["101"]["title_orig"] == "Top Gun"
        assert movies["102"]["title_orig"] == "EARTH'S GREATEST ENEMY"

    def test_clean_title_after_json_parse(self, filmrausch_embedded_json):
        match = re.search(r"var filmrausch_php_vars\s*=\s*({.*?});", filmrausch_embedded_json, re.DOTALL)
        data = json.loads(match.group(1))
        shows = data["cached_data"]["shows"]
        special_show = shows[1]
        cleaned = _clean_movie_title(special_show["name"])
        assert cleaned == "EARTH'S GREATEST ENEMY"


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


class TestNewFlags:
    """Tests for the new-screening detection and snapshot history."""

    def _make_screening(
        self, title="Jaws", cinema="Babylon", date=None, venue=None,
    ) -> Screening:
        return Screening(
            cinema_name=cinema,
            movie_title=title,
            date=date or datetime(2026, 10, 10, 20, 15),
            year=1975,
            venue_name=venue,
        )

    def test_screening_key_uses_venue(self):
        from main import screening_key

        a = self._make_screening(venue="Freiluftbühne")
        b = self._make_screening(venue="Anderer Ort")
        assert screening_key(a) != screening_key(b)
        c = self._make_screening()
        d = self._make_screening()
        assert screening_key(c) == screening_key(d)

    def test_apply_new_flags_empty_baseline_marks_nothing(self):
        from main import apply_new_flags

        screenings = [self._make_screening()]
        apply_new_flags(screenings, set())
        assert screenings[0].is_new is False

    def test_apply_new_flags(self):
        from main import apply_new_flags, screening_key

        known = self._make_screening()
        new_date = self._make_screening(date=datetime(2026, 10, 11, 20, 15))
        new_cinema = self._make_screening(cinema="Zoo Palast")
        screenings = [known, new_date, new_cinema]
        apply_new_flags(screenings, {screening_key(known)})
        assert known.is_new is False
        assert new_date.is_new is True
        assert new_cinema.is_new is True

    def test_snapshot_roundtrip_and_rotation(self, tmp_path, monkeypatch):
        import main
        from main import load_baseline_keys, screening_key

        monkeypatch.setattr(main, "SNAPSHOT_DIR", tmp_path)
        assert load_baseline_keys("2026-10-08") == set()

        old = [self._make_screening()]
        main.save_snapshot(old, "2026-09-30")
        assert (tmp_path / "screenings_2026-09-30.json").exists()

        current = [self._make_screening(), self._make_screening("Jaws 2")]
        main.save_snapshot(current, "2026-10-07")

        # Baseline = youngest snapshot older than today
        assert load_baseline_keys("2026-10-07") == {
            screening_key(s) for s in old
        }

        main.save_snapshot(current, "2026-10-08")

        # 8-day-old snapshot pruned, 8-day window kept
        assert not (tmp_path / "screenings_2026-09-30.json").exists()
        assert (tmp_path / "screenings_2026-10-07.json").exists()
        assert (tmp_path / "screenings_2026-10-08.json").exists()

        baseline = load_baseline_keys("2026-10-08")
        assert baseline == {screening_key(s) for s in current}
