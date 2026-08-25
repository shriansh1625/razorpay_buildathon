# Binding Constraints

Per-resource utilization at mid-cycle allocation snapshot.

## Official scale (sample: seed 1 BALANCED)

| resource | binding | avg_util | peak_util | shadow_freq |
|----------|---------|----------|-----------|-------------|
| retry_slots | 1 | 1.00 | 1.00 | 1 |
| message_capacity | 0 | 0.00 | 0.00 | 0 |
| voice_minutes | 0 | 0.00 | 0.00 | 0 |
| human_review_slots | 1 | 1.00 | 1.00 | 1 |
| incentive_budget | 0 | 0.00 | 0.00 | 0 |
| contact_allowance | 0 | 0.00 | 0.00 | 0 |

## Aggregate official-scale binding frequency
- **contact_allowance**: avg_peak_util=0.00, binding_cells=0%
- **human_review_slots**: avg_peak_util=1.00, binding_cells=100%
- **incentive_budget**: avg_peak_util=0.00, binding_cells=0%
- **message_capacity**: avg_peak_util=0.00, binding_cells=0%
- **retry_slots**: avg_peak_util=0.94, binding_cells=83%
- **voice_minutes**: avg_peak_util=0.00, binding_cells=0%
