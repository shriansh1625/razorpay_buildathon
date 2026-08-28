# AI failure modes

| Failure | Behavior |
|---|---|
| Missing API key | Deterministic fallback, no crash |
| Timeout (12s) | Fallback, `AI_UNAVAILABLE` |
| HTTP 4xx/5xx | Bounded retry (2), then fallback |
| Schema invalid | Fallback |
| Unknown cause/action in model output | Fallback |
| AI proposes action blocked by policy | Engine BLOCK still applies — show both |

## Security

- Groq API key must be supplied through `GROQ_API_KEY` (environment variable only)
- Never returned in API JSON, HTML, or logs
- Never committed to Git
- If exposed: revoke/rotate in Groq console immediately

## Rate control

- No Groq calls from Benchmark Lab
- Cached per opportunity — not on every UI rerender
- Cleared when sandbox world regenerates
