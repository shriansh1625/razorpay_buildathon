# Git authorship audit — PAYVANTA

**Date:** 2026-08-28  
**Audit type:** Read-only (no history rewrite, no commit, no push)

---

## Repository

| Field | Value |
|---|---|
| **Repository** | `shriansh1625/razorpay_buildathon` |
| **Remote origin** | `https://github.com/shriansh1625/razorpay_buildathon.git` |
| **Branch** | `main` |
| **HEAD** | `7bed946` |
| **Visibility** | **Public** (verified via unauthenticated GitHub fetch) |
| **Total commits** | 9 |

---

## Git identity (local environment)

| Setting | Value | Scope |
|---|---|---|
| **user.name** | `shriansh1625` | Global (no repo-local override) |
| **user.email** | `omshriansh16@gmail.com` | Global (no repo-local override) |

**Assessment:** Identity matches the repository owner GitHub account. No change required.

**`.git/config`:** Contains only `core`, `remote.origin`, and `branch.main` entries. No AI tool names. No incorrect identity overrides.

---

## Authorship history (full repository)

### Unique authors

```
shriansh1625 <omshriansh16@gmail.com>
```

### Unique committers

```
shriansh1625 <omshriansh16@gmail.com>
```

All 9 commits share the same author and committer. No other humans. No AI identities.

### Recent commits (last 20)

| SHA | Author | Subject |
|---|---|---|
| `7bed946` | shriansh1625 | docs: record final submission status after public repo push |
| `11ad65a` | shriansh1625 | fix: make invalidated-tree test portable on fresh clone |
| `992217f` | shriansh1625 | feat: ship PAYVANTA revenue recovery product |
| `25dc006` | shriansh1625 | Complete M13.27 cloud validation gate for metrics tail rescue |
| `7765854` | shriansh1625 | Rescue production metrics aggregation performance |
| `e7ab952` | shriansh1625 | Repair benchmark checkpoint reconciliation |
| `891e259` | shriansh1625 | Fix parallel stress benchmark worker dispatch |
| `ff80e5f` | shriansh1625 | Restore Lagrangian reference equivalence |
| `fd7a6ed` | shriansh1625 | Finalize REVIVE benchmark implementation |

---

## Co-author and AI attribution scan

Commands run:

```bash
git log --all --format='%B' | grep -i "co-authored-by"
git log --all --format='%an <%ae>%n%cn <%ce>%n%B' | grep -i -E "cursor|claude|anthropic|copilot|openai"
git log --all --format='%B' | grep -i -E "Co-authored-by|Signed-off-by|Helped-by|Reviewed-by"
```

| Check | Count |
|---|---|
| **Co-authored-by trailers** | **0** |
| **AI tool names in author/committer/message** | **0** |
| **Other commit message trailers** | **0** |

No accidental Cursor, Claude, Anthropic, OpenAI, or Copilot attribution in Git history.

---

## Public contributor check

| Source | Observation |
|---|---|
| **GitHub repo page** | Public; README and commits visible without authentication |
| **GitHub commits (`/commits/main/`)** | All 9 commits attributed to owner on Aug 25–28, 2026 |
| **GitHub contributors graph** | Page loads; owner is sole contributor (matches desired “Contributors: 1” state) |

No attempt was made to manipulate GitHub contributor metadata.

**Unexpected authors on GitHub:** None observed.

---

## Legitimate human contributors

| Contributor | Email | Commits |
|---|---|---|
| **shriansh1625** | `omshriansh16@gmail.com` | 9 / 9 |

No legitimate co-authors to preserve or remove. History was **not** rewritten.

---

## Future commit policy (Cursor / agent environment)

1. **Do not auto-commit or auto-push** without explicit owner instruction.
2. **Do not append** `Co-authored-by:` trailers for Cursor, Claude, Anthropic, OpenAI, Copilot, or any AI tool.
3. **Use owner identity only:**
   - `user.name = shriansh1625`
   - `user.email = omshriansh16@gmail.com`
4. **Before every future commit**, run:
   ```bash
   git status
   git log -1 --format=fuller
   ```
   Confirm author, committer, and message contain no accidental AI co-author lines.
5. **Do not rewrite history** to “clean up” attribution that does not exist.

---

## Actions taken in this audit

| Action | Result |
|---|---|
| Rewrite history | **NO** |
| Force push | **NO** |
| Commit | **NO** |
| Push | **NO** |
| Change git config | **NO** (identity already correct) |
| Modify product / benchmark / README | **NO** |

This report file is created locally and is **not committed** per audit instructions.

---

## Final acceptance

| Gate | Status |
|---|---|
| Repository public | **PASS** |
| Contributor state understood | **PASS** (1 contributor — desired) |
| No accidental Cursor attribution | **PASS** |
| No accidental Claude attribution | **PASS** |
| AI co-author trailers | **0** |
| Future commits use owner identity | **PASS** (config correct) |
| Cursor will not auto-commit/push | **POLICY RECORDED** |
| Legitimate authorship untouched | **PASS** |
| History intact | **PASS** |
