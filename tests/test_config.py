from pathlib import Path


from main import load_config


def test_load_config_returns_dict(config_file: Path):
    result = load_config(str(config_file))
    assert isinstance(result, dict)
    assert "cinemas" in result
    assert "newsletter" in result
    assert "tmdb" in result
    assert "output" in result


def test_config_values(config_file: Path):
    result = load_config(str(config_file))
    assert result["tmdb"]["language"] == "de-DE"


def test_load_config_missing_file():
    try:
        load_config("/nonexistent/path/config.yaml")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_config_has_cinemas(config_file: Path):
    result = load_config(str(config_file))
    assert len(result["cinemas"]) == 1
    assert result["cinemas"][0]["name"] == "Test Cinema"
