"""Six-profile 15-cycle M6/M7 fingerprints — development only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.m13_22_fingerprint import cycle_m6_m7_fingerprint

PROFILES = (
    "BALANCED",
    "HIGH_NATURAL",
    "SCARCE",
    "ABUNDANT",
    "HOSTILE",
    "DEGRADED",
)


def main() -> None:
    out = Path("implementation/m13-22-m6-m7-performance")
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for profile in PROFILES:
        print(f"fingerprinting seed=1 {profile}...", flush=True)
        results.append(cycle_m6_m7_fingerprint(1, profile, cycles=15))
    payload = {"label": "DEVELOPMENT_ONLY", "results": results}
    (out / "six-profile-fingerprints.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
