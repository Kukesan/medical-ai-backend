from markupsafe import Markup, escape


def json_to_html(data: object) -> Markup:
    """Render arbitrary JSON-like data (dict/list/primitive) as nested HTML.

    Used for the free-form extraction result, whose keys/shape vary per
    document since the extraction model decides the structure itself.
    """
    if data is None:
        return Markup('<span class="value-empty">&mdash;</span>')

    if isinstance(data, bool):
        return Markup(f'<span class="value-bool">{"Yes" if data else "No"}</span>')

    if isinstance(data, (int, float)):
        return Markup(f'<span class="value-number">{escape(data)}</span>')

    if isinstance(data, str):
        text = data.strip()
        if not text:
            return Markup('<span class="value-empty">&mdash;</span>')
        return Markup(f'<span class="value-text">{escape(text)}</span>')

    if isinstance(data, dict):
        if not data:
            return Markup('<span class="value-empty">&mdash;</span>')
        rows = "".join(
            f"<tr><th>{escape(_humanize_key(str(key)))}</th><td>{json_to_html(value)}</td></tr>"
            for key, value in data.items()
        )
        return Markup(f'<table class="json-table">{rows}</table>')

    if isinstance(data, list):
        if not data:
            return Markup('<span class="value-empty">&mdash;</span>')
        items = "".join(f"<li>{json_to_html(item)}</li>" for item in data)
        return Markup(f'<ul class="json-list">{items}</ul>')

    return Markup(f'<span class="value-text">{escape(str(data))}</span>')


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").strip().title()
