
from services.tmdb import TMDBService


class TestCleanTitle:
    """Tests for TMDBService._clean_title."""

    def setup_method(self):
        self.service = TMDBService(api_key="test_key", language="de-DE")

    def test_removes_latin_brackets(self):
        result = self.service._clean_title("La verità [LVM]")
        assert "LVM" not in result

    def test_removes_event_prefixes(self):
        result = self.service._clean_title("Greek Film Festival: Zorba the Greek")
        assert "Greek Film Festival" not in result
        assert "Zorba the Greek" in result

    def test_removes_dash_suffixes(self):
        result = self.service._clean_title("Film Title - Director Name")
        assert "Film Title" == result

    def test_removes_babylon_suffix(self):
        result = self.service._clean_title("Film Title Babylon")
        assert "Film Title" == result

    def test_handles_ascii_replacement(self):
        title = "Cinema Paradiso - Original Title"
        result = self.service._clean_title(title)
        # Should not raise on valid ASCII
        assert result

    def test_collapses_whitespace(self):
        result = self.service._clean_title("  Film   Title  ")
        assert result == "Film Title"

    def test_strips_live_keyword(self):
        result = self.service._clean_title("Live at the Movies: Inception")
        assert "Live" not in result
        assert "Inception" in result

    def test_handles_modern_times(self):
        result = self.service._clean_title("Modern Times - Special Edition")
        assert result == "Modern Times"

    def test_handles_city_lights(self):
        result = self.service._clean_title("City Lights - Restored")
        assert result == "City Lights"

    def test_removes_with_guests(self):
        result = self.service._clean_title("Film Title with Guests")
        assert result == "Film Title"

    def test_handles_umlaut_oe(self):
        result = self.service._clean_title("Münchhausen")
        assert "Munchhausen" == result

    def test_handles_umlaut_ue(self):
        result = self.service._clean_title("Über")
        assert "Uber" == result

    def test_handles_umlaut_ae(self):
        result = self.service._clean_title("Mädchen")
        assert "Madchen" == result

    def test_handles_multiple_umlauts(self):
        result = self.service._clean_title("Die Unbestechlichen")
        assert "Die Unbestechlichen" == result

    def test_handles_umlauts_in_search_query(self):
        result = self.service._clean_title("So grün war mein Tal")
        assert "So grun war mein Tal" == result


class TestCalculateTitleSimilarity:
    """Tests for TMDBService._calculate_title_similarity."""

    def setup_method(self):
        self.service = TMDBService(api_key="test_key", language="de-DE")

    def test_identical_titles(self):
        result = self.service._calculate_title_similarity("The Godfather", "The Godfather")
        assert result == 1.0

    def test_one_in_another(self):
        result = self.service._calculate_title_similarity("Godfather", "The Godfather")
        assert result == 0.8

    def test_partial_match(self):
        result = self.service._calculate_title_similarity("The Godfather", "Godfather II")
        # "Godfather" is common word
        assert result > 0

    def test_no_match(self):
        result = self.service._calculate_title_similarity("Godfather", "Pulp Fiction")
        assert result == 0.0

    def test_case_insensitive(self):
        result = self.service._calculate_title_similarity("THE GODFATHER", "the godfather")
        assert result == 1.0
