"""WO-604: a broker whose search page we can't read is never fetched.

Fetching it would only tell the broker that someone is looking this person up (name and city
in the URL) for no possible benefit. Fake people and fake brokers on .example hosts only.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from freemyid import config as cfgmod
from freemyid.engine import exposure as ex
from freemyid.models import Broker, PersonName, Registry, SearchSpec
from tests.conftest import make_profile

T0 = datetime(2026, 11, 1, tzinfo=UTC)
IDS = ("noparsea", "noparseb")


def _pattern(bid: str) -> str:
    return f"https://{bid}.example/name/{{first}}-{{last}}/{{city}}-{{state}}"


def _broker(bid: str, search: SearchSpec | None) -> Broker:
    return Broker(id=bid, name=f"Fake {bid}", url=f"https://{bid}.example/",
                  category="people_search", domains=[f"{bid}.example"], method="email",
                  opt_out_email=f"privacy@{bid}.example", search_url_pattern=_pattern(bid),
                  search_access="open", search=search)


def must_not_fetch(broker, url):
    raise AssertionError(f"fetched a page with no parser: {broker.id}")


@pytest.mark.parametrize("search", [None, SearchSpec(result_selector=None)],
                         ids=["no_search_spec", "no_result_selector"])
def test_no_parser_means_no_fetch_and_no_gap(store, search) -> None:
    p = make_profile(previous_names=[PersonName(first="Jane", last="Oldname")])
    store.save_profile(p)
    reg = Registry(version="2026.11.11-test", updated=T0.date(),
                   brokers=[_broker(b, search) for b in IDS])
    slept: list[float] = []
    cfg = cfgmod.Config(min_delay_s=1.0, max_delay_s=2.0)
    res = ex.scan_exposure(store, p.id, registry=reg, cfg=cfg,
                           fetch=must_not_fetch, browser_fetch=must_not_fetch,
                           now=T0, sleep=slept.append, old_addresses=True,
                           previous_names=True, refresh=True)
    assert [(e.broker_id, e.status, e.reason) for e in res.entries] == [
        (b, "check_by_hand", "no_parser") for b in IDS]
    assert slept == []                 # no polite gap spent between two unread sites
    checks = [e for e in store.events(p.id) if e.action == ex.CHECK_ACTION]
    assert sorted(e.broker_id for e in checks) == list(IDS)
    for ev in checks:
        assert ev.detail["status"] == "check_by_hand" and ev.detail["reason"] == "no_parser"
        for v in ev.detail.values():   # ids/enums/counts only
            assert v is None or isinstance(v, bool | int) or v in ("check_by_hand", "no_parser")
    blob = repr([e.detail for e in store.events(p.id)])
    for pii in ("Jane", "Testperson", "Oldname", "Springfield", ".example/name"):
        assert pii not in blob


def test_read_refuses_before_fetch(store) -> None:
    p = make_profile()
    with pytest.raises(ex.FetchFailed) as e:
        ex._read(p, _broker(IDS[0], None), _pattern(IDS[0]), must_not_fetch, T0)
    assert e.value.reason == "no_parser"
