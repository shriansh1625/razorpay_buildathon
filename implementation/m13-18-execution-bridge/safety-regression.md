# Safety Regression (M13.18)

## Verified unchanged

| Control | Test |
|---------|------|
| G5 max discount | `test_m10_safety_discount_still_blocks` |
| G7 enforced | Approver wired through G7, not bypassed |
| SR / stale / idempotency | Existing `tests/policy/test_authorization_demo.py`, `tests/execution/test_authorization_requirement.py` — all pass |

## Not a safety bypass

`simulated_v1` only supplies `approval_state` when G7 triggers require approval. Gates G1–G6, G8–G12, and stopping rules still evaluated in `authorize_execution()`.

Risk-flag contexts → deterministic `REJECTED` (not auto-approved).
