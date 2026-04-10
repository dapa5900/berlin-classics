import locale
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")


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
    ) -> str:
        classical_screenings = [
            s
            for s in screenings
            if s.year is not None
            and (s.year <= threshold_year or getattr(s, "skip_year_filter", False))
        ]

        template = self.env.get_template("newsletter.html")
        html = template.render(
            screenings=classical_screenings,
            generated_at=datetime.now(),
            threshold_year=threshold_year,
            cinema_config=cinema_config or {},
        )

        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding="utf-8")

            logger.info(f"Newsletter generated: {output_file}")

        return html
