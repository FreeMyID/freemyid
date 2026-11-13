"""Synthetic broker registry for scale tests (roadmap 0.7 "Registry at scale").

Every broker is fake and lives on `<id>.example.test` (RFC 6761 reserves `.test`; nothing
resolves). The mix follows the real registry's shape: about 70% email-route entries from
the state data-broker registries, 25% web forms (some covered by a parent's suppression
centre), 5% people-search sites with a `search_url_pattern`. Never load the private
registry in tests: it is not in the public repo.
"""
from __future__ import annotations

import random
from functools import lru_cache

import yaml

from freemyid.models import Registry

EMAIL_SHARE, WEB_SHARE = 0.70, 0.25   # the rest is people-search


def _kind(i: int) -> str:
    """Deterministic interleaved mix (not blocks), so any prefix has the same proportions."""
    r = random.Random(i).random()   # test data, not crypto
    if r < EMAIL_SHARE:
        return "email"
    if r < EMAIL_SHARE + WEB_SHARE:
        return "web_form"
    return "people_search"


def _broker(i: int, kind: str, parents: list[str]) -> dict:
    bid = f"fake{kind[0]}{i:05d}"
    dom = f"{bid.replace('_', '-')}.example.test"
    base: dict = {
        "id": bid,
        "name": f"Fake Broker {i:05d}",
        "url": f"https://{dom}/",
        "domains": [dom],
        "source_urls": [f"https://registry.example.test/brokers/{i:05d}"],
    }
    if kind == "email":
        base.update({
            "category": "data_broker",
            "method": "email",
            "opt_out_email": f"privacy@{dom}",
            "confirmation_domains": [dom],
            "priority": 10 + i % 20,
            "ca_registered": True,
            "recheck_interval_days": 90,
            "steps": ["Send a deletion request to the privacy address."],
            "legal_basis_notes": "Listed on a state data-broker registry (synthetic).",
        })
    elif kind == "web_form":
        base.update({
            "category": "people_search" if i % 2 else "background_check",
            "method": "web_form",
            "alt_methods": ["email"] if i % 5 == 0 else [],
            "opt_out_url": f"https://{dom}/opt-out",
            "has_captcha": i % 3 == 0,
            "required_fields": ["full_name", "city", "state", "email"],
            "confirmation_domains": [dom],
            "priority": 40 + i % 30,
            "recheck_interval_days": 30,
            "steps": ["Open the opt-out page.", "Search for your name.",
                      "Pick your listing and confirm by email."],
        })
        if i % 5 == 0:
            base["opt_out_email"] = f"privacy@{dom}"
        if parents and i % 7 == 0:
            base["covered_by"] = parents[i % len(parents)]
        if parents and i % 4 == 0:
            base["feeds_from"] = [parents[(i + 1) % len(parents)]]
    else:
        base.update({
            "category": "people_search",
            "method": "web_form",
            "opt_out_url": f"https://{dom}/removal",
            "search_url_pattern": f"https://{dom}/name/{{first}}-{{last}}/{{state}}/{{city}}",
            "search_access": "open",
            "search_url_checked": "2026-11-01",
            "slug_case": "title" if i % 2 else "lower",
            "listing_url_pattern": r"^/person/[a-z0-9-]+$",
            "required_fields": ["full_name", "city", "state"],
            "confirmation_domains": [dom],
            "priority": 70 + i % 30,
            "recheck_interval_days": 30,
            "steps": ["Search for your name.", "Open your listing.", "Press Remove."],
        })
    return base


def registry_dict(n: int, *, version: str | None = None) -> dict:
    kinds = [_kind(i) for i in range(n)]
    # suppression-centre parents: the first few people-search entries
    parents = [f"fakep{i:05d}" for i, k in enumerate(kinds) if k == "people_search"][:10]
    return {
        "version": version or f"2026.11.12-synthetic-{n}",
        "updated": "2026-11-12",
        "brokers": [_broker(i, k, parents) for i, k in enumerate(kinds)],
    }


@lru_cache(maxsize=4)
def registry_yaml(n: int) -> str:
    """The synthetic registry as YAML text (what load_registry parses)."""
    return yaml.safe_dump(registry_dict(n), sort_keys=False, allow_unicode=True)


@lru_cache(maxsize=4)
def registry(n: int) -> Registry:
    """The synthetic registry, validated (cached: models are treated as read-only)."""
    return Registry.model_validate(yaml.safe_load(registry_yaml(n)))


def mix(reg: Registry) -> dict[str, int]:
    out = {"email": 0, "web_form": 0, "people_search": 0}
    for b in reg.brokers:
        if b.search_url_pattern:
            out["people_search"] += 1
        elif b.method.value == "email":
            out["email"] += 1
        else:
            out["web_form"] += 1
    return out

