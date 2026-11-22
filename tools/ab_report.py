"""Home-page A/B/C test report (docs/AB_TEST.md). Stdlib only.

    CF_ACCOUNT_ID=<id> python3 tools/ab_report.py [--days 30]
    python3 tools/ab_report.py --rows rows.json        # offline: [{"arm":..,"event":..,"n":..}, ...]

Reads the aggregate counts the edge worker (worker/ab-test) writes to Workers Analytics Engine (dataset
freemyid_ab) through the SQL API, with the Cloudflare token in ~/.config/freemyid/cf_token (chmod 600; needs
Account > Account Analytics > Read). Prints, per arm: visits assigned at "/", downloads started, the download rate
with a 95% interval, and a two-sided two-proportion z-test against the control arm.

Visits are draws, not people: a refresh draws again, and the counts hold no identifiers to merge them. That inflates
every arm's denominator the same way, so the comparison stays fair; the absolute rates read low.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ARMS = ("control", "heritage", "frontier", "glory")
DATASET = "freemyid_ab"
MIN_VISITS = 400  # per arm before any verdict; below this the report says "keep running"


@dataclass
class Arm:
    name: str
    visits: int
    downloads: int

    @property
    def rate(self) -> float:
        return self.downloads / self.visits if self.visits else 0.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def z_test(a: Arm, b: Arm) -> tuple[float, float]:
    """Two-proportion z-test (pooled). Returns (z, two-sided p). b is compared against a."""
    if not a.visits or not b.visits:
        return (0.0, 1.0)
    p = (a.downloads + b.downloads) / (a.visits + b.visits)
    se = math.sqrt(p * (1 - p) * (1 / a.visits + 1 / b.visits))
    if se == 0:
        return (0.0, 1.0)
    z = (b.rate - a.rate) / se
    return (z, math.erfc(abs(z) / math.sqrt(2)))


def arms_from_rows(rows: list[dict]) -> list[Arm]:
    tally = {a: {"assign": 0, "download": 0} for a in ARMS}
    for r in rows:
        arm, event = str(r.get("arm")), str(r.get("event"))
        if arm in tally and event in tally[arm]:
            tally[arm][event] += int(float(r.get("n", 0)))
    return [Arm(a, t["assign"], t["download"]) for a, t in tally.items()]


def fetch_rows(account: str, days: int) -> list[dict]:
    token_file = Path.home() / ".config/freemyid/cf_token"
    if token_file.stat().st_mode & 0o077:
        sys.exit("cf_token must be chmod 600")
    token = token_file.read_text(encoding="utf-8").strip()
    # _sample_interval restores true counts if Analytics Engine sampled the writes.
    sql = (f"SELECT blob1 AS arm, blob2 AS event, SUM(_sample_interval) AS n FROM {DATASET} "
           f"WHERE timestamp > NOW() - INTERVAL '{int(days)}' DAY AND blob2 IN ('assign', 'download') "
           "GROUP BY arm, event FORMAT JSON")
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/analytics_engine/sql",
        data=sql.encode(), method="POST", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return list(json.load(resp).get("data", []))


def report(arms: list[Arm]) -> str:
    control = next(a for a in arms if a.name == "control")
    lines = [f"{'arm':<10}{'visits':>8}{'downloads':>11}{'rate':>8}   95% interval     vs control"]
    for a in arms:
        lo, hi = wilson(a.downloads, a.visits)
        vs = "baseline" if a is control else ""
        if a is not control:
            _, p = z_test(control, a)
            lift = (a.rate / control.rate - 1) * 100 if control.rate else float("nan")
            vs = f"{lift:+.0f}% (p={p:.3f})" if control.rate else f"p={p:.3f}"
        lines.append(f"{a.name:<10}{a.visits:>8}{a.downloads:>11}{a.rate:>8.1%}   "
                     f"{lo:>5.1%} - {hi:<6.1%}   {vs}")
    small = [a.name for a in arms if a.visits < MIN_VISITS]
    if small:
        lines.append(f"\nNot enough data yet ({', '.join(small)} under {MIN_VISITS} visits). Keep the test running.")
    else:
        # Three designs are compared with the control, so a winner needs p < 0.05 / 3 (Bonferroni).
        winners = [a for a in arms if a is not control and a.rate > control.rate and z_test(control, a)[1] < 0.05 / 3]
        best = max(winners, key=lambda a: a.rate, default=None)
        lines.append("\n" + (f"{best.name} beats the control on downloads (p < {0.05 / 3:.3f})." if best
                             else "No design beats the control clearly yet."))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--rows", type=Path, help="JSON rows instead of the SQL API (offline/testing)")
    a = ap.parse_args()
    if a.rows:
        rows = json.loads(a.rows.read_text(encoding="utf-8"))
    else:
        account = os.environ.get("CF_ACCOUNT_ID")
        if not account:
            sys.exit("set CF_ACCOUNT_ID (Cloudflare dashboard > Workers > Account ID)")
        rows = fetch_rows(account, a.days)
    print(report(arms_from_rows(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
