"""Distro READMEs agree with their recipes (WO-328).

tests/copilot/test_cp_packaging_lint.py checks version numbers and hash fields
inside each recipe. This guard compares each README with its recipe.

Offline. Repo files are read from the checkout root. Fake cases write only under
tmp_path. No network, subprocess, or git.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = ("aur", "flatpak", "homebrew", "nix", "scoop", "winget")
_ZERO_HASH = "0" * 64
_REAL_HASH = "ab12" * 16

# A named version may be the package version or another version the recipe
# itself states (Flatpak runtime 24.08, winget ManifestVersion). A version the
# recipe does not state is a mismatch.
_VERSION_TOKEN = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.\d+)?)(?![\d])")
_HASH_VALUE = re.compile(
    r"(?i)\b(?:sha256sums?|sha256|installersha256|hash)\b"
    r"(?:[\"']?\s*[:=]\s*\(?\s*[\"']?|\s+\")([^\"'\s)#,]+)"
)
_HASH_TOPIC = re.compile(
    r"(?i)\b(?:sha-?256|sha256sums?|installersha256|checksums?|hash(?:es)?)\b"
)
_PLACEHOLDER_PHRASE = re.compile(r"(?i)placeholder|not filled in")
_NOT_UPSTREAM = re.compile(
    r"(?i)not\s+published|not\s+submitted|nothing\s+is\s+submitted|"
    r"not\s+on\s+flathub|no\s+\w+\s+bucket|not\s+in\s+nixpkgs|"
    r"has\s+not\s+been\s+submitted"
)
_PY_PKG = re.compile(r"(?<![A-Za-z0-9])python-[a-z0-9]+(?:-[a-z0-9]+)*\b")
_RDNS = re.compile(r"\b[a-z][a-z0-9]*(?:\.[A-Za-z0-9-]+){2,}\b")
_WINGET_ID = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:\.[A-Z][A-Za-z0-9]*)+)\b")
_BREW_FORMULA_FLAG = re.compile(r"(?i)--formula(?:=|\s+)([A-Za-z0-9_+-]+)")
_BREW_SIMPLE = re.compile(
    r"(?i)\bbrew\s+(?:uninstall|test|reinstall|upgrade)\s+([A-Za-z0-9_+-]+)\b"
)
_BREW_INSTALL = re.compile(
    r"(?i)\bbrew\s+install\b(?:\s+--[A-Za-z0-9-]+)*\s+([A-Za-z0-9_@./\\+-]+)"
)
_RB_FILE = re.compile(r"(?i)(?<![A-Za-z0-9_+-])([A-Za-z0-9_+-]+)\.rb\b")
_SCOOP_JSON = re.compile(r"(?i)(?<![A-Za-z0-9_+-])([A-Za-z0-9_+-]+)\.json\b")
_SCOOP_UNINSTALL = re.compile(r"(?i)\bscoop\s+uninstall\s+([A-Za-z0-9_+-]+)\b")
_SCOOP_INSTALL = re.compile(r"(?i)\bscoop\s+install\s+(\S+)")
_BIN_NAME = re.compile(r"\bbin/([A-Za-z0-9_+-]+)\b")


def _under_root(path: Path) -> bool:
    try:
        path.relative_to(ROOT)
    except ValueError:
        return False
    return True


def _has_token(text: str, token: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
        text,
    ) is not None


def _one_value(values: list[str], label: str) -> tuple[str | None, str | None]:
    unique = list(dict.fromkeys(values))
    if not unique:
        return None, f"recipe does not name a {label}"
    if len(unique) > 1:
        return None, f"recipe names more than one {label}: {', '.join(unique)}"
    return unique[0], None


def _version_tokens(text: str) -> set[str]:
    return set(_VERSION_TOKEN.findall(text))


def _is_placeholder_hash(value: str) -> bool:
    token = value.strip().strip("'\"")
    if token.upper() == "SKIP" or token.upper().startswith("REPLACE_WITH"):
        return True
    return bool(re.fullmatch(r"0{64}", token))


def _placeholder_values(recipe: str) -> list[str]:
    found: list[str] = []
    for value in _HASH_VALUE.findall(recipe):
        if _is_placeholder_hash(value):
            found.append(value.strip().strip("'\""))
    return list(dict.fromkeys(found))


def _discloses_placeholder(readme: str) -> bool:
    """True when some paragraph talks about the hash and calls it out."""
    for paragraph in re.split(r"\n[ \t]*\n", readme):
        if _HASH_TOPIC.search(paragraph) and _PLACEHOLDER_PHRASE.search(paragraph):
            return True
    return False


def _project_table() -> dict[str, object]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return {}
    return project


def _recipe_files(channel_dir: Path) -> list[Path]:
    channel = channel_dir.name
    if channel == "aur":
        files = [channel_dir / "PKGBUILD"]
        srcinfo = channel_dir / ".SRCINFO"
        if srcinfo.is_file():
            files.append(srcinfo)
        return [path for path in files if path.is_file()]
    pattern = {
        "flatpak": "*.yml",
        "homebrew": "*.rb",
        "nix": "flake.nix",
        "scoop": "*.json",
        "winget": "*.yaml",
    }[channel]
    return sorted(path for path in channel_dir.glob(pattern) if path.is_file())


def _nix_version(text: str, channel_dir: Path) -> tuple[str | None, str | None]:
    inherits = bool(
        re.search(r"inherit\s*\(\s*project\s*\)\s*version", text) or "project.version" in text
    )
    if inherits:
        if not _under_root(channel_dir):
            return None, "nix recipe reads pyproject.toml, which this tree does not include"
        version = _project_table().get("version")
        if not isinstance(version, str) or not version:
            return None, "pyproject.toml has no project.version"
        return version, None
    return _one_value(re.findall(r'(?m)^\s*version\s*=\s*"([^"]+)"', text), "version")


def _package_version(
    channel: str, recipe: str, channel_dir: Path
) -> tuple[str | None, str | None]:
    if channel == "aur":
        return _one_value(re.findall(r"(?m)^\s*pkgver\s*=\s*(\S+)", recipe), "pkgver")
    if channel in ("flatpak", "homebrew"):
        return _one_value(re.findall(r"(\d+\.\d+\.\d+)\.tar\.gz", recipe), "sdist version")
    if channel == "scoop":
        return _one_value(re.findall(r'"version"\s*:\s*"([^"]+)"', recipe), "version")
    if channel == "winget":
        return _one_value(
            re.findall(r"(?m)^\s*PackageVersion:\s*(\S+)", recipe), "PackageVersion"
        )
    return _nix_version(recipe, channel_dir)


def _hash_problems(channel: str, readme: str, recipe: str) -> list[str]:
    placeholders = _placeholder_values(recipe)
    if not placeholders or _discloses_placeholder(readme):
        return []
    shown = ", ".join(placeholders)
    return [
        (
            "placeholder: "
            f"{channel} recipe hash is a placeholder ({shown}) but the README does not "
            "say placeholder or not filled in about that hash"
        )
    ]


def _version_problems(readme: str, recipe: str, package_version: str | None) -> list[str]:
    named = _version_tokens(readme)
    if not named:
        return []
    allowed = _version_tokens(recipe)
    if package_version:
        allowed.add(package_version)
    bad = sorted(named - allowed)
    if not bad:
        return []
    label = package_version if package_version else "unset"
    return [
        "version: README names "
        + ", ".join(bad)
        + f", which the recipe does not state (recipe version {label})"
    ]


def _upstream_problems(channel: str, readme: str) -> list[str]:
    if _NOT_UPSTREAM.search(readme):
        return []
    return [f"upstream: {channel} README does not say the recipe is not submitted upstream"]


def _leaf_stem(token: str) -> str:
    name = token.strip().strip("`").replace("\\", "/").rsplit("/", 1)[-1]
    for suffix in (".rb", ".json"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


def _rdns_tokens(text: str) -> list[str]:
    found: list[str] = []
    for match in _RDNS.findall(text):
        found.append(re.sub(r"\.(?:yml|yaml)$", "", match))
    return found


def _claimed_formulas(readme: str) -> list[str]:
    claimed = [
        *_BREW_FORMULA_FLAG.findall(readme),
        *_BREW_SIMPLE.findall(readme),
        *(_leaf_stem(token) for token in _BREW_INSTALL.findall(readme)),
        *_RB_FILE.findall(readme),
    ]
    return list(dict.fromkeys(claimed))


def _claimed_scoop_names(readme: str) -> list[str]:
    claimed = [*_SCOOP_JSON.findall(readme), *_SCOOP_UNINSTALL.findall(readme)]
    for token in _SCOOP_INSTALL.findall(readme):
        match = re.search(r"(?i)([A-Za-z0-9_+-]+)\.json\b", token)
        claimed.append(match.group(1) if match else _leaf_stem(token))
    return list(dict.fromkeys(claimed))


def _aur_id_problems(readme: str, recipe: str) -> list[str]:
    problems: list[str] = []
    pkgname, error = _one_value(re.findall(r"(?m)^\s*pkgname\s*=\s*(\S+)", recipe), "pkgname")
    if error or pkgname is None:
        return [f"package-id: {error or 'recipe has no pkgname'}"]
    if not _has_token(readme, pkgname):
        problems.append(f"package-id: README does not name {pkgname}")
    for claimed in dict.fromkeys(_PY_PKG.findall(readme)):
        if not _has_token(recipe, claimed):
            problems.append(f"package-id: README names {claimed}, which the recipe does not")
    return problems


def _flatpak_id_problems(readme: str, recipe: str) -> list[str]:
    problems: list[str] = []
    app_id, error = _one_value(re.findall(r"(?m)^\s*app-id:\s*(\S+)", recipe), "app-id")
    if error or app_id is None:
        return [f"package-id: {error or 'recipe has no app-id'}"]
    if not _has_token(readme, app_id):
        problems.append(f"package-id: README does not name {app_id}")
    for claimed in dict.fromkeys(_rdns_tokens(readme)):
        if not _has_token(recipe, claimed):
            problems.append(f"package-id: README names {claimed}, which the recipe does not")
    return problems


def _homebrew_id_problems(readme: str, recipe: str, channel_dir: Path) -> list[str]:
    stems = [path.stem for path in sorted(channel_dir.glob("*.rb"))]
    formula, error = _one_value(stems, "formula file")
    if error or formula is None:
        return [f"package-id: {error or 'recipe has no formula'}"]
    for class_name in re.findall(r"(?m)^class\s+([A-Za-z0-9_]+)\s*<\s*Formula\b", recipe):
        if class_name.lower() != formula.lower():
            return [f"package-id: formula class {class_name} does not match {formula}"]
    problems: list[str] = []
    if not _has_token(readme, formula):
        problems.append(f"package-id: README does not name formula {formula}")
    for claimed in _claimed_formulas(readme):
        if claimed.lower() != formula.lower():
            problems.append(f"package-id: README names {claimed}, recipe formula is {formula}")
    return problems


def _scoop_id_problems(readme: str, channel_dir: Path) -> list[str]:
    stems = [path.stem for path in sorted(channel_dir.glob("*.json"))]
    app_name, error = _one_value(stems, "scoop manifest")
    if error or app_name is None:
        return [f"package-id: {error or 'recipe has no scoop manifest'}"]
    problems: list[str] = []
    if not _has_token(readme, app_name):
        problems.append(f"package-id: README does not name {app_name}")
    for claimed in _claimed_scoop_names(readme):
        if claimed.lower() != app_name.lower():
            problems.append(f"package-id: README names {claimed}, recipe manifest is {app_name}")
    return problems


def _winget_id_problems(readme: str, recipe: str) -> list[str]:
    package_id, error = _one_value(
        re.findall(r"(?m)^\s*PackageIdentifier:\s*(\S+)", recipe), "PackageIdentifier"
    )
    if error or package_id is None:
        return [f"package-id: {error or 'recipe has no PackageIdentifier'}"]
    problems: list[str] = []
    if not _has_token(readme, package_id):
        problems.append(f"package-id: README does not name {package_id}")
    for claimed in dict.fromkeys(_WINGET_ID.findall(readme)):
        if claimed != package_id:
            problems.append(f"package-id: README names {claimed}, recipe id is {package_id}")
    return problems


def _nix_id_problems(readme: str, recipe: str, channel_dir: Path) -> list[str]:
    names = [
        *re.findall(r'mainProgram\s*=\s*"([^"]+)"', recipe),
        *re.findall(r'pname\s*=\s*"([^"]+)"', recipe),
    ]
    if "project.name" in recipe and _under_root(channel_dir):
        project_name = _project_table().get("name")
        if isinstance(project_name, str) and project_name:
            names.append(project_name)
    unique = list(dict.fromkeys(names))
    if not unique:
        return ["package-id: nix recipe does not name a package"]
    if len(unique) > 1:
        return ["package-id: nix recipe names more than one package: " + ", ".join(unique)]
    package = unique[0]
    problems: list[str] = []
    if not _has_token(readme, package):
        problems.append(f"package-id: README does not name {package}")
    for claimed in dict.fromkeys(_BIN_NAME.findall(readme)):
        if claimed not in unique:
            problems.append(
                f"package-id: README names bin/{claimed}, recipe package is {package}"
            )
    return problems


def _id_problems(
    channel: str, readme: str, recipe: str, channel_dir: Path
) -> list[str]:
    if channel == "aur":
        return _aur_id_problems(readme, recipe)
    if channel == "flatpak":
        return _flatpak_id_problems(readme, recipe)
    if channel == "homebrew":
        return _homebrew_id_problems(readme, recipe, channel_dir)
    if channel == "scoop":
        return _scoop_id_problems(readme, channel_dir)
    if channel == "winget":
        return _winget_id_problems(readme, recipe)
    return _nix_id_problems(readme, recipe, channel_dir)


def compare_channel(channel_dir: Path) -> list[str]:
    """Problems in one channel directory, or an empty list when the README matches."""
    channel = channel_dir.name
    if channel not in CHANNELS:
        return [f"package-id: unknown channel {channel}"]
    readme_path = channel_dir / "README.md"
    if not readme_path.is_file():
        return [f"package-id: {channel}/README.md is missing"]
    recipes = _recipe_files(channel_dir)
    if not recipes:
        return [f"package-id: {channel} has no recipe file"]
    readme = readme_path.read_text(encoding="utf-8")
    recipe = "\n".join(path.read_text(encoding="utf-8") for path in recipes)
    version, version_error = _package_version(channel, recipe, channel_dir)
    problems = [
        *_hash_problems(channel, readme, recipe),
        *_version_problems(readme, recipe, version),
        *_upstream_problems(channel, readme),
        *_id_problems(channel, readme, recipe, channel_dir),
    ]
    if version_error:
        problems.append(f"version: {version_error}")
    return problems


def _channel_cases() -> list[str]:
    return list(CHANNELS)


@pytest.mark.parametrize("channel", _channel_cases())
def test_distro_readme_matches_its_recipe(channel: str) -> None:
    problems = compare_channel(ROOT / "distro" / channel)
    assert not problems, "\n".join(problems)


def _write_channel(tmp_path: Path, channel: str, files: dict[str, str]) -> Path:
    folder = tmp_path / channel
    folder.mkdir(parents=True)
    for name, text in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return folder


def _kinds(problems: list[str]) -> set[str]:
    return {item.split(":", 1)[0] for item in problems}


def _homebrew_formula(hash_line: str, version: str = "1.2.3") -> str:
    return (
        "class Freemyid < Formula\n"
        '  url "https://files.pythonhosted.org/packages/source/f/freemyid/'
        f'freemyid-{version}.tar.gz"\n'
        f"  {hash_line}\n"
    )


def _homebrew_readme(version: str, hash_sentence: str, install_name: str = "freemyid") -> str:
    return (
        f"# Homebrew formula {install_name}\n"
        "\n"
        f"This draft is not published yet. Version {version}.\n"
        f"{hash_sentence}\n"
        "\n"
        f"brew install {install_name}\n"
    )


@pytest.mark.parametrize(
    "hash_line",
    [
        pytest.param('sha256 "REPLACE_WITH_SDIST_SHA256"', id="replace-with"),
        pytest.param("sha256sums=('SKIP')", id="skip"),
        pytest.param(f'sha256 "{_ZERO_HASH}"', id="all-zeros"),
    ],
)
def test_readme_that_hides_a_placeholder_fails(tmp_path: Path, hash_line: str) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula(hash_line),
            "README.md": _homebrew_readme("1.2.3", "The sha256 will be set at release."),
        },
    )
    assert _kinds(compare_channel(folder)) == {"placeholder"}


def test_placeholder_word_away_from_the_hash_fails(tmp_path: Path) -> None:
    readme = (
        "# Homebrew formula freemyid\n"
        "\n"
        "This draft is not published yet. Version 1.2.3.\n"
        "The sha256 is listed in the formula.\n"
        "\n"
        "This note is a placeholder for later.\n"
        "\n"
        "brew install freemyid\n"
    )
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula('sha256 "REPLACE_WITH_SDIST_SHA256"'),
            "README.md": readme,
        },
    )
    assert _kinds(compare_channel(folder)) == {"placeholder"}


def test_readme_that_names_a_wrong_version_fails(tmp_path: Path) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula('sha256 "REPLACE_WITH_SDIST_SHA256"'),
            "README.md": _homebrew_readme("9.9.9", "The sha256 is a placeholder."),
        },
    )
    assert _kinds(compare_channel(folder)) == {"version"}


def test_readme_that_names_a_wrong_formula_fails(tmp_path: Path) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula('sha256 "REPLACE_WITH_SDIST_SHA256"'),
            "README.md": _homebrew_readme(
                "1.2.3", "The sha256 is a placeholder.", install_name="otherformula"
            ),
        },
    )
    assert _kinds(compare_channel(folder)) == {"package-id"}


def test_readme_that_names_a_wrong_winget_id_fails(tmp_path: Path) -> None:
    recipe = (
        "PackageIdentifier: FreeMyID.FreeMyID\n"
        "PackageVersion: 1.2.3\n"
        f"InstallerSha256: {_ZERO_HASH}\n"
    )
    readme = (
        "# winget manifest\n"
        "\n"
        "Nothing is submitted to the winget community repository. Version 1.2.3.\n"
        "InstallerSha256 is a placeholder.\n"
        "\n"
        "winget uninstall Other.App\n"
    )
    folder = _write_channel(
        tmp_path,
        "winget",
        {"FreeMyID.FreeMyID.installer.yaml": recipe, "README.md": readme},
    )
    assert _kinds(compare_channel(folder)) == {"package-id"}


def test_matching_readme_and_recipe_passes(tmp_path: Path) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula('sha256 "REPLACE_WITH_SDIST_SHA256"'),
            "README.md": _homebrew_readme("1.2.3", "The sha256 is a placeholder."),
        },
    )
    assert compare_channel(folder) == []


def test_not_filled_in_counts_as_saying_the_hash_is_a_placeholder(tmp_path: Path) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula("sha256sums=('SKIP')"),
            "README.md": _homebrew_readme("1.2.3", "The sha256 is not filled in."),
        },
    )
    assert compare_channel(folder) == []


def test_real_hash_does_not_need_the_placeholder_word(tmp_path: Path) -> None:
    folder = _write_channel(
        tmp_path,
        "homebrew",
        {
            "freemyid.rb": _homebrew_formula(f'sha256 "{_REAL_HASH}"'),
            "README.md": _homebrew_readme("1.2.3", "The sha256 is the sdist checksum."),
        },
    )
    assert compare_channel(folder) == []
