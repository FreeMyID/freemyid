"""Property-style checks for network-policy parsing and allow-list invariants."""
from __future__ import annotations

import unicodedata

import pytest

from freemyid.netpolicy import NetPolicy, captcha_subresource_allowed, host_of


@pytest.mark.parametrize("raw", [
    "https://FAKEPEOPLE.EXAMPLE./optout",
    "FAKEPEOPLE.EXAMPLE.",
    "https://[::1]/",
    "[::1]",
    "::1",
    "::ffff:127.0.0.1",
    "https://fakepeople.example:443/",
    "fakepeople.example:8443",
    "https://fake%2epeople.example/",
    "https://xn--fakepeople-9za.example/",
    "https://@fakepeople.example/",
    "https://fakepeople.example\t/",
    "https://fakepeople.example\u00a0/",
    pytest.param(
        "https://fake\u200bpeople.example/",
        marks=pytest.mark.xfail(
            strict=True,
            reason="SEC finding, fix owner: orchestrator (netpolicy.py contract): host_of "
                   "keeps invisible Unicode format (Cf) characters such as zero-width "
                   "chars instead of returning None (src/freemyid/netpolicy.py:38-56)",
        ),
    ),
    "javascript:alert(1)",
    "data:text/plain,fakepeople.example",
    "//fakepeople.example/path",
    "https://evilfakepeople.example/",
    "https://fakepeople.example.evil.example/",
    "https://fakepeople.example\\@evil.example/",
    "https://fakepeople.example/\npath",
    "https://fakepeople.example/\x00path",
    "https://fakepeople.example/\x7fpath",
    "https://fakepeople.example/#fragment",
    "https://fakepeople.example?query=1",
    "https://user:pass@fakepeople.example/",
    "https://fakepeople.example:443/path",
    "https://fakepeople.example:99999/",
    "https://[invalid/",
    "https://fakepeople.example..",
    "fakepeople.example ",
    " fakepeople.example",
    "https://fake people.example/",
    "https://fakepeople.example\u2028/",
    pytest.param(
        "https://fakepeople.example\u200e/",
        marks=pytest.mark.xfail(
            strict=True,
            reason="SEC finding, fix owner: orchestrator (netpolicy.py contract): host_of "
                   "keeps invisible Unicode format (Cf) characters such as zero-width "
                   "chars instead of returning None (src/freemyid/netpolicy.py:38-56)",
        ),
    ),
    "https://fakepeople.example%2f.evil.example/",
    "https://fakepeople.example.\u00a0/",
])
def test_host_of_returns_normalized_idempotent_values_for_odd_inputs(raw: str) -> None:
    result = host_of(raw)
    if result is None:
        return

    assert result == result.lower()
    assert not result.endswith(".")
    assert not any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F
                   for char in result)
    assert "\\" not in result
    assert not any(unicodedata.category(char) == "Cf" for char in result)
    assert host_of(result) == result


def test_allow_list_suffix_matching_is_boundary_safe_and_case_stable(fake_registry) -> None:
    policy = NetPolicy(fake_registry)

    assert policy.is_allowed("https://fakepeople.example/optout")
    assert policy.is_allowed("https://www.fakepeople.example/optout")
    assert policy.is_allowed("https://FAKEPEOPLE.EXAMPLE./optout")
    assert policy.is_allowed("https://WWW.FAKEPEOPLE.EXAMPLE./optout")
    assert not policy.is_allowed("https://evilfakepeople.example/optout")
    assert not policy.is_allowed("https://fakepeople.example.evil.example/optout")


def test_for_broker_is_a_subset_and_drops_loopback_without_opt_in(fake_registry) -> None:
    policy = NetPolicy(fake_registry)
    candidates = [
        "fakepeople.example",
        "sub.fakepeople.example",
        "evilfakepeople.example",
        "fakepeople.example.evil.example",
        "localhost",
        "127.0.0.2",
        "x.localhost",
        "::1",
    ]

    result = policy.for_broker(candidates[:2], candidates[2:])

    assert all(policy.is_allowed(host) for host in result)
    assert result == {"fakepeople.example", "sub.fakepeople.example"}
    assert not ({"localhost", "127.0.0.2", "x.localhost", "::1"} & result)


def test_for_broker_can_keep_loopback_only_when_policy_opts_in(fake_registry) -> None:
    policy = NetPolicy(fake_registry, allow_loopback=True)

    result = policy.for_broker(
        ["fakepeople.example"], ["localhost", "127.0.0.1", "::1", "127.0.0.2"]
    )

    assert all(policy.is_allowed(host) for host in result)
    assert result == {"fakepeople.example", "localhost", "127.0.0.1", "::1"}


def test_with_loopback_returns_an_independent_copy(fake_registry) -> None:
    policy = NetPolicy(fake_registry)
    original_allowed = set(policy.allowed)
    original_loopback_setting = policy.allow_loopback

    copied = policy.with_loopback()

    assert copied is not policy
    assert copied.allow_loopback is True
    assert {"localhost", "127.0.0.1", "::1"} <= copied.allowed
    assert policy.allowed == original_allowed
    assert policy.allow_loopback is original_loopback_setting is False
    copied.allowed.add("added-only-to-copy.example")
    assert "added-only-to-copy.example" not in policy.allowed


@pytest.mark.parametrize(("url", "allowed"), [
    ("https://www.google.com:443/recaptcha/api2/anchor", True),
    ("https://www.google.com:8443/recaptcha/api2/anchor", False),
    ("https://www.google.com/recaptcha", False),
    ("https://www.google.com/recaptchaX/anchor", False),
    ("https://sub.www.google.com/recaptcha/api2/anchor", False),
    ("https://api.hcaptcha.com/checksiteconfig", True),
])
def test_captcha_widget_host_port_and_path_rules(url: str, allowed: bool) -> None:
    assert captcha_subresource_allowed(url, is_main_frame_navigation=False) is allowed


@pytest.mark.parametrize("url", [
    "https://www.google.com/recaptcha/api2/anchor",
    "https://api.hcaptcha.com/checksiteconfig",
])
def test_captcha_widget_is_never_allowed_as_top_level_navigation(url: str) -> None:
    assert not captcha_subresource_allowed(url, is_main_frame_navigation=True)
