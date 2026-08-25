# REVIVE — Revenue Recovery Autopilot

Razorpay Buildathon — Track 03: AI Revenue Recovery

**Status:** M10 Authorization Gates complete. 170 tests passing.

Specification: `docs/`  
Implementation planning: `implementation/`

## Development

```bash
python -m pip install -e ".[dev]"
pytest
revive generate-dataset --seed 42 --profile BALANCED --output artefacts/datasets/dev
```

## Scope

M1: foundation (types, clock, PRNG, state machines, config skeleton).  
M2: synthetic merchant environment + hidden outcome oracle.  
M3: baseline policies B0–B3.  
M4: Revenue Sentinel — detect revenue at risk (no action selection).  
M5: Context + Diagnosis — assemble observable context and rank candidate causes (no action selection).  
M6: Candidate recovery actions — enumerate feasible actions (no ranking or ENRV).  
M7: Counterfactual valuation — ENRV per candidate (no ranking or allocation).  
M8: Portfolio allocator — constrained capacity allocation (no execution or gates).  
M9: Decision lifecycle — seal, reconcile, reservations (no execution or gates).  
M10: Authorization gates + stopping rules (no execution).  
No payment execution, UI, LLM, or production integrations yet.
