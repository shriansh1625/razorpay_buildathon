# Public parity matrix (P14)

**Ship commit:** `1f6f069` — feat: ship PAYVANTA AI-enabled recovery release  
**Verified:** 2026-08-28  
**Fresh clone path:** `C:\temp\payvanta-final-public-clone`

---

| Feature | Local RC | `origin/main` | Fresh public clone |
|---|---|---|---|
| Control Room | PASS | PASS | PASS |
| `revive/product/intelligence/` | PASS | PASS | PASS |
| AI diagnosis API | PASS | PASS | PASS |
| AI diagnosis UI panel | PASS | PASS | PASS (source present) |
| Economic decision boundary | PASS | PASS | PASS |
| Deterministic fallback (no key) | PASS | PASS | PASS |
| Guardrails | PASS | PASS | PASS |
| Authorization / execution gates | PASS | PASS | PASS |
| Measurement + receipt | PASS | PASS | PASS |
| Audit ledger | PASS | PASS | PASS |
| Benchmark contract (no mount) | PASS | PASS | PASS |
| Benchmark matrix (with mount) | PASS | PASS | When artefacts mounted |
| `GET /api/product/overview` | PASS | PASS | PASS |
| `GET /api/intelligence/status` | PASS | PASS | PASS |
| Product tests | 55 passed | 55 collected | 44 passed, 11 skipped* |
| README AI architecture | PASS | PASS | PASS |
| Submission pitch package | PASS | PASS | PASS |
| Official benchmark code diff | none | none | none |
| Official artefact diff | none | none | none |
| Secrets in repo | none | none | none |

\*11 skipped = official-cloud-final not extracted in clone (expected without mounted evidence).

---

## Demo opportunities (seed 14 · 4 cycles)

| Path | Opportunity | Public clone |
|---|---|---|
| Success | `opp_CQ6VCH7HPPW9WG284G5EFRMDN0` | AUTHORIZED · SUCCEEDED |
| Blocked | `opp_WST4PPPH81VPNTNC18K0YGRAW9` | BLOCKED · NOT_EXECUTED |

---

## Fresh clone commands (verified)

```powershell
git clone https://github.com/shriansh1625/razorpay_buildathon.git
cd razorpay_buildathon
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest tests/product -q
revive control-room
```

---

## AI enabled (manual — owner key only)

```powershell
$env:GROQ_API_KEY = "<rotated-key>"   # never commit
revive control-room
```

Open `#/opportunity/opp_CQ6VCH7HPPW9WG284G5EFRMDN0` → Analyze → verify AI diagnosis panel.

---

## Remaining non-parity items

| Item | Status |
|---|---|
| 5-minute video | P1 — not recorded |
| GitHub description/topics | P2 — manual |
| Screenshots from public clone | P2 — pre-ship set in repo; refresh optional after video |

**Public repository is now the source of truth for the AI-enabled release.**
