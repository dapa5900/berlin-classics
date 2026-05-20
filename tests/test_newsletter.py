import tempfile
from pathlib import Path

import pytest

from services.newsletter import NewsletterGenerator


class TestNewsletterGenerator:
    """Tests for NewsletterGenerator."""

    def setup_method(self):
        self.generator = NewsletterGenerator(template_dir="templates")

    def test_generate_returns_html(self, sample_screenings):
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        assert isinstance(html, str)
        assert len(html) > 0

    def test_generate_includes_screening_title(self, sample_screenings):
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        assert "The Godfather" in html
        assert "Pulp Fiction" in html

    def test_generate_filters_by_threshold_year(self):
        from scrapers.base import Screening
        from datetime import datetime

        modern_screenings = [
            Screening(
                cinema_name="Test",
                movie_title="Blade Runner 2049",
                date=datetime(2026, 5, 20, 20, 0),
                year=2017,
            ),
        ]
        html = self.generator.generate(
            screenings=modern_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        # Blade Runner 2049 (2017) should be filtered out
        assert "Blade Runner 2049" not in html

    def test_generate_includes_skip_year_filter(self):
        from scrapers.base import Screening
        from datetime import datetime

        screenings = [
            Screening(
                cinema_name="Best of Cinema",
                movie_title="The Godfather",
                date=datetime(2026, 5, 20, 20, 0),
                year=1972,
                skip_year_filter=True,
            ),
        ]
        html = self.generator.generate(
            screenings=screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        assert "The Godfather" in html

    def test_generate_writes_file(self, sample_screenings, tmp_path: Path):
        output_path = str(tmp_path / "test_newsletter.html")
        result_path = self.generator.generate(
            screenings=sample_screenings,
            output_path=output_path,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0

    def test_generate_with_no_screenings(self):
        html = self.generator.generate(
            screenings=[],
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        assert isinstance(html, str)
        assert "Berlin Classics" in html

    def test_generate_with_cinema_config(self, sample_screenings):
        cinema_config = {
            "cinemas": [
                {
                    "name": "Babylon",
                    "url": "https://babylonberlin.eu",
                    "google_maps_url": "https://maps.example.com/babylon",
                },
                {
                    "name": "Zoo Palast",
                    "url": "https://zoopalast.premiumkino.de",
                    "google_maps_url": "https://maps.example.com/zoo",
                },
            ]
        }
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config=cinema_config,
        )
        assert "Babylon" in html
        assert "Zoo Palast" in html
