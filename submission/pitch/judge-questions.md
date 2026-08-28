# Judge questions

**Why AI?**  
Decision intelligence under uncertainty: uplift, scarce capacity, counterfactuals. Not a chatbot. See `docs/why-ai.md`.

**Why isn’t this just rules?**  
B1 is fixed retry. B2 is contact-all. B3 is greedy ENRV. PAYVANTA allocates a batch under gates. That is the official comparison.

**What is actually autonomous?**  
A bounded cycle that can detect, choose, and execute without a human on every opportunity — and must stop or escalate when gates fire.

**How do you choose interventions?**  
Feasible candidates → ENRV versus do-nothing → constrained allocator → gates.

**What is incremental net recovery?**  
Attributed recovery minus cost, not counting natural recovery as a win. Official M-10 is that net minus B0 on the same seed and profile.

**What happens when action is unsafe?**  
Authorization is not AUTHORIZED. No adapter call. See the prepared blocked opportunity.

**What happens when the system is uncertain?**  
Unclassified diagnosis; conservative candidates; human approval when the pack requires it. No invented action class.

**How do you stop automation?**  
Stopping rules override even a high ENRV. Autonomy bound on the opportunity.

**How do you prevent duplicate execution?**  
Idempotency keys. Second execute of the same authorization does not double-spend.

**How is the batch measured?**  
The sandbox Control Room aggregates this session. The official experiment measures 600 frozen cells.

**How is the benchmark different from the sandbox?**  
Sandbox demonstrates the workflow. Official experiment evaluates the engine under a frozen 20×6×5 design.

**What does 600 cells prove?**  
That the declared experiment was run, validated (`BENCHMARK_VALID`), and kept read-only. It does **not** prove universal superiority or production ROI.

**What does it NOT prove?**  
Live Razorpay recovery, scientific certainty, guaranteed merchant outcomes.

**What can be integrated into Razorpay?**  
Decision core, PolicyPack, audit, measurement — behind real adapters. Not in this sandbox.

**What is currently sandbox-only?**  
Simulated adapters, synthetic population, draft policy pack on the demo world, local HTTP Control Room.
