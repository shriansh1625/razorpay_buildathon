# AI diagnosis contract — ai_diagnosis_v1

## Endpoint

`POST /api/opportunity/{opportunity_id}/ai-diagnosis`

## Response fields

| Field | Meaning |
|---|---|
| `schema_version` | `ai_diagnosis_v1` |
| `source` | `groq` or `deterministic_fallback` |
| `status` | `AI_COMPLETED` · `DETERMINISTIC_FALLBACK` · `AI_UNAVAILABLE` |
| `proposal.primary_cause` | Closed `CauseCode` |
| `proposal.cause_confidence` | Diagnosis confidence 0–1 (not recovery probability) |
| `proposal.observed_evidence` | Facts from detection/context only |
| `proposal.inference_notes` | Explicit inference |
| `proposal.candidate_actions[]` | Closed `ActionCode` proposals |
| `economic_decision` | Authoritative engine selection (ENRV path) |
| `trust_boundary` | AI propose · control authorize · engine execute |

## Validation

- Parsed with `parse_proposal()` — invalid schema → fallback
- Invalid cause/action codes rejected
- `opportunity_id` must match request

## Caching

One cached diagnosis per opportunity per server session. Cleared on `POST /api/recovery-run`.
