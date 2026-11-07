"""Public sample registry vs private full registry: precedence, source reporting, family install."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from freemyid import paths, registry
from freemyid.models import Method, VerificationStatus
from tests.conftest import full_registry_path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = ROOT / "brokers" / "registry.sample.yaml"
MIN = FIXTURES / "registry_min.yaml"


def test_sample_registry_validates_and_has_tier_spread():
    reg = registry.load_registry(SAMPLE)
    ids = {b.id for b in reg.brokers}
    assert 15 <= len(ids) <= 50
    assert "ca_drop" in ids                         # runner special-cases CA DROP
    assert any(b.opt_out_email for b in reg.brokers)                       # Email tier
    assert any(b.method is Method.WEB_FORM and not b.form for b in reg.brokers)  # Assisted
    assert any(b.form and b.verification_status is VerificationStatus.VERIFIED
               for b in reg.brokers)                                       # Automatic
    for b in reg.brokers:
        for d in [*b.domains, *b.confirmation_domains]:
            assert "." in d and "/" not in d and ":" not in d, (b.id, d)


def test_sample_is_a_subset_of_full_when_present():
    full = full_registry_path()
    if full is None:
        pytest.skip("full registry not present (public checkout)")
    full_by_id = {b.id: b for b in registry.load_registry(full).brokers}
    for b in registry.load_registry(SAMPLE).brokers:
        assert b == full_by_id[b.id], b.id


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "bundled"
    (d / "brokers").mkdir(parents=True)
    shutil.copytree(ROOT / "schema", d / "schema")
    shutil.copyfile(SAMPLE, d / "brokers" / "registry.sample.yaml")
    monkeypatch.setattr(paths, "bundled_data_dir", lambda: d)
    return d


def test_precedence_sample_only(data_dir):
    assert registry.registry_source() == "sample"
    assert registry.bundled_registry_path().name == "registry.sample.yaml"
    assert registry.load_registry().version.endswith("-sample")


def test_precedence_full_beats_sample(data_dir):
    shutil.copyfile(MIN, data_dir / "brokers" / "registry.yaml")
    assert registry.registry_source() == "full"
    assert {b.id for b in registry.load_registry().brokers} == {"fakepeople", "fakemail"}


def test_precedence_update_beats_everything(data_dir):
    shutil.copyfile(MIN, data_dir / "brokers" / "registry.yaml")
    shutil.copyfile(MIN, paths.registry_cache_path())
    assert registry.registry_source() == "update"
    assert registry.load_registry().brokers


def test_default_load_works_without_full_registry(data_dir):
    assert not (data_dir / "brokers" / "registry.yaml").exists()
    assert registry.load_registry().brokers


def test_family_registry_installs_through_validation(data_dir):
    v, n = registry.install_family_registry(MIN)
    assert n == 2 and v
    assert registry.registry_source() == "update"
    assert paths.registry_cache_path().read_bytes() == MIN.read_bytes()


@pytest.mark.parametrize("bad", [b"brokers: [", b"version: x\n", b"\xff\xfe", b""])
def test_family_registry_rejects_invalid_and_keeps_working_copy(data_dir, bad):
    shutil.copyfile(MIN, paths.registry_cache_path())
    before = paths.registry_cache_path().read_bytes()
    with pytest.raises(registry.RegistryError):
        registry.install_family_registry(bad)
    assert paths.registry_cache_path().read_bytes() == before


def test_family_registry_size_cap(data_dir, monkeypatch):
    monkeypatch.setattr(registry, "MAX_REGISTRY_BYTES", 10)
    with pytest.raises(registry.RegistryError):
        registry.install_family_registry(MIN)
    assert not paths.registry_cache_path().exists()


def test_find_family_registry_only_when_frozen(tmp_path, monkeypatch):
    import sys
    assert registry.find_family_registry() is None
    exe = tmp_path / "app" / "FreeMyID.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert registry.find_family_registry() is None
    (exe.parent / "registry.yaml").write_text("x")
    assert registry.find_family_registry() == exe.parent / "registry.yaml"


# --------------------------------------------------------------------------- family registry
# (registry.yaml next to an installed, frozen exe; source "family")


@pytest.fixture
def frozen_exe(tmp_path, monkeypatch):
    import sys
    exe = tmp_path / "app" / "FreeMyID.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    return exe


def test_family_registry_beside_frozen_exe_is_used(data_dir, frozen_exe):
    shutil.copyfile(SAMPLE, data_dir / "brokers" / "registry.yaml")   # a full one too
    shutil.copyfile(MIN, frozen_exe.parent / "registry.yaml")
    assert registry.registry_source() == "family"
    assert {b.id for b in registry.load_registry().brokers} == {"fakepeople", "fakemail"}
    assert registry.registry_source() == "family" and not registry.load_warnings


def test_update_cache_beats_family(data_dir, frozen_exe):
    shutil.copyfile(MIN, frozen_exe.parent / "registry.yaml")
    shutil.copyfile(SAMPLE, paths.registry_cache_path())
    assert registry.registry_source() == "update"
    assert registry.load_registry().version.endswith("-sample")
    assert registry.registry_source() == "update"


def test_invalid_family_file_raises_when_loaded_explicitly(data_dir, frozen_exe):
    fam = frozen_exe.parent / "registry.yaml"
    fam.write_text("brokers: [\n", encoding="utf-8")
    assert registry.find_family_registry() == fam
    with pytest.raises(registry.RegistryError):
        registry.load_registry(fam)


def test_invalid_family_file_falls_back_with_warning(data_dir, frozen_exe):
    (frozen_exe.parent / "registry.yaml").write_text("version: x\n", encoding="utf-8")
    reg = registry.load_registry()
    assert reg.version.endswith("-sample")
    assert registry.registry_source() == "sample"
    assert len(registry.load_warnings) == 1 and "family" in registry.load_warnings[0]


# --------------------------------------------------------------------------- hardening


def test_alias_bomb_refused(tmp_path):
    with pytest.raises(registry.RegistryError):
        registry.validate_text("a: &a [1,2]\nb: [*a,*a]\n")
    bomb = tmp_path / "bomb.yaml"
    lines = ["a0: &a0 [x, x, x, x, x, x, x, x, x]"]
    lines += [f"a{i}: &a{i} [*a{i-1}, *a{i-1}, *a{i-1}, *a{i-1}]" for i in range(1, 12)]
    bomb.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(registry.RegistryError):
        registry.load_registry(bomb)
    with pytest.raises(registry.RegistryError):
        registry.install_family_registry(bomb)
    assert not paths.registry_cache_path().exists()


def test_scalar_alias_still_loads(tmp_path):
    text = MIN.read_text(encoding="utf-8")
    body = text.replace("    url: https://fakepeople.example/\n",
                        "    url: &home https://fakepeople.example/\n", 1)
    body = body.replace("    opt_out_url: https://fakepeople.example/optout\n",
                        "    opt_out_url: *home\n", 1)
    assert body.count("&home") == 1 and body.count("*home") == 1
    out = tmp_path / "alias.yaml"
    out.write_text(body, encoding="utf-8")
    reg = registry.load_registry(out)
    b = reg.get("fakepeople")
    assert str(b.opt_out_url) == str(b.url) == "https://fakepeople.example/"


def test_corrupt_update_cache_falls_back_to_family(data_dir, frozen_exe):
    shutil.copyfile(MIN, frozen_exe.parent / "registry.yaml")
    paths.registry_cache_path().write_text("brokers: [", encoding="utf-8")
    reg = registry.load_registry()
    assert {b.id for b in reg.brokers} == {"fakepeople", "fakemail"}
    assert registry.registry_source() == "family"
    assert len(registry.load_warnings) == 1 and "update" in registry.load_warnings[0]


def test_corrupt_update_cache_falls_back_to_full(data_dir):
    shutil.copyfile(MIN, data_dir / "brokers" / "registry.yaml")
    paths.registry_cache_path().write_bytes(b"\xff\xfe not utf-8")
    assert {b.id for b in registry.load_registry().brokers} == {"fakepeople", "fakemail"}
    assert registry.registry_source() == "full"
    assert registry.load_warnings and "update" in registry.load_warnings[0]


def test_corrupt_update_cache_falls_back_to_sample(data_dir):
    paths.registry_cache_path().write_text("version: x\n", encoding="utf-8")
    assert registry.load_registry().version.endswith("-sample")
    assert registry.registry_source() == "sample"
    assert len(registry.load_warnings) == 1
    # the fallback is only reported while that broken cache is still the preferred one
    paths.registry_cache_path().unlink()
    assert registry.registry_source() == "sample"


def test_oversized_update_cache_falls_back(data_dir, monkeypatch):
    shutil.copyfile(MIN, paths.registry_cache_path())
    monkeypatch.setattr(registry, "MAX_REGISTRY_BYTES", 10)
    with pytest.raises(registry.RegistryError):     # the sample is bigger than 10 bytes too
        registry.load_registry()
    assert len(registry.load_warnings) == 2


def test_explicit_path_never_falls_back(data_dir, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("brokers: [", encoding="utf-8")
    with pytest.raises(registry.RegistryError):
        registry.load_registry(bad)
    with pytest.raises(registry.RegistryError):
        registry.load_registry(tmp_path / "missing.yaml")
    assert not registry.load_warnings


def test_cli_registry_source_plain_prints_one_word(data_dir):
    from typer.testing import CliRunner

    from freemyid.cli import app
    paths.registry_cache_path().write_text("brokers: [", encoding="utf-8")   # forces fallback
    r = CliRunner().invoke(app, ["registry", "source", "--plain"])
    assert r.exit_code == 0, r.output
    assert r.stdout.split() == ["sample"] and r.stdout.strip() == "sample"
    r = CliRunner().invoke(app, ["registry", "source"])
    assert r.exit_code == 0 and "sample" in r.stdout and "warning" in r.stdout
