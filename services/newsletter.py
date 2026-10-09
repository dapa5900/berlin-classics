import locale
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

for _locale_name in ("de_DE.UTF-8", "de_DE", "German_Germany.1252", "German"):
    try:
        locale.setlocale(locale.LC_TIME, _locale_name)
        break
    except locale.Error:
        continue
else:
    logger.warning(
        "No German locale available, falling back to default date formatting"
    )


class NewsletterGenerator:
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(
        self,
        screenings: list,
        output_path: Optional[str] = None,
        threshold_year: int = 2010,
        cinema_config: Optional[dict] = None,
        rendered_cinemas: Optional[list] = None,
    ) -> str:
        classical_screenings = [
            s
            for s in screenings
            if s.year is not None
            and (s.year <= threshold_year or getattr(s, "skip_year_filter", False))
        ]

        by_cinema: dict[str, list] = {}
        for s in classical_screenings:
            by_cinema.setdefault(s.cinema_name, []).append(s)
        config_cinemas = (cinema_config or {}).get("cinemas", [])
        maps_by_name = {c.get("name"): c.get("google_maps_url") for c in config_cinemas}
        grouped_screenings = [
            {
                "name": name,
                "screenings": sorted(items, key=lambda s: s.date.replace(tzinfo=None)),
                "maps_url": maps_by_name.get(name) or "",
            }
            for name, items in sorted(by_cinema.items())
        ]

        template = self.env.get_template("newsletter.html")
        html = template.render(
            screenings=classical_screenings,
            grouped_screenings=grouped_screenings,
            generated_at=datetime.now(),
            threshold_year=threshold_year,
            cinema_config=cinema_config or {},
            rendered_cinemas=(
                rendered_cinemas if rendered_cinemas is not None else config_cinemas
            ),
        )

        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding="utf-8")

            logger.info(f"Newsletter generated: {output_file}")

        return html
