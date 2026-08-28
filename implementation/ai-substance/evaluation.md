# Enable Groq AI diagnosis (sandbox)

```powershell
# PowerShell — session only (do not commit this value)
$env:GROQ_API_KEY = "<your-groq-api-key>"
revive control-room
```

```bash
# bash
export GROQ_API_KEY="<your-groq-api-key>"
revive control-room
```

Model: `openai/gpt-oss-120b` via Groq API.

Without the key, PAYVANTA shows **DETERMINISTIC FALLBACK** honestly.

Verify: `GET /api/intelligence/status` · open workspace → **AI diagnosis** panel.
