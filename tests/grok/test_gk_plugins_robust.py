"""WO-346: a broken custom submitter falls back and does not break a run.

Fake people only. No network. Plugin files live under the test tmp data folder.
"""
from __future__ import annotations

import logging
import socket
from pathlib import Path

import pytest

from freemyid.engine import plugins
from freemyid.models import Broker, Tier

_VALID = """\
from pathlib import Path

from freemyid.interfaces import Submitter as _Base

Path(__file__).with_name("imported.txt").write_text("1", encoding="utf-8")


class Submitter(_Base):
    marker = "gk346"

    async def search(self, ctx):
        Path(__file__).with_name("called.txt").write_text("search", encoding="utf-8")
        return []

    async def submit(self, ctx, listings):
        Path(__file__).with_name("called.txt").write_text("submit", encoding="utf-8")
        return None
"""

_IMPORT = 'raise RuntimeError("Jane Q Testperson Springfield IL")\n'

_SYNTAX = "def (\n"

_MISSING = "VALUE = 1\n"

_CONSTRUCT = """\
from freemyid.interfaces import Submitter as _Base


class Submitter(_Base):
    def __init__(self) -> None:
        raise RuntimeError("construct-failed")

    async def search(self, ctx):
        return []

    async def submit(self, ctx, listings):
        return None
"""

_WRONG = """\
class Submitter:
    pass
"""

_RAN = """\
from pathlib import Path

Path(__file__).with_name("plugin.ran").write_text("ran", encoding="utf-8")
raise RuntimeError("should-not-run")
"""

_OTHER = """\
from pathlib import Path

Path(__file__).with_name("other.ran").write_text("ran", encoding="utf-8")
"""


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    """socket.connect and create_connection always raise. Runs after the suite guard."""
    assert freemyid_env is not None

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def plugin_dir(freemyid_env: Path) -> Path:
    folder = freemyid_env / "plugins"
    folder.mkdir(parents=True)
    (folder / "other.py").write_text(_OTHER, encoding="utf-8")
    return folder


def _broker(**over: object) -> Broker:
    data: dict[str, object] = {
        "id": "fakeb",
        "name": "Fake B",
        "url": "https://fakeb.example/",
        "category": "people_search",
        "domains": ["fakeb.example"],
        "opt_out_url": "https://fakeb.example/opt-out",
        "method": "web_form",
    }
    data.update(over)
    return Broker.model_validate(data)


def _generic(tier: Tier) -> type:
    return type(plugins.generic_submitter(tier))


def _write(folder: Path, body: str, name: str = "fakeplug.py") -> Path:
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path


def test_sockets_cannot_connect() -> None:
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.parametrize("kind", ["named", "path"])
@pytest.mark.parametrize(
    ("body", "reason"),
    [
        pytest.param(_IMPORT, plugins.IMPORT_ERROR, id="import_error"),
        pytest.param(_SYNTAX, plugins.IMPORT_ERROR, id="syntax_error"),
        pytest.param(_MISSING, plugins.MISSING_CLASS, id="missing_class"),
        pytest.param(_CONSTRUCT, plugins.CONSTRUCT_ERROR, id="construct_error"),
        pytest.param(_WRONG, plugins.WRONG_TYPE, id="wrong_type"),
    ],
)
def test_broken_plugin_falls_back(
    kind: str, body: str, reason: str, plugin_dir: Path,
) -> None:
    path = _write(plugin_dir, body)
    if kind == "named":
        broker = _broker(submitter="freemyid.submitters.fakeplug:Submitter")
        loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
        got = plugins.get_submitter(broker, Tier.AUTOMATIC)
        assert plugins.custom_submitter(broker) is None
    else:
        broker = _broker()
        loaded = plugins.load_submitter(broker, Tier.AUTOMATIC, plugin_path=path)
        got = plugins.get_submitter(broker, Tier.AUTOMATIC, plugin_path=path)
    generic = _generic(Tier.AUTOMATIC)
    assert loaded.reason == reason
    assert type(loaded.submitter) is generic
    assert type(got) is generic
    assert not (plugin_dir / "other.ran").exists()


def test_valid_plugin_is_used(plugin_dir: Path) -> None:
    _write(plugin_dir, _VALID)
    broker = _broker(submitter="freemyid.submitters.fakeplug:Submitter")
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    got = plugins.get_submitter(broker, Tier.AUTOMATIC)
    custom = plugins.custom_submitter(broker)
    assert loaded.reason is None
    assert getattr(loaded.submitter, "marker", None) == "gk346"
    assert type(loaded.submitter).__module__.startswith("_freemyid_plugin_")
    assert getattr(got, "marker", None) == "gk346"
    assert type(got).__module__.startswith("_freemyid_plugin_")
    assert custom is not None
    assert getattr(custom, "marker", None) == "gk346"
    assert type(got) is not _generic(Tier.AUTOMATIC)
    assert (plugin_dir / "imported.txt").is_file()
    assert not (plugin_dir / "called.txt").exists()
    assert not (plugin_dir / "other.ran").exists()


def test_explicit_path_loads_the_same_plugin(plugin_dir: Path) -> None:
    path = _write(plugin_dir, _VALID)
    loaded = plugins.load_submitter(_broker(), Tier.AUTOMATIC, plugin_path=path)
    assert loaded.reason is None
    assert getattr(loaded.submitter, "marker", None) == "gk346"
    assert not (plugin_dir / "called.txt").exists()
    assert not (plugin_dir / "other.ran").exists()


@pytest.mark.parametrize(
    ("tier", "class_name"),
    [(Tier.EMAIL, "EmailSubmitter"), (Tier.ASSISTED, "AssistedSubmitter")],
)
def test_other_tiers_do_not_import_a_plugin(
    tier: Tier, class_name: str, plugin_dir: Path,
) -> None:
    path = _write(plugin_dir, _VALID)
    broker = _broker(submitter="freemyid.submitters.fakeplug:Submitter")
    loaded = plugins.load_submitter(broker, tier, plugin_path=path)
    assert loaded.reason is None
    assert type(loaded.submitter).__name__ == class_name
    assert not (plugin_dir / "imported.txt").exists()
    assert not (plugin_dir / "other.ran").exists()


def test_outside_path_is_refused(
    tmp_path: Path, plugin_dir: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    outside = tmp_path / "outside.py"
    outside.write_text(_RAN, encoding="utf-8")
    sneaky = plugin_dir / ".." / ".." / "outside.py"
    assert sneaky.resolve() == outside.resolve()
    loaded = plugins.load_submitter(_broker(), Tier.AUTOMATIC, plugin_path=sneaky)
    got = plugins.get_submitter(_broker(), Tier.AUTOMATIC, plugin_path=outside)
    assert loaded.reason == plugins.PATH_REFUSED
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)
    assert type(got) is _generic(Tier.AUTOMATIC)
    assert not (tmp_path / "plugin.ran").exists()
    assert not outside.with_name("plugin.ran").exists()
    assert str(outside) not in caplog.text
    assert plugins.PATH_REFUSED in caplog.text
    assert not (plugin_dir / "other.ran").exists()


def test_symlink_to_outside_is_refused(tmp_path: Path, plugin_dir: Path) -> None:
    outside = tmp_path / "linked.py"
    outside.write_text(_RAN, encoding="utf-8")
    link = plugin_dir / "link.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    loaded = plugins.load_submitter(_broker(), Tier.AUTOMATIC, plugin_path=link)
    assert loaded.reason == plugins.PATH_REFUSED
    assert not (tmp_path / "plugin.ran").exists()
    assert not (plugin_dir / "plugin.ran").exists()
    assert not (plugin_dir / "other.ran").exists()


def test_repo_path_is_not_refused() -> None:
    repo_file = Path(plugins.__file__).resolve()
    assert plugins.plugin_path_allowed(repo_file)
    loaded = plugins.load_submitter(_broker(), Tier.AUTOMATIC, plugin_path=repo_file)
    # The module uses package-relative imports, so a loose load fails closed.
    # That is an import error, not a refusal, and it still falls back.
    assert loaded.reason == plugins.IMPORT_ERROR
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)


def test_arbitrary_module_string_is_not_imported() -> None:
    data = _broker().model_dump(mode="python")
    data["submitter"] = "os:system"
    broker = Broker.model_construct(**data)
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    assert loaded.reason == plugins.PATH_REFUSED
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)
    assert plugins.custom_submitter(broker) is None


def test_no_custom_has_no_reason() -> None:
    broker = _broker()
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    assert loaded.reason is None
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)
    assert plugins.custom_submitter(broker) is None
    assert type(plugins.get_submitter(broker, Tier.AUTOMATIC)) is _generic(Tier.AUTOMATIC)


def test_log_is_codes_only(plugin_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    _write(plugin_dir, _IMPORT)
    broker = _broker(submitter="freemyid.submitters.fakeplug:Submitter")
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    assert loaded.reason == plugins.IMPORT_ERROR
    text = caplog.text
    assert plugins.IMPORT_ERROR in text
    assert "RuntimeError" in text
    for word in ("Jane", "Testperson", "Springfield"):
        assert word not in text
    assert str(plugin_dir / "fakeplug.py") not in text


def test_entry_point_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)

    class Boom:
        name = "fakeb"

        def load(self) -> object:
            raise RuntimeError("Jane Q Testperson Springfield IL")

    def fake_entry_points(group: str) -> list[Boom]:
        assert group == "freemyid.submitters"
        return [Boom()]

    monkeypatch.setattr(plugins, "entry_points", fake_entry_points)
    broker = _broker()
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    assert loaded.reason == plugins.IMPORT_ERROR
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)
    assert type(plugins.get_submitter(broker, Tier.AUTOMATIC)) is _generic(Tier.AUTOMATIC)
    for word in ("Jane", "Testperson", "Springfield"):
        assert word not in caplog.text


def test_entry_point_wrong_type_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    class Bad:
        name = "fakeb"

        def load(self) -> object:
            return object()

    monkeypatch.setattr(plugins, "entry_points", lambda group: [Bad()])
    loaded = plugins.load_submitter(_broker(), Tier.AUTOMATIC)
    assert loaded.reason == plugins.WRONG_TYPE
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)


def test_named_package_missing_class_falls_back() -> None:
    broker = _broker(submitter="freemyid.submitters.web_form:NotAClass")
    loaded = plugins.load_submitter(broker, Tier.AUTOMATIC)
    assert loaded.reason == plugins.MISSING_CLASS
    assert type(loaded.submitter) is _generic(Tier.AUTOMATIC)
    assert plugins.custom_submitter(broker) is None
