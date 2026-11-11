"""Invisible Unicode in a URL or host never yields an allowed host (WO-236 finding)."""
import pytest

from freemyid.netpolicy import host_of


@pytest.mark.parametrize("ch", ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
                                "\u2060", "\ufeff", "\u202e", "\xad", "\ue000"])
@pytest.mark.parametrize("template", ["https://fake{c}people.example/",
                                      "https://fakepeople.example{c}/", "fake{c}people.example"])
def test_invisible_or_private_char_is_rejected(ch: str, template: str) -> None:
    assert host_of(template.format(c=ch)) is None


def test_plain_hosts_still_parse() -> None:
    assert host_of("https://FakePeople.example./x") == "fakepeople.example"
    assert host_of("https://xn--fakepeople-9za.example/") == "xn--fakepeople-9za.example"
