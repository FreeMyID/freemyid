"""WO-111: developer release claims match the shipped v0.2.0 scope, offline."""

import re
from html import unescape
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web/dist/developers/index.html"


def text(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())


@pytest.fixture(scope="module")
def sections() -> dict[str, str]:
    assert PAGE.is_file(), "Run pnpm --dir web build before testing developer release status"
    html = PAGE.read_text(encoding="utf-8")
    return dict(re.findall(
        r'<section\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</section>', html, re.DOTALL,
    ))


def installation_section(sections: dict[str, str], name: str) -> str:
    match = re.search(
        rf'<h3\b[^>]*\bid="{name}"[^>]*>.*?(?=<h3\b|$)',
        sections["install"], re.DOTALL,
    )
    assert match is not None, f"Existing install anchor must remain: {name}"
    return match[0]


def test_status_separates_shipped_cli_from_planned_desktop_and_docker(
    sections: dict[str, str],
) -> None:
    rows = [text(row) for row in re.findall(r"<li\b[^>]*>(.*?)</li>", sections["status"], re.DOTALL)]
    assert any("Available now" in row and "Windows app" in row for row in rows)
    assert any(
        all(phrase in row for phrase in (
            "Available now", "Linux and macOS command line", "PyPI", "pipx",
            "headless runs", "JSON output", "background scheduling",
        )) for row in rows
    )
    assert any(
        all(phrase in row for phrase in (
            "Planned", "public Docker image", "desktop apps and packages for Linux and macOS",
        )) for row in rows
    )
    status = text(sections["status"])
    assert "Version 0.2.0 is out" in status
    assert "Linux and macOS are command line only" in status
    assert "Coming in v0.2" not in status
    assert "Version 0.2 isn't out yet" not in status


@pytest.mark.parametrize("section", ["first-run", "scheduling", "secrets", "json"])
def test_shipped_features_no_longer_carry_prerelease_badges(
    sections: dict[str, str], section: str,
) -> None:
    copy = text(sections[section])
    assert "Coming in v0.2" not in copy
    assert "Planned" not in copy
    assert "you will be able" not in copy
    assert "will read the saved status" not in copy


@pytest.mark.parametrize("name", ["pipx", "source"])
def test_shipped_install_methods_are_current(sections: dict[str, str], name: str) -> None:
    copy = text(installation_section(sections, name))
    assert "Coming in v0.2" not in copy and "Planned" not in copy
    assert "Linux and macOS" in copy
    assert "isn't finished until v0.2" not in copy
    if name == "pipx":
        assert "pipx install freemyid" in copy
    else:
        assert "Version 0.2.0 supports the command line" in copy


def test_public_docker_commands_are_explicitly_not_ready(sections: dict[str, str]) -> None:
    docker = installation_section(sections, "docker")
    copy = text(docker)
    assert "With Docker Planned" in copy
    assert "The public Docker image is not available yet" in copy
    assert "The examples below are planned; do not run them yet" in copy
    assert "Once the public image is available" in copy
    assert docker.index("not available yet") < docker.index("<pre")
    assert "ghcr.io/freemyid/freemyid" in copy
    assert "docker pull" not in copy


def test_json_is_present_tense_and_mac_testing_limit_stays_visible(
    sections: dict[str, str],
) -> None:
    json = text(sections["json"])
    assert "reads the saved status without changing it" in json
    assert "JSON output contains exactly one JSON object on stdout" in json
    assert "Each object identifies its versioned schema" in json
    scheduling = text(sections["scheduling"])
    assert "a systemd user timer on Linux, a launchd agent on macOS" in scheduling
    assert "not yet on real Mac hardware" in scheduling
