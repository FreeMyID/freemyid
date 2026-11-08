"""Lint the packaging recipes under distro/ (CP-12 / WO-150).

Every recipe that exists must:
- name the version from pyproject.toml (nix reads pyproject.toml itself, which also counts);
- carry a hash field, where a placeholder is allowed only if the recipe says so in words;
- download from FreeMyID/freemyid on GitHub or the PyPI project `freemyid`.
Recipes that do not exist yet are skipped. Offline; reads files only.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DISTRO = ROOT / "distro"
PYPROJECT_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
# Community recipes never track a pre-release (0.3.0rc1 and the like): while pyproject is a
# pre-release they keep naming the latest stable release from site_src/data/release.yaml.
# (In-house fix with the v0.3.0rc1 bump; Copilot informed via the tracker.)
_STABLE = re.search(r'^version:\s*"([^"]+)"', (ROOT / "site_src" / "data" / "release.yaml")
                    .read_text(encoding="utf-8"), re.MULTILINE)
VERSION = (_STABLE.group(1) if re.search(r"(a|b|rc|dev)\d*$", PYPROJECT_VERSION) and _STABLE
           else PYPROJECT_VERSION)

RECIPES = [
    "aur/PKGBUILD",
    "flatpak/org.freemyid.FreeMyID.yml",
    "homebrew/freemyid.rb",
    "nix/flake.nix",
    "scoop/freemyid.json",
    "winget/FreeMyID.FreeMyID.yaml",
    "winget/FreeMyID.FreeMyID.installer.yaml",
    "winget/FreeMyID.FreeMyID.locale.en-US.yaml",
]
# Recipes that download an artifact, so they need a hash.
HASHED = [r for r in RECIPES if r.split("/")[0] != "nix" and not r.endswith(("FreeMyID.yaml", "locale.en-US.yaml"))]
# Recipes that pin a version number in their text.
VERSIONED = [r for r in RECIPES if not r.startswith("nix/")]

HASH_RE = re.compile(
    r"""(?i)\b(?:sha256sums?|sha256|installersha256|hash)\b(?:["']?\s*[:=]\s*\(?\s*["']?|\s+")([^"'\s)#,]+)"""
)
PLACEHOLDER_WORDS = re.compile(r"(?i)placeholder|fixme|todo|replace_with|\bskip\b")
GITHUB_RE = re.compile(r"github\.com/([^/\s\"')]+)/([^/\s\"')#]+)")
PYPI_RE = re.compile(r"files\.pythonhosted\.org/packages/source/(\w)/([^/\s\"']+)/")


def _recipe(rel: str) -> str:
    path = DISTRO / rel
    if not path.exists():
        pytest.skip(f"{rel} does not exist yet")
    return path.read_text(encoding="utf-8")


def _is_real_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value)) and set(value) != {"0"}


@pytest.mark.parametrize("rel", VERSIONED)
def test_recipe_names_pyproject_version(rel: str) -> None:
    text = _recipe(rel)
    assert re.search(rf"(?<![\d.]){re.escape(VERSION)}(?![\d])", text), (
        f"distro/{rel} does not mention version {VERSION} from pyproject.toml"
    )
    stale = {
        v
        for v in re.findall(r"(?:PackageVersion:|pkgver=|\"version\":|[-/vV])\s*\"?(\d+\.\d+\.\d+)(?![\d.]*\d\.\d)", text)
        if v != VERSION
    }
    stale.discard("1.10.0")  # winget ManifestVersion, not ours
    assert not stale, f"distro/{rel} mentions other versions: {sorted(stale)}"


def test_nix_flake_reads_version_from_pyproject() -> None:
    text = _recipe("nix/flake.nix")
    assert "pyproject.toml" in text
    assert re.search(r"inherit\s*\(project\)\s*version", text) or "project.version" in text


@pytest.mark.parametrize("rel", HASHED)
def test_recipe_has_hash_field_and_placeholders_are_marked(rel: str) -> None:
    text = _recipe(rel)
    values = [m.group(1) for m in HASH_RE.finditer(text)]
    assert values, f"distro/{rel} has no sha/hash field"
    for value in values:
        if _is_real_hash(value):
            continue
        assert PLACEHOLDER_WORDS.search(text), (
            f"distro/{rel} has unmarked placeholder hash {value!r}; say 'placeholder' near it"
        )


@pytest.mark.parametrize("rel", RECIPES)
def test_recipe_points_only_at_freemyid_sources(rel: str) -> None:
    text = _recipe(rel)
    for owner, repo in GITHUB_RE.findall(text):
        if owner == "NixOS":
            continue
        assert (owner, repo.removesuffix(".git")) == ("FreeMyID", "freemyid"), (
            f"distro/{rel} points at github.com/{owner}/{repo}"
        )
    for letter, project in PYPI_RE.findall(text):
        assert project == "freemyid" and letter == "f", f"distro/{rel} downloads PyPI project {project!r}"


@pytest.mark.parametrize(
    "rel", ["aur/PKGBUILD", "flatpak/org.freemyid.FreeMyID.yml", "homebrew/freemyid.rb",
            "scoop/freemyid.json", "winget/FreeMyID.FreeMyID.installer.yaml"],
)
def test_download_recipes_have_a_freemyid_download_url(rel: str) -> None:
    text = _recipe(rel)
    if rel == "aur/PKGBUILD":
        assert re.search(r"^_name=freemyid\s*$", text, re.MULTILINE)
        assert "files.pythonhosted.org/packages/source/" in text
        return
    assert (
        "github.com/FreeMyID/freemyid/" in text
        or "files.pythonhosted.org/packages/source/f/freemyid/" in text
    ), f"distro/{rel} has no FreeMyID download URL"
