# M8 Implementation Audit

**Status:** ALIGNED

- Objective: maximize Σ ENRV under capacities — implemented in allocate_portfolio (docs/10 §2.1).
- Lagrangian relaxation with subgradient on capacity violations — lagrangian_allocate().
- Primal recovery with reservation — primal_recovery() matches docs/10 §5.1.
- Greedy density fallback on iteration budget — fallback_greedy_allocate() (docs/10 §5.2).
- ε threshold from PolicyPack — enforced in best_action_for_opportunity and primal recovery.
- Six resource families tracked — retry, message, voice, human, incentive, contact_allowance.
- Shadow prices from Lagrangian dual and binding-resource estimates in primal recovery.
- Opportunity exclusivity — one assignment per opportunity in assignments dict.
- No oracle / latent inputs in allocation package (observable ENRV only).
- CAUTION: contact_allowance subgradient uses aggregate violation heuristic, not per-customer duals.
- CAUTION: M8 fallback uses ENRV/resource density; B3 uses raw ENRV — differentiation requires density inversions.
