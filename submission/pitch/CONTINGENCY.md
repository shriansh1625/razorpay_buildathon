# Demo contingency plan

Do **not** improvise if a click fails. Use a prepared fallback.

## Primary paths

| Path | Entry | Key IDs / routes |
|---|---|---|
| **Success** | `#/control` → success opp | `opp_CQ6VCH7HPPW9WG284G5EFRMDN0` → AUTHORIZED → SUCCEEDED → MEASURED |
| **Blocked** | Opportunities → blocked opp | `opp_WST4PPPH81VPNTNC18K0YGRAW9` → BLOCKED → NOT EXECUTED → Audit |
| **Benchmark** | `#/benchmark` → matrix | ABUNDANT × REVIVE × seed 14 |
| **System / evidence** | `#/system` | Claim → evidence table · intelligence · track03 |
| **Receipt** | `#/receipt/{id}` | From success opportunity after execution |

## Failure modes

| Symptom | Likely cause | Fallback |
|---|---|---|
| Blank Control Room | Server not running | Restart `revive control-room`; open http://127.0.0.1:8765 |
| Wrong seed / empty world | Run Recovery clicked | **Do not click Run Recovery.** Refresh. Prepared seed 14 reloads. |
| Opportunity not found | Wrong id / stale hash | Use palette search or `#/opportunities` list |
| Benchmark cell empty | Official tree not mounted | Show Benchmark Lab **contract** + methodology; state mount path; do not invent M-10 values |
| Matrix slow | Large payload | Use executive Benchmark level first; open seed 14 cell only |
| Navigation stuck | Hash routing | Hard refresh on `#/control` |
| Server crash | Port conflict | `revive control-room --port 8766` |

## Spoken pivots

**If success path breaks:**

> “Let me show the evidence map instead — the same workflow is in the engine projection and tests.”

→ `#/system` claim/evidence table

**If benchmark mount missing:**

> “The official 600-cell tree is frozen and gitignored. The contract, methodology, and verification API are in the repo. Here is what a verified cell looks like when mounted.”

→ Show methodology + reference cell documentation in `docs/42-official-benchmark.md`

**If blocked path breaks:**

> “Escalation is structural: BLOCKED means no adapter call. Here is the audit entry.”

→ `#/audit` filtered verbally to blocked opp

## Pre-recording checklist

- [ ] Server running; seed 14 loaded
- [ ] Run Recovery **not** pressed
- [ ] Browser 100% zoom · 1440×900
- [ ] Notifications off · bookmarks hidden
- [ ] Official evidence mounted (optional, for cell drilldown)
