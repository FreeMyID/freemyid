"""Check the built Open Graph metadata for the developer reference pages."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web/dist"
PAGES_YAML = ROOT / "site_src/pages.yaml"
SITE_YAML = ROOT / "site_src/site.yaml"

ROUTES = {
    "developers-cli": ("developers/cli/index.html", "og-developers-cli.png"),
    "developers-config": ("developers/config/index.html", "og-developers-config.png"),
}


class _OpenGraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        prop = attributes.get("property")
        content = attributes.get("content")
        if prop and content is not None and prop.startswith("og:"):
            self.values[prop] = content


def _meta(route: str) -> dict[str, str]:
    parser = _OpenGraphParser()
    parser.feed((DIST / route).read_text(encoding="utf-8"))
    return parser.values


@pytest.mark.web_dist
@pytest.mark.parametrize(("page_id", "route", "image_name"), [
    (page_id, route, image_name)
    for page_id, (route, image_name) in ROUTES.items()
])
def test_developer_reference_open_graph_metadata(
    page_id: str, route: str, image_name: str
) -> None:
    pages = yaml.safe_load(PAGES_YAML.read_text(encoding="utf-8"))
    page = next(entry for entry in pages if entry["id"] == page_id)
    base_url = yaml.safe_load(SITE_YAML.read_text(encoding="utf-8"))["base_url"]
    metadata = _meta(route)

    image_url = metadata["og:image"]
    assert image_url == f"{base_url}assets/{image_name}"
    assert "og-home.png" not in image_url
    other_image = "og-developers-config.png" if page_id == "developers-cli" else "og-developers-cli.png"
    assert other_image not in image_url
    assert metadata["og:image:width"] == "1200"
    assert metadata["og:image:height"] == "630"
    assert metadata["og:image:alt"] == page["og_alt"]

    image_path = urlparse(image_url).path
    assert (DIST / image_path.lstrip("/")).is_file()
