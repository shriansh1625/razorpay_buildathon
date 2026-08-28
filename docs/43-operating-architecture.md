# 43 · Operating architecture (as implemented)

This is the architecture of **the shipped PAYVANTA**, not the unimplemented LLM
agents in the original spec. Spec vs implementation: [why-ai.md](why-ai.md),
[08-agent-architecture.md](08-agent-architecture.md) (status banner).

---

## 1. Recovery loop (under 20 seconds)

```mermaid
flowchart TD
  CTX[OBSERVED CONTEXT] --> AI[AI DIAGNOSIS · Groq optional]
  AI --> CAND[CANDIDATE VALIDATION]
  CAND --> CF[COUNTERFACTUAL / ENRV]
  CF --> POL[DETERMINISTIC POLICY]
  POL --> GRD[GUARDRAILS]
  GRD --> AUTH[AUTHORIZATION]
  AUTH --> EX[BOUNDED EXECUTION]
  EX --> MEAS[MEASUREMENT]
  MEAS --> AUD[AUDIT / RECEIPT]
```

Intelligence (diagnosis, ENRV, allocation) **proposes**.  
Deterministic controls **permit or refuse**.  
Execution cannot start without `AUTHORIZED`.

---

## 2. Official experiment (parallel, frozen)

```mermaid
flowchart TD
  ENG[SAME ENGINE] --> EXP[OFFICIAL EXPERIMENT]
  EXP --> FZ[FROZEN CONFIGURATION]
  FZ --> GRID[20 SEEDS × 6 PROFILES × 5 POLICIES]
  GRID --> CELLS[600 CELLS · 120 GROUPS]
  CELLS --> VAL[VALIDATED EVIDENCE]
  VAL --> LAB[Benchmark Lab · read-only]
```

Sandbox ≠ cell. Evidence path:
`artefacts/benchmark/official-cloud-final/` (gitignored; mount to verify).

---

## 3. Trust boundary

```mermaid
flowchart LR
  subgraph INTELLIGENCE["INTELLIGENCE · PROPOSE"]
    D[Diagnosis]
    E[ENRV]
    A[Lagrangian allocate]
  end
  subgraph CONTROL["CONTROL · AUTHORIZE"]
    G[Guardrails]
    Z[Authorization]
  end
  subgraph ENGINE["ENGINE · EXECUTE"]
    X[Bounded execution]
    M[Measurement]
    J[Audit]
  end
  D --> E --> A --> G --> Z --> X --> M --> J
```

No LLM in this submission. Intelligence cannot skip CONTROL.

---

## 3. Product surfaces

| Human | Machine |
|---|---|
| `#/control` Control Room | `GET /api/product/overview` |
| `#/opportunity/{id}` Workspace | `GET /api/opportunity/{id}` |
| `#/audit` | `GET /api/audit` |
| `#/benchmark` | `GET /api/benchmark` · `/official/contract` |

---

## 4. What does not execute

- LLM calls (`llm_used=False`, official `LLM_OFF`)
- Writes to official evidence (HTTP 405)
- Adapter calls for `BLOCKED` / unapproved states
- Package rename (`revive` stays)
