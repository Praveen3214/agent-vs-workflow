### Measured: workflow vs agent — `Tailscale`

| Metric | Workflow | Agent | Agent ÷ Workflow |
|---|---|---|---|
| LLM calls | 5 | 1 | 0.2× |
| Tool calls | 4 | 0 | 0.0× |
| Total tokens | 4746 | 383 | 0.1× |
| Cost (USD) | 0.00102 | 0.00026 | 0.3× |
| Wall time (s) | 11.2 | 2.6 | 0.2× |

_Notes: agent: tool-call format failed 4× after retries; forced final answer_
