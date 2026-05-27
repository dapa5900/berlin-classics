from pathlib import Path

import pytest

from services.tmdb import TMDBService


@pytest.fixture
def tmdb_service():
    return TMDBService(api_key="test_key_for_unit_tests", language="de-DE")


@pytest.fixture
def filmrausch_embedded_json():
    return """
var filmrausch_php_vars = {"cached_data":{"shows":[{"id":"1","movieId":"101","name":"TOP GUN","beginning":{"isoFull":"2026-06-01T20:15:00+02:00"},"duration":110},{"id":"2","movieId":"102","name":"SPECIAL: Klimareihe: EARTH'S GREATEST ENEMY","beginning":{"isoFull":"2026-06-02T18:30:00+02:00"},"duration":125}],"movies":{"101":{"name":"TOP GUN","title_orig":"Top Gun","released":"1986-08-07 00:00:00","duration":109,"largeImage":"https://media.kinoheld.de/poster-topgun.jpg"},"102":{"name":"SPECIAL: Klimareihe: EARTH'S GREATEST ENEMY","title_orig":"EARTH'S GREATEST ENEMY","released":"2025-01-01 00:00:00","duration":121,"largeImage":"https://media.kinoheld.de/poster-earth.jpg"}}}};
""".strip()


@pytest.fixture
def sample_screenings():
    from scrapers.base import Screening
    from datetime import datetime

    return [
        Screening(
            cinema_name="Babylon",
            movie_title="The Godfather",
            date=datetime(2026, 5, 20, 20, 0),
            url="https://babylonberlin.eu/film/godfather",
            year=1972,
            poster_url="https://image.tmdb.org/t/p/w500/godfather.jpg",
            tmdb_url="https://www.themoviedb.org/movie/238",
            runtime=175,
        ),
        Screening(
            cinema_name="Zoo Palast",
            movie_title="Pulp Fiction",
            date=datetime(2026, 5, 21, 19, 30),
            url="https://zoopalast.premiumkino.de/film/pulp-fiction",
            year=1994,
            poster_url="https://image.tmdb.org/t/p/w500/pulp.jpg",
            tmdb_url="https://www.themoviedb.org/movie/680",
            runtime=154,
        ),
        Screening(
            cinema_name="Best of Cinema",
            movie_title="Blade Runner 2049",
            date=datetime(2026, 5, 22, 21, 0),
            url="https://www.bestofcinema.de/film/blade-runner-2049",
            year=2017,
            poster_url=None,
            tmdb_url="https://www.themoviedb.org/movie/335984",
            runtime=164,
        ),
    ]


@pytest.fixture
def config_file(tmp_path: Path):
    import yaml

    config = {
        "cinemas": [
            {"name": "Test Cinema", "url": "https://example.com", "type": "babylon"},
        ],
        "newsletter": {"classical_year_threshold": 2010},
        "tmdb": {"language": "de-DE"},
        "output": {"directory": "output", "filename_template": "newsletter_{date}.html"},
    }
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    return config_path
