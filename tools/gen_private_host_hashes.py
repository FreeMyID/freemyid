"""Regenerate tools/private_host_hashes.txt (SHA-256 of private-only broker hostnames).

Run locally while brokers/registry.yaml still exists. Hashes only; no plaintext hostnames are written.
site_check.py compares them with hostnames found in the built site so the leak check keeps working
after the full registry moves to a private repo.
"""
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "private_host_hashes.txt"
FREEMAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "proton.me", "protonmail.com"}


def norm(h: str) -> str:
    h = h.strip().lower().rstrip(".")
    return h.removeprefix("www.")


def hostnames(path: Path) -> set[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for b in data.get("brokers", []):
        for key in ("url", "opt_out_url"):
            if b.get(key):
                out.add(norm(urlsplit(str(b[key])).hostname or ""))
        for d in b.get("domains") or []:
            out.add(norm(str(d)))
        if b.get("opt_out_email") and "@" in str(b["opt_out_email"]):
            out.add(norm(str(b["opt_out_email"]).split("@", 1)[1]))
    return {h for h in out if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", h) and h not in FREEMAIL}


def sha(h: str) -> str:
    return hashlib.sha256(h.encode()).hexdigest()


def main() -> int:
    full, sample = ROOT / "brokers" / "registry.yaml", ROOT / "brokers" / "registry.sample.yaml"
    if not full.exists():
        print("brokers/registry.yaml not present; keeping existing hash file")
        return 1
    sample_text = sample.read_text(encoding="utf-8").lower()
    # Anything the public sample already mentions anywhere (steps, notes) is public, so not private-only.
    private = {h for h in hostnames(full) - hostnames(sample) if h not in sample_text}
    lines = sorted(sha(h) for h in private)
    OUT.write_text("# SHA-256 of private-only broker hostnames (see gen_private_host_hashes.py). Hashes only.\n"
                   + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} hashes to {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
