from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.utils.json_to_html import json_to_html

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["json_html"] = json_to_html
