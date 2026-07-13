# Agent-first I/O (Cartograph blueprint)

Terra is for **agents first**. Humans get secondary views (`--human`, HTML).

## Install the feature, not two leaves

| Unit | Role |
| ---- | ---- |
| **`universal-agent-response-python`** | Leaf: envelope `{status, data\|error, meta?}` |
| **`infra-agent-cli-python`** | Leaf: declarative CLI, JSON stdout, no prompts |
| **`bp-agent-tool-cli-python`** | **Blueprint**: sealed composition of the two |

```text
cg/bp_agent_tool_cli_python/     ← install this
cg/universal_agent_response…     ← leaf (pinned dep)
cg/infra_agent_cli…              ← leaf (pinned dep)
```

Public façade (import only the blueprint):

```python
from cg.bp_agent_tool_cli_python.src.agent_tool_cli import (
    AgentToolCLI,
    tool_success,
    tool_error,
    emit,
    format_json,
    wrap_handler,
)
```

Terra adapter: `terra.agent_io` re-exports the blueprint + map `attention` / `next_actions` helpers.

## Envelope

```json
{
  "status": "success",
  "data": { … },
  "meta": { … }
}
```

Errors: `{"status": "error", "error": {"message": "…", "code": "…"}}`

## Map status

```bash
terra map status              # JSON default (agent-first)
terra map status --human      # pretty text
```

Agents read `data.attention` + `data.next_actions` — not prose.

## Law

1. Prefer **blueprint** over freehand leaf wiring.  
2. Default stdout = **JSON** envelope.  
3. Human format only behind `--human` (or dashboard).  
4. Do not invent a second schema beside agent-response.
