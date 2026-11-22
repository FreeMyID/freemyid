"""Home-page A/B/C test (docs/AB_TEST.md): the edge worker (worker/ab-test/src/index.js) and the report
(tools/ab_report.py). The worker runs under Node with stubbed fetch and D1, so no network is used."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "worker/ab-test/src/index.js"
WRANGLER = ROOT / "worker/ab-test/wrangler.jsonc"

spec = importlib.util.spec_from_file_location("ab_report", ROOT / "tools/ab_report.py")
assert spec and spec.loader
ab_report = importlib.util.module_from_spec(spec)
sys.modules["ab_report"] = ab_report  # dataclasses look the module up
spec.loader.exec_module(ab_report)

HARNESS = r"""
import * as w from %(worker)s;
const points = [], fetched = [], waits = [];
globalThis.fetch = async (req) => {
  const u = new URL(req.url ?? req);
  fetched.push(u.pathname);
  if (u.pathname === globalThis.missing) return new Response("missing", { status: 404 });
  const html = !/\.(css|woff2|png)$/.test(u.pathname);
  return new Response("<html>" + u.pathname, { status: 200, headers: {
    "content-type": html ? "text/html; charset=utf-8" : "text/css", etag: "x", "cache-control": "max-age=600" } });
};
const DB = { prepare: (sql) => ({ bind: (...args) => ({ run: async () => { points.push({ sql, args }); } }) }) };
const ctx = { waitUntil: (p) => waits.push(p) };
const env = (extra = {}) => ({ AB_ENABLED: "1", DB, ...extra });
const ua = { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0" };
const go = async (path, e = env(), headers = ua, method = "GET") => {
  points.length = 0; fetched.length = 0; waits.length = 0;
  const r = await w.default.fetch(new Request("https://freemyid.org" + path, { headers, method }), e, ctx);
  await Promise.all(waits);
  return { status: r.status, location: r.headers.get("location"), cache: r.headers.get("cache-control"),
           etag: r.headers.get("etag"), body: method === "GET" ? await r.text() : "",
           points: JSON.parse(JSON.stringify(points)), fetched: [...fetched] };
};
const out = {};
out.weights_default = w.weights(undefined);
out.weights_custom = w.weights('{"control":0,"glory":2,"bogus":5}');
out.weights_bad = w.weights("not json");
const ws = w.weights(undefined), seen = {};
for (let i = 0; i < 1000; i++) { const a = w.pickArm(ws, i / 1000); seen[a] = (seen[a] || 0) + 1; }
out.spread = seen;
out.only_glory = [0, 0.5, 0.999].map((r) => w.pickArm(w.weights('{"glory":1}'), r));
out.arm_path = [w.armPath("/x/heritage/faq/"), w.armPath("/x/heritage"), w.armPath("/x/evil/"), w.armPath("/faq/")];
out.bots = ["", "Googlebot/2.1", "facebookexternalhit/1.1", "curl/8"].map(w.isBot);
out.human = w.isBot(ua["user-agent"]);
out.off = await go("/", env({ AB_ENABLED: "0" }));
out.home = await go("/");
out.home_bot = await go("/", env(), { "user-agent": "Googlebot/2.1" });
out.home_head = await go("/", env(), ua, "HEAD");
globalThis.missing = "/x/glory/";
out.home_missing = await go("/", env({ AB_WEIGHTS: '{"glory":1}' }));
globalThis.missing = undefined;
out.download = await go("/x/glory/get/windows/");
out.download_noslash = await go("/x/frontier/get/windows");
out.download_bot = await go("/x/glory/get/windows/", env(), { "user-agent": "Googlebot" });
out.page = await go("/x/heritage/how-it-works/");
out.asset = await go("/x/heritage/_assets/a.css");
out.other = await go("/faq/");
out.unknown_arm = await go("/x/evil/get/windows/");
out.no_binding = await go("/", { AB_ENABLED: "1" });
out.db_fails = await go("/", env({ DB: { prepare: () => { throw new Error("D1 down"); } } }));
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run() -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    code = HARNESS % {"worker": json.dumps(WORKER.as_uri())}
    r = subprocess.run([node, "--no-warnings", "--input-type=module", "-e", code],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


ARMS = ["control", "heritage", "frontier", "glory"]
UPSERT = ("INSERT INTO totals (day, arm, event, page, n) VALUES (?1, ?2, ?3, ?4, 1) "
          "ON CONFLICT (day, arm, event, page) DO UPDATE SET n = n + 1")


def counted(result: dict) -> list[list[str]]:
    """The (arm, event, page) of each total the request added to; checks the SQL and the day on the way."""
    out = []
    for p in result["points"]:
        assert p["sql"] == UPSERT
        day, *rest = p["args"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)  # a day, never a time
        out.append(rest)
    return out


def test_weights_and_random_pick(run: dict) -> None:
    assert run["weights_default"] == [[a, 1] for a in ARMS]
    assert dict(run["weights_custom"]) == {"control": 0, "heritage": 0, "frontier": 0, "glory": 2}
    assert run["weights_bad"] == [[a, 1] for a in ARMS]  # bad config falls back to equal arms
    assert run["spread"] == {a: 250 for a in ARMS}  # equal weights split [0, 1) evenly
    assert run["only_glory"] == ["glory"] * 3


def test_paths_and_bots(run: dict) -> None:
    assert run["arm_path"] == [{"arm": "heritage", "rest": "/faq/"}, {"arm": "heritage", "rest": "/"}, None, None]
    assert run["bots"] == [True, True, True, True] and run["human"] is False


def test_kill_switch_passes_everything_through(run: dict) -> None:
    off = run["off"]
    assert off["fetched"] == ["/"] and off["points"] == [] and off["cache"] == "max-age=600"


def test_home_serves_one_arm_uncached_and_counts_the_assignment(run: dict) -> None:
    home = run["home"]
    arm = home["fetched"][0].split("/")[2]
    assert home["fetched"] == [f"/x/{arm}/"] and arm in ARMS
    assert home["status"] == 200 and home["body"] == f"<html>/x/{arm}/"
    assert home["cache"] == "no-store" and home["etag"] is None
    assert counted(home) == [[arm, "assign", "/"]]


def test_bots_and_head_get_the_normal_home_uncounted(run: dict) -> None:
    assert run["home_bot"]["fetched"] == ["/"] and run["home_bot"]["points"] == []
    assert run["home_head"]["points"] == []


def test_missing_arm_falls_back_to_the_normal_home(run: dict) -> None:
    miss = run["home_missing"]
    assert miss["fetched"] == ["/x/glory/", "/"] and miss["status"] == 200 and miss["body"] == "<html>/"
    assert miss["points"] == []  # a visit that never saw the arm is not counted as assigned to it


def test_download_is_counted_and_redirected(run: dict) -> None:
    for key, arm in (("download", "glory"), ("download_noslash", "frontier")):
        d = run[key]
        assert d["status"] == 302 and d["location"] == "https://freemyid.org/get/windows"
        assert counted(d) == [[arm, "download", "/get/windows/"]]
        assert d["fetched"] == []  # the redirect never touches the origin
    assert run["download_bot"]["status"] == 302 and run["download_bot"]["points"] == []


def test_pages_pass_through_and_only_html_views_count(run: dict) -> None:
    assert counted(run["page"]) == [["heritage", "view", "/how-it-works/"]]
    assert run["asset"]["points"] == [] and run["asset"]["fetched"] == ["/x/heritage/_assets/a.css"]
    assert run["other"]["points"] == [] and run["other"]["fetched"] == ["/faq/"]
    assert run["unknown_arm"]["fetched"] == ["/x/evil/get/windows/"] and run["unknown_arm"]["points"] == []


def test_counting_never_breaks_the_page(run: dict) -> None:
    assert run["no_binding"]["status"] == 200
    assert run["db_fails"]["status"] == 200 and run["db_fails"]["points"] == []


def test_data_points_hold_no_identifiers() -> None:
    src = WORKER.read_text(encoding="utf-8")
    call = src[src.index(".bind("):]
    call = call[: call.index(")")]
    assert call == ".bind(day, arm, event, page"  # exactly these four values are stored
    for banned in ("CF-Connecting-IP", "user-agent", "referer", "cf.", "country", "headers"):
        assert banned.lower() not in call.lower(), banned
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.DOTALL).lower()  # code only, not comments
    for banned in ("cookie", "cf-connecting-ip", "x-forwarded-for", "request.cf"):
        assert banned not in code, banned


def test_worker_is_disclosed_whenever_it_is_on_and_logs_stay_off() -> None:
    text = WRANGLER.read_text(encoding="utf-8")
    assert '"AB_ENABLED": "0"' in text or '"AB_ENABLED": "1"' in text
    if '"AB_ENABLED": "1"' in text:
        # owner-approved disclosure (docs/AB_TEST.md) must be on /safety/#this-website while the test counts
        safety = (ROOT / "web/src/pages/safety/index.astro").read_text(encoding="utf-8")
        assert "our server picks one of four designs at random" in safety
        assert "no cookies, no IP address, nothing about your device" in safety
        assert "no trackers, no analytics," not in safety  # the old blanket claim is gone
    assert '"observability": { "enabled": false }' in text
    assert '"pattern": "freemyid.org/"' in text and '"pattern": "freemyid.org/x/*"' in text


# ---------------------------------------------------------------- report statistics


def test_wilson_and_z_test() -> None:
    lo, hi = ab_report.wilson(50, 1000)
    assert 0.038 < lo < 0.040 and 0.064 < hi < 0.066
    assert ab_report.wilson(0, 0) == (0.0, 0.0)
    a, b = ab_report.Arm("control", 1000, 50), ab_report.Arm("glory", 1000, 80)
    z, p = ab_report.z_test(a, b)
    assert 2.6 < z < 2.8 and 0.005 < p < 0.01
    assert ab_report.z_test(a, ab_report.Arm("x", 0, 0)) == (0.0, 1.0)


def test_rows_to_arms_ignores_unknown_values() -> None:
    rows = [{"arm": "glory", "event": "assign", "n": "10"}, {"arm": "glory", "event": "download", "n": 2},
            {"arm": "evil", "event": "assign", "n": 5}, {"arm": "control", "event": "view", "n": 9}]
    arms = {a.name: a for a in ab_report.arms_from_rows(rows)}
    assert (arms["glory"].visits, arms["glory"].downloads) == (10, 2)
    assert arms["control"].visits == 0 and set(arms) == set(ARMS)


def test_report_waits_for_enough_data_then_names_a_clear_winner() -> None:
    few = [ab_report.Arm(a, 100, 5) for a in ARMS]
    assert "Not enough data yet" in ab_report.report(few)
    even = [ab_report.Arm(a, 2000, 100) for a in ARMS]
    assert "No design beats the control clearly yet." in ab_report.report(even)
    clear = [ab_report.Arm("control", 2000, 100), ab_report.Arm("heritage", 2000, 105),
             ab_report.Arm("frontier", 2000, 170), ab_report.Arm("glory", 2000, 110)]
    assert "frontier beats the control" in ab_report.report(clear)
