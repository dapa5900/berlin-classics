# Agent Guidelines for Berlin Classics Newsletter

## Project Overview

This is a Python web scraping project that generates a weekly HTML newsletter of classic film screenings from Berlin cinemas (Babylon, Zoo Palast, Astor, Best of Cinema). It scrapes cinema websites, filters for films from 2010 or earlier (except Best of Cinema), and produces a newsletter using Jinja2 templates.

## Build & Run Commands

### Running the Project

```bash
python main.py
```

This reads `config.yaml`, scrapes all configured cinemas, filters for classical films, and outputs an HTML newsletter to the `output/` directory.

### Dependencies

Install with:
```bash
pip install -r requirements.txt
```

Required packages: `httpx`, `beautifulsoup4`, `lxml`, `jinja2`, `pyyaml`, `playwright`, `requests-cache`.

### Testing

To run tests, create a `tests/` directory and use `pytest`:

```bash
# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_scraper.py

# Run a specific test function in a file
pytest tests/test_scraper.py::test_year_extraction
```

### Code Quality Tools

This project utilizes `ruff`, `black`, and `mypy` for code quality:

```bash
ruff check .               # Lint all files
black .                    # Format all files
mypy .                     # Type check (requires type annotations)
```

## Code Style Guidelines

### Imports

Standard library first, then third-party, then local. Use explicit relative imports for project modules.

### Formatting

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use blank lines between top-level definitions (2 lines) and functions (1 line)
- No trailing whitespace
- Use meaningful variable names

### Types & Data Structures

- Use type hints for all function signatures and return types.
- Use `Optional[X]` instead of `X | None` for Python < 3.10 compatibility.
- Use `dataclasses` (preferably frozen) for structured data (e.g., `Screening`).

### Naming Conventions

- Classes: `PascalCase` (e.g., `BabylonScraper`, `NewsletterGenerator`)
- Functions/variables: `snake_case` (e.g., `get_screenings`, `cinema_name`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DAY_MAP`)
- Private methods: prefix with underscore (e.g., `_rate_limit`)

### Error Handling

- Use `try/except` sparingly and catch specific exceptions.
- Return `None` or a default value when appropriate rather than raising.
- Log errors with descriptive messages including context (`logger.error(...)`).
- Bare `except:` is discouraged; prefer `except SomeException:`.

## Coding Standards for Agents

1. **Source of Truth:** Treat data scraped directly from cinema websites as the primary source of truth for raw metadata (year, runtime, original title). Use TMDB primarily for enrichment (posters, IDs) and disambiguation.
2. **Robustness:** If a scraping attempt fails, log a specific error and gracefully skip the item rather than crashing the orchestrator.
3. **Original Titles:** When handling non-English titles in brackets (e.g., `[La verità]`), always extract the original title and prioritize it in TMDB searches to ensure accurate matching.
4. **Immutability:** Use `dataclasses` with `frozen=True` for data transfer objects like `Screening`.

## Project Structure

```
.
├── main.py              # Entry point, orchestrator
├── config.yaml          # Cinema configurations
├── requirements.txt     # Dependencies
├── scrapers/            # Website scrapers
│   ├── base.py          # BaseScraper, Screening dataclass
│   ├── babylon.py       # Babylon-specific scraper
│   ├── zoo_palast.py    # Zoo Palast scraper
│   └── astor.py         # Astor scraper
├── services/            # Business logic
│   ├── newsletter.py    # HTML generation with Jinja2
│   ├── poster_lookup.py # Movie poster fetching
│   └── tmdb.py          # TMDBService - matching logic
├── templates/           # Jinja2 templates
│   └── newsletter.html  # Newsletter HTML template
└── output/              # Generated newsletters
```

## Adding a New Cinema

1. Create a new scraper class in `scrapers/` inheriting from `BaseScraper`.
2. Implement `get_screenings() -> list[Screening]`.
3. Add the cinema to `SCRAPER_MAP` in `main.py`.
4. Add entry to `config.yaml` with unique `type` matching the map key.
