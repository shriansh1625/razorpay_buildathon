# FINAL demo contingency

Do **not** improvise. Use prepared routes.

## Direct hash routes

| Target | Route |
|---|---|
| Control Room | `#/control` |
| Success workspace | `#/opportunity/opp_CQ6VCH7HPPW9WG284G5EFRMDN0` |
| Blocked workspace | `#/opportunity/opp_WST4PPPH81VPNTNC18K0YGRAW9` |
| Benchmark Lab | `#/benchmark` |
| Matrix | `#/benchmark/matrix` |
| Cell ABUNDANT×REVIVE×14 | Matrix click or API reference in System |
| System / evidence | `#/system` |
| Receipt | `#/receipt/{id}` from success opp |
| Audit | `#/audit` |

## Primary paths

| Path | Flow |
|---|---|
| **Success** | Control Room → success opp → Analyze → Lab → Guardrails → Execution → Receipt → Audit |
| **Blocked** | Blocked opp → Guardrails (BLOCKED / Approval Denied) → Audit (no execution) |
| **Benchmark** | Benchmark Lab → 20×6×5 → matrix → ABUNDANT × REVIVE × seed 14 |

## Failure recovery (no benchmark rerun)

| Symptom | Fallback |
|---|---|
| Blank UI | Restart `revive control-room` |
| Wrong world | Refresh — **never click Run Recovery** during pitch |
| Cell data empty | Show contract + methodology; cite mount path `artefacts/benchmark/official-cloud-final/` |
| Navigation fail | Hard refresh `#/control` |
| Success opp broken | `#/system` claim/evidence table |

## Spoken pivots

**Benchmark unmounted:**  
> “Six hundred cells are verified when the frozen tree is mounted. The contract and methodology are in the repo — here is the declared experiment structure.”

**AI question mid-demo:**  
> “PAYVANTA’s sandbox may call Groq for diagnosis proposals. The engine still decides. If Groq is off, you are seeing DETERMINISTIC FALLBACK — that is honest, not fake AI.”

See also: `submission/pitch/VIDEO-RECORDING-CHECKLIST.md`
