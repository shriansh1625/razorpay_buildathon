# AI fallback modes

| Condition | UI label | `status` |
|---|---|---|
| `GROQ_API_KEY` absent | DETERMINISTIC FALLBACK | `DETERMINISTIC_FALLBACK` |
| Groq timeout / HTTP error | AI FALLBACK ACTIVE | `AI_UNAVAILABLE` |
| Invalid model JSON | AI FALLBACK ACTIVE | `AI_UNAVAILABLE` |
| Groq success | AI DIAGNOSIS AVAILABLE | `AI_COMPLETED` |

Fallback uses deterministic taxonomy ranking + engine candidate catalogue — never pretends to be Groq output.

Product continues safely. Authorization never granted due to AI failure.
