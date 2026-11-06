"""Public sample registry vs private full registry: precedence, source reporting, family install."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from freemyid import paths, registry
from freemyid.models import Method, VerificationStatus

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
    full = ROOT / "brokers" / "registry.yaml"
    if not full.exists():
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
