"""SEC-101: stacked Content-Encoding values are capped."""
from __future__ import annotations

import pytest

from freemyid.engine import exposure as ex


def test_two_encodings_are_accepted():
    assert len(ex._decoders("gzip")) == 1
    assert len(ex._decoders("deflate, gzip")) == 2
    assert ex._decoders("") == []


@pytest.mark.parametrize("header", ["gzip, gzip, gzip", "identity, gzip, deflate",
                                    ",".join(["gzip"] * 50)])
def test_more_than_two_stacked_encodings_are_refused(header):
    with pytest.raises(ex.FetchFailed) as e:
        ex._decoders(header)
    assert e.value.reason == "http_error"
