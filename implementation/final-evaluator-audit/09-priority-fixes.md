# 09 · Priority fixes

**This file is a recommended sequence only. The audit did not implement any of it.**

Do not commit or push until the owner asks. Do not rerun official benchmark. Do not modify `artefacts/benchmark/official-cloud-final/` or `revive/benchmark/official/`.

---

## P0 — do these or the process can fail

| Order | Fix | Done when |
|---|---|---|
| 1 | Make the GitHub repo **public**. Confirm `https://github.com/shriansh1625/razorpay_buildathon` returns 200 while logged out. | Incognito GET works |
| 2 | Commit **and** push the actual product: `revive/product/`, `tests/product/`, `revive/cli.py` `control-room`, local README, `pyproject.toml` description. Origin README must not say M10 / REVIVE Autopilot. | Fresh clone: `pip install -e ".[dev]"` → `revive control-room` → Control Room |
| 3 | Make official evidence **cloneable** without violating the freeze. Options: (a) git-lfs / release zip of `official-cloud-final` with checksum instructions, or (b) stop gitignoring that one tree, or (c) document a read-only download URL. Never rewrite cells. | Clean clone: Benchmark Lab VERIFIED, 600 cells |
| 4 | Record the **5-minute pitch** from seed-14 Control Room. Put the link in README. Do not click Run Recovery in the recording. | URL in README; video shows detect → intervene → execute → measure → 600 cells |
| 5 | Add a 20-line **ARCHITECTURE.md** (or README section) that matches the **running** system: UI → product projection → engine → simulated adapters; Benchmark Lab → official-cloud-final → verify. | A stranger can explain the loop without `docs/08` |

---

## P1 — materially protects score

| Order | Fix | Done when |
|---|---|---|
| 6 | One spoken and written **bridge sentence**: sandbox = this world, DRAFT pack; official = sealed pack, 600 cells; **same engine loop**. Put it on Control Room + README, not only `#/system`. | Judge cannot think ₹19,799 is M-10 |
| 7 | Align agent story with code: `docs/08` must say C-05 is deterministic rules, C-10 is **not shipped**, official LLM_OFF. Delete “2 LLM-invoking agents” or implement them behind a flag that never moves money. | Spec and `llm_used=False` match |
| 8 | Kill contradictory status lines: `docs/README.md` “source none / benchmark none”; `docs/00` “no implementation exists.” | First doc opened does not say the repo is empty |
| 9 | Fill or retire `docs/26-demo-script.md` placeholders. Single demo script = product README table. | One script |
| 10 | Demo pack: either run the Control Room on the **sealed** pack (preferred, if it still yields a clean wow+blocked pair) or label DRAFT as loudly as SANDBOX. | System view does not say DRAFT next to “same engine as official” without explanation |
| 11 | Show **one fired stopping rule** in the five-minute path (not only G7 block). | Track “stopping rules” is visible, not only coded |
| 12 | Surface hash-chain (or a “verify chain” button) on Audit Ledger, or stop claiming hash-chained audit in the pitch if only the engine has it. | Claim matches screen |
| 13 | Rehearse disaster: Restore demo seed 14; palette ABUNDANT×REVIVE×14. Hide or demote Run Recovery during pitch (do not fake-disable it). | Accidental click recoverable in <15s |
| 14 | State in the first 20s of the video: synthetic book, simulated rails, measured incremental net, official 600-cell evaluation. | Mockup attack pre-empted |

---

## P2 — polish

- First-viewport 1024 / mobile: already acceptable as non-demo form factors.
- Subnav clipping; matrix below-fold click.
- Remove or quarantine screenshot dumps and M13.26 forensic profiles from the default clone (or put under `implementation/` with a one-line “not evidence”).
- Decorative `ar-live` pulse: keep, but do not imply live merchant traffic.
- Fix links to `README.md#c-7` → `docs/README.md`.
- `implementation/open-blockers.md` M0 banner.

---

## P3 — optional, after P0/P1

- Schema-closed LLM diagnosis **off** on official cells (does not fix Track 03 bar; may help “AI Builder” branding).
- Razorpay **test-mode** adapter behind a flag — only if it can be demoed honestly; do not fake it.
- Learning engine — only if it can be measured; do not add theatre.

---

## Explicitly do not do

- Do not rerun the 600-cell official benchmark into `official-cloud-final`.
- Do not hardcode ₹19,799.25 or opportunity IDs into `app.js`.
- Do not add evaluator-only HTML, robots tricks, or user-agent forks.
- Do not “fix AI” by pasting an unconstrained chatbot onto authorization.
- Do not commit `.env`, credentials, or the invalidated `artefacts/benchmark/official/` tree as if it were product proof.

---

## Definition of “ready to submit”

A stranger, incognito:

1. Opens the public GitHub README and understands PAYVANTA in 20 seconds.
2. Watches a 5-minute video that shows the Track 03 loop and 600-cell evidence.
3. Clones, installs, runs Control Room, sees SANDBOX seed 14, a measured batch, a blocked path, Benchmark Lab VERIFIED.
4. Reads one architecture page that matches what they just ran.
5. Never needs a founder to explain PAYVANTA vs REVIVE vs the draft pack vs the sealed pack.

Until then, the engine can be excellent and the submission can still lose.

**Audit complete. No code changed.**
