"""Submitter lookup (order from interfaces.Submitter):

1. broker.submitter 'freemyid.submitters.<module>:<Class>' (namespace enforced here too)
2. entry point group 'freemyid.submitters' keyed by broker id
3. module freemyid.submitters.<broker_id> with a class named `Submitter`
4. generic by tier: AUTOMATIC -> WebFormSubmitter, EMAIL -> EmailSubmitter,
   ASSISTED -> AssistedSubmitter

A broken custom submitter falls back to the generic one. `load_submitter` records a
reason code (`import_error`, `missing_class`, `construct_error`, `wrong_type`,
`path_refused`) and does not raise. Files load only from the data folder or the repo.
A missing `freemyid.submitters.<leaf>` module may be supplied by `<data>/plugins/<leaf>.py`.

v1 ships no per-broker modules (PLAN_V1 D1). Steps 1-3 stay for later exceptions.
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import re
import sys
import uuid
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

from ..interfaces import Submitter
from ..models import Broker, Tier

log = logging.getLogger(__name__)

_GENERIC_NAMES = {"base", "assisted", "email", "web_form"}
# Same shape as models._SUBMITTER_RE. Anything else is refused before import.
_SUBMITTER_RE = re.compile(r"^freemyid\.submitters\.[a-z0-9_.]+:[A-Za-z_][A-Za-z0-9_]*$")
_MODULE_RE = re.compile(r"^freemyid\.submitters\.[a-z0-9_.]+$")
_LEAF_RE = re.compile(r"^freemyid\.submitters\.([a-z0-9_]+)$")
_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BROKER_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")

IMPORT_ERROR = "import_error"
MISSING_CLASS = "missing_class"
CONSTRUCT_ERROR = "construct_error"
WRONG_TYPE = "wrong_type"
PATH_REFUSED = "path_refused"

_MISSING = object()


class SubmitterLoad(NamedTuple):
    """Submitter chosen for a broker, plus why a custom plugin was not used.

    `reason` is None when the custom plugin loaded, or when no custom plugin was
    requested. A code means the generic submitter was used because the custom one failed.
    """

    submitter: Submitter
    reason: str | None


def _fail(broker_id: str, reason: str, exc: BaseException | None = None) -> None:
    """Log a reason code and, when we have one, the exception type. Never the message."""
    if exc is None:
        log.warning("custom submitter for %s unavailable: %s", broker_id, reason)
    else:
        log.warning(
            "custom submitter for %s unavailable: %s %s",
            broker_id, reason, type(exc).__name__,
        )


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    # src/freemyid/engine/plugins.py -> repo root is parents[3]
    if len(here.parents) < 4:
        return None
    repo = here.parents[3]
    if (repo / "pyproject.toml").is_file() and (repo / "src" / "freemyid").is_dir():
        return repo
    return None


def _allowed_roots() -> tuple[Path, ...]:
    """Data folder (user home and bundled data) and the repo checkout, if this is one."""
    roots: list[Path] = []
    repo = _repo_root()
    if repo is not None:
        roots.append(repo)
    try:
        from .. import paths

        roots.append(paths.bundled_data_dir().resolve())
        roots.append(paths.home().resolve())
    except OSError:
        pass
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return tuple(unique)


def _contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def plugin_path_allowed(path: Path) -> bool:
    """True when `path` resolves inside the data folder or the repo. Does not import it."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(_contained(resolved, root) for root in _allowed_roots())


def _submitters_root() -> Path | None:
    try:
        import freemyid.submitters as pkg
    except Exception as exc:  # noqa: BLE001 - a broken package must not stop the run
        log.warning("custom submitter unavailable: %s %s", IMPORT_ERROR, type(exc).__name__)
        return None
    pkg_paths = getattr(pkg, "__path__", None)
    if pkg_paths:
        return Path(next(iter(pkg_paths))).resolve()
    file = getattr(pkg, "__file__", None)
    if isinstance(file, str):
        return Path(file).resolve().parent
    return None


def _origin_allowed(origin: str) -> bool:
    if not origin or origin in {"namespace", "built-in"}:
        return False
    try:
        resolved = Path(origin).resolve()
    except OSError:
        return False
    roots = list(_allowed_roots())
    pkg = _submitters_root()
    if pkg is not None:
        roots.append(pkg)
    return any(_contained(resolved, root) for root in roots)


def _data_plugin_file(mod_name: str) -> Path | None:
    """`<data>/plugins/<leaf>.py` for a single-segment submitter module, if that file exists."""
    match = _LEAF_RE.fullmatch(mod_name)
    if match is None:
        return None
    leaf = match.group(1)
    if leaf in _GENERIC_NAMES:
        return None
    try:
        from .. import paths

        candidate = (paths.home() / "plugins" / f"{leaf}.py").resolve()
    except OSError:
        return None
    if candidate.is_file() and plugin_path_allowed(candidate):
        return candidate
    return None


def _build(obj: object, broker_id: str) -> tuple[Submitter | None, str]:
    if not isinstance(obj, type):
        _fail(broker_id, WRONG_TYPE)
        return None, WRONG_TYPE
    try:
        ok = issubclass(obj, Submitter)
    except TypeError as exc:
        _fail(broker_id, WRONG_TYPE, exc)
        return None, WRONG_TYPE
    if not ok:
        _fail(broker_id, WRONG_TYPE)
        return None, WRONG_TYPE
    try:
        return obj(), ""
    except Exception as exc:  # noqa: BLE001 - construction must not stop the run
        _fail(broker_id, CONSTRUCT_ERROR, exc)
        return None, CONSTRUCT_ERROR


def _class_on(module: ModuleType, class_name: str, broker_id: str) -> tuple[Submitter | None, str]:
    if _CLASS_RE.fullmatch(class_name) is None:
        _fail(broker_id, MISSING_CLASS)
        return None, MISSING_CLASS
    obj = getattr(module, class_name, _MISSING)
    if obj is _MISSING:
        _fail(broker_id, MISSING_CLASS)
        return None, MISSING_CLASS
    return _build(obj, broker_id)


def _exec_plugin_file(path: Path, broker_id: str) -> tuple[ModuleType | None, str | None]:
    """Execute one file. The module name is private, so a sibling file is not imported."""
    if not plugin_path_allowed(path):
        _fail(broker_id, PATH_REFUSED)
        return None, PATH_REFUSED
    try:
        resolved = path.resolve()
    except OSError as exc:
        _fail(broker_id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR
    if resolved.suffix.lower() != ".py" or not resolved.is_file():
        _fail(broker_id, IMPORT_ERROR)
        return None, IMPORT_ERROR
    mod_name = f"_freemyid_plugin_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(mod_name, resolved)
    loader = spec.loader if spec is not None else None
    exec_module = getattr(loader, "exec_module", None)
    if spec is None or exec_module is None:
        _fail(broker_id, IMPORT_ERROR)
        return None, IMPORT_ERROR
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        exec_module(module)
    except Exception as exc:  # noqa: BLE001 - import errors must not stop the run
        _fail(broker_id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR
    finally:
        sys.modules.pop(mod_name, None)
    return module, None


def _load_from_path(
    path: Path, class_name: str, broker_id: str,
) -> tuple[Submitter | None, str]:
    module, reason = _exec_plugin_file(path, broker_id)
    if module is None:
        return None, reason or IMPORT_ERROR
    return _class_on(module, class_name, broker_id)


def _import_allowed_module(mod_name: str, broker_id: str) -> tuple[ModuleType | None, str | None]:
    """Import `mod_name` only when its file is already inside an allowed root.

    `(None, None)` means the module is not installed. That is not a failure for the
    optional broker-id step.
    """
    if _MODULE_RE.fullmatch(mod_name) is None:
        _fail(broker_id, PATH_REFUSED)
        return None, PATH_REFUSED
    try:
        spec = importlib.util.find_spec(mod_name)
    except (ImportError, ValueError, AttributeError) as exc:
        _fail(broker_id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR
    if spec is None:
        return None, None
    origin = spec.origin or ""
    if not _origin_allowed(origin):
        _fail(broker_id, PATH_REFUSED)
        return None, PATH_REFUSED
    try:
        imported = importlib.import_module(mod_name)
    except Exception as exc:  # noqa: BLE001 - import errors must not stop the run
        _fail(broker_id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR
    if not isinstance(imported, ModuleType):
        _fail(broker_id, IMPORT_ERROR)
        return None, IMPORT_ERROR
    return imported, None


def _explicit_submitter(broker: Broker) -> tuple[Submitter | None, str | None, bool]:
    """Return `(instance, reason, stop)`. `stop` means do not try a later source."""
    spec = broker.submitter
    if not spec:
        return None, None, False
    if _SUBMITTER_RE.fullmatch(spec) is None:
        _fail(broker.id, PATH_REFUSED)
        return None, PATH_REFUSED, True
    mod_name, _, class_name = spec.partition(":")
    module, reason = _import_allowed_module(mod_name, broker.id)
    if reason == PATH_REFUSED:
        return None, PATH_REFUSED, True
    if module is None and reason is None:
        data_file = _data_plugin_file(mod_name)
        if data_file is None:
            _fail(broker.id, IMPORT_ERROR)
            return None, IMPORT_ERROR, False
        inst, file_reason = _load_from_path(data_file, class_name, broker.id)
        if inst is not None:
            return inst, None, True
        # A wrong type is the named plugin, not a miss. Other failures can fall through.
        return None, file_reason, file_reason == WRONG_TYPE
    if module is None:
        return None, reason or IMPORT_ERROR, False
    inst, built = _class_on(module, class_name, broker.id)
    if inst is not None:
        return inst, None, True
    return None, built, built == WRONG_TYPE


def _entry_point_submitter(broker: Broker) -> tuple[Submitter | None, str | None, bool]:
    try:
        found = entry_points(group="freemyid.submitters")
    except Exception as exc:  # noqa: BLE001 - a broken plugin must not stop the run
        _fail(broker.id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR, True
    try:
        matched = False
        for ep in found:
            if ep.name != broker.id:
                continue
            matched = True
            try:
                loaded = ep.load()
            except Exception as exc:  # noqa: BLE001 - a broken plugin must not stop the run
                _fail(broker.id, IMPORT_ERROR, exc)
                return None, IMPORT_ERROR, True
            inst, built = _build(loaded, broker.id)
            if inst is not None:
                return inst, None, True
            return None, built, True
        if not matched:
            return None, None, False
    except Exception as exc:  # noqa: BLE001 - a broken plugin must not stop the run
        _fail(broker.id, IMPORT_ERROR, exc)
        return None, IMPORT_ERROR, True
    return None, None, False


def _broker_id_module(broker: Broker) -> tuple[Submitter | None, str | None, bool]:
    if broker.id in _GENERIC_NAMES or _BROKER_ID_RE.fullmatch(broker.id) is None:
        return None, None, False
    module, reason = _import_allowed_module(f"freemyid.submitters.{broker.id}", broker.id)
    if module is None and reason is None:
        return None, None, False
    if module is None:
        return None, reason, True
    inst, built = _class_on(module, "Submitter", broker.id)
    if inst is not None:
        return inst, None, True
    return None, built, True


def _lookup_custom(broker: Broker) -> tuple[Submitter | None, str | None]:
    inst, reason, stop = _explicit_submitter(broker)
    if inst is not None or stop:
        return inst, reason
    ep_inst, ep_reason, ep_stop = _entry_point_submitter(broker)
    if ep_inst is not None:
        return ep_inst, None
    if ep_stop:
        return None, ep_reason or reason
    if ep_reason is not None and reason is None:
        reason = ep_reason
    id_inst, id_reason, id_stop = _broker_id_module(broker)
    if id_inst is not None:
        return id_inst, None
    if id_stop:
        return None, id_reason or reason
    return None, reason


def custom_submitter(broker: Broker) -> Submitter | None:
    try:
        found, _reason = _lookup_custom(broker)
    except Exception as exc:  # noqa: BLE001 - a broken plugin must not stop the run
        _fail(broker.id, IMPORT_ERROR, exc)
        return None
    return found


def generic_submitter(tier: Tier) -> Submitter:
    if tier == Tier.AUTOMATIC:
        from ..submitters.web_form import WebFormSubmitter
        return WebFormSubmitter()
    if tier == Tier.EMAIL:
        from ..submitters.email import EmailSubmitter
        return EmailSubmitter()
    from ..submitters.assisted import AssistedSubmitter
    return AssistedSubmitter()


def load_submitter(
    broker: Broker,
    tier: Tier,
    *,
    plugin_path: Path | None = None,
    plugin_class: str = "Submitter",
) -> SubmitterLoad:
    """Resolve a submitter. Failures fall back to generic and set `reason`. Never raises.

    `plugin_path` is loaded only when it sits in the data folder or the repo, and only on
    the Automatic tier. A path outside those roots is `path_refused` and is not imported.
    Custom plugins are ignored for other tiers (the file is not imported).
    """
    try:
        return _load_submitter(broker, tier, plugin_path=plugin_path, plugin_class=plugin_class)
    except Exception as exc:  # noqa: BLE001 - a broken plugin must not stop the run
        _fail(broker.id, IMPORT_ERROR, exc)
        return SubmitterLoad(generic_submitter(tier), IMPORT_ERROR)


def _load_submitter(
    broker: Broker,
    tier: Tier,
    *,
    plugin_path: Path | None,
    plugin_class: str,
) -> SubmitterLoad:
    if plugin_path is not None and not plugin_path_allowed(plugin_path):
        _fail(broker.id, PATH_REFUSED)
        return SubmitterLoad(generic_submitter(tier), PATH_REFUSED)
    if tier != Tier.AUTOMATIC:
        return SubmitterLoad(generic_submitter(tier), None)
    if plugin_path is not None:
        if _CLASS_RE.fullmatch(plugin_class) is None:
            _fail(broker.id, MISSING_CLASS)
            return SubmitterLoad(generic_submitter(tier), MISSING_CLASS)
        inst, path_reason = _load_from_path(plugin_path, plugin_class, broker.id)
        if inst is not None:
            return SubmitterLoad(inst, None)
        return SubmitterLoad(generic_submitter(tier), path_reason)
    found, why = _lookup_custom(broker)
    if found is not None:
        return SubmitterLoad(found, None)
    return SubmitterLoad(generic_submitter(tier), why)


def get_submitter(
    broker: Broker,
    tier: Tier,
    *,
    plugin_path: Path | None = None,
    plugin_class: str = "Submitter",
) -> Submitter:
    """Custom submitters only apply to the Automatic tier; others use the generic path.

    A broken custom plugin falls back to generic and does not raise into the runner.
    The reason code is on `load_submitter`.
    """
    return load_submitter(
        broker, tier, plugin_path=plugin_path, plugin_class=plugin_class,
    ).submitter
