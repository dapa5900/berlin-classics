from pathlib import Path


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

    def test_generate_includes_gcal_export(self, sample_screenings):
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        # Per-card Google button and Template-URL builder
        assert "gcal-btn" in html
        assert "addSingleToGCal" in html
        assert "calendar.google.com/calendar/render?action=TEMPLATE" in html
        # New films hook the poster glow via is-new, no badge/chip elements
        assert "is-new" in html
        assert "new-badge" not in html
        # ICS export is removed: no checkboxes, no ICS builder, no download
        assert "movie-select" not in html
        assert "exportToCalendar" not in html
        assert "exportToGCal" not in html
        assert "berlin-classics-events.ics" not in html
        # Date icon replaced by the Google button, no dead references
        assert "date-icon" not in html
        assert "btn-plus" not in html
        assert "card-actions" not in html
        # Short mobile date variant rendered alongside the full date
        assert "card-date-short" in html
        # TMDB link lives in the title row (same typography as year), not the time row
        assert "tmdb-link-title" in html
        assert 'class="tmdb-link"' not in html

    def test_footer_lists_only_rendered_cinemas(self, sample_screenings):
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
                {
                    "name": "Open Air Cinema",
                    "url": "https://openair-kino.net",
                    "google_maps_url": None,
                },
            ]
        }
        # Blade Runner 2049 (2017) is filtered out by the threshold, so only
        # Babylon + Zoo Palast render — Open Air must not appear in the footer.
        rendered = [c for c in cinema_config["cinemas"] if c["name"] != "Open Air Cinema"]
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config=cinema_config,
            rendered_cinemas=rendered,
        )
        assert "https://babylonberlin.eu" in html
        assert "https://zoopalast.premiumkino.de" in html
        assert "Open Air Cinema" not in html
        assert "https://openair-kino.net" not in html

    def test_sections_grouped_and_sorted_by_cinema(self, sample_screenings):
        html = self.generator.generate(
            screenings=sample_screenings,
            output_path=None,
            threshold_year=2010,
            cinema_config={"cinemas": []},
        )
        # One section per rendered cinema, sorted by name (Babylon < Zoo Palast)
        assert html.index("cinema-title") < html.index("The Godfather")
        assert html.index(">Babylon <") < html.index(">Zoo Palast <")
        assert "Pulp Fiction" in html
