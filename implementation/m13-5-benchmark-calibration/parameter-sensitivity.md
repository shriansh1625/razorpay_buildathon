# Parameter Sensitivity

Epsilon materially changes selection: True

## Notes

- tiny_config (12 opps): differing_allocations=0, b3_selected=5, revive_selected=5
- calibration_config (40 opps): differing=3, b3_selected=23, revive_selected=22
- M13 zero M-10 likely driven by tiny scale + single seed, not REVIVE architecture failure.

### Sweep: epsilon_paise

- {'epsilon_paise': 0, 'b3_selected_count': 23}
- {'epsilon_paise': 100, 'b3_selected_count': 22}
- {'epsilon_paise': 500, 'b3_selected_count': 20}
- {'epsilon_paise': 1000, 'b3_selected_count': 18}
- {'epsilon_paise': 5000, 'b3_selected_count': 16}
- {'epsilon_paise': 20000, 'b3_selected_count': 10}

### Sweep: opportunity_count

- {'opportunity_count': 12, 'positive_enrv_candidates': 22, 'competition_ratio_retry': 0.08}
- {'opportunity_count': 25, 'positive_enrv_candidates': 91, 'competition_ratio_retry': 0.28}
- {'opportunity_count': 40, 'positive_enrv_candidates': 124, 'competition_ratio_retry': 0.5}
- {'opportunity_count': 60, 'positive_enrv_candidates': 201, 'competition_ratio_retry': 0.64}

Diagnostic only — no parameter tuned toward a desired winner.
