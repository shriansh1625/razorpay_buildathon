# Final blockers (P13)

**Classification:** P0 = submission-invalidating · P1 = material risk · P2 = presentation · P3 = optional

---

## P0 — submission-invalidating

| ID | Blocker | Status |
|---|---|---|
| P0-1 | Public repo missing PAYVANTA product | **RESOLVED** |
| P0-2 | Repository private | **RESOLVED** |
| P0-3 | Secrets in repository | **CLEAR** |
| P0-4 | Official benchmark artefacts modified | **CLEAR** |

**No open P0 on local tree.**

---

## P1 — material risk

| ID | Issue | Status | Mitigation |
|---|---|---|---|
| P1-1 | **5-minute pitch video not recorded** | **OPEN** | `FINAL-5-MINUTE-SCRIPT.md` · `VIDEO-RECORDING-CHECKLIST.md` |
| P1-2 | **Groq AI layer not on public GitHub** | **OPEN** | Local RC verified (55 tests). Owner must commit + push when authorized. Public clone at `7bed946` has no `intelligence/` module. |
| P1-3 | Official evidence not in Git (by design) | **ACCEPTED** | README + Benchmark Lab explain mount |
| P1-4 | Compromised Groq key (exposed in chat) | **OPEN (external)** | Rotate/revoke in Groq console; use new key via env only |

---

## P2 — presentation

| ID | Issue | Status | Mitigation |
|---|---|---|---|
| P2-1 | GitHub description/topics | **OPEN** | `GITHUB-METADATA.md` |
| P2-2 | Submission docs + AI layer uncommitted | **OPEN** | Commit when owner approves |
| P2-3 | Public README stale vs local AI architecture | **OPEN** | Resolved on push |

---

## P3 — optional

| ID | Item |
|---|---|
| P3-1 | Refresh screenshots with AI diagnosis panel |
| P3-2 | Commit `git-authorship-audit.md` |
| P3-3 | Mobile screenshots in README |

---

## Freeze rule

No new features. No benchmark reruns. Close P1-1, P1-2, P1-4 before submission.

See `submission/FINAL-RELEASE-REPORT.md`.
