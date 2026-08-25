# B3 Implementation Audit

**Status:** ALIGNED

- B3 = GREEDY_ENRV per docs/20 — GreedyEnrvBaseline ranks by raw heuristic ENRV.
- Observable inputs only — best_action_for_opportunity on ObservableOpportunity features.
- Resource handling via can_reserve_action / reserve_action on BaselineCycleContext.
- Below-ε opportunities get NO_ACTION; capacity exhaustion yields DEFERRED.
- Tie-breaking: sort by (-enrv, opportunity_id) in decide_cycle.
- Calibration b3_greedy_selection mirrors greedy-by-ENRV on M7 PricedCandidates.
- CAUTION: B3 baseline uses observable heuristic ENRV; calibration path uses M7 ENRV — same ranking intent.
- No oracle access in baseline package.
