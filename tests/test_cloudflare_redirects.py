"""tools/cloudflare_redirects.py: offline checks (no network, no real token)."""
import http.client
import importlib.util
import io
import urllib.error
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "cloudflare_redirects", Path(__file__).resolve().parent.parent / "tools" / "cloudflare_redirects.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)  # importing must not run main()


class _TruncatedBody(io.BytesIO):
    def read(self, *a, **k):
        raise http.client.IncompleteRead(b'{"succ', 40)


def test_truncated_http_error_body_falls_back_to_status(monkeypatch):
    monkeypatch.setattr(cf, "token", lambda: "fake-token")

    def urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, _TruncatedBody())

    monkeypatch.setattr(cf.urllib.request, "urlopen", urlopen)
    r = cf.api("GET", "/zones?name=example.test")
    assert r == {"success": False, "errors": [{"message": "HTTP 403"}]}
    assert cf.errs(r) == ["HTTP 403"]
