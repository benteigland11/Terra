# Map type: `number`

Probes are open. **Knowns and unknowns** of type `number` filter the world to a
scalar with uncertainty.

## Shared idea

```text
samples (from runs.measures) → substrate stats → confidence ladder
```

| Field | Owner |
| ----- | ----- |
| `quantity` | you — stable name, e.g. `hostile_count` |
| `claim` | you — what Q means in words |
| `run_ids` | links |
| `stats.n/mean/std` | **Terra recomputes** — never agent-authored |
| `confidence` | claimed, **capped** by derived ladder |

## Probe payload

```python
return {
    "to": to,
    "status": "ok",
    "artifacts": [...],
    "measures": [
        {"quantity": "hostile_count", "value": 3},
    ],
}
```

Runs stamp `measures` into `meta.json`.  
`link-run` pulls values matching the node’s `quantity`.

## Confidence ladder (n=1 guard)

| derived | when |
| ------- | ---- |
| **low** | n ≥ 1 (std is null if n &lt; 2) |
| **med** | n ≥ 3 **or** (n ≥ 2 and std defined) |
| **high** | n ≥ 5 and std defined and std/\|mean\| ≤ 0.5 (or both 0) |

`terra known promote <id> high` **blocks** if ladder not met.

## CLI

```bash
# Unknown seeking a number
terra unknown create hostiles_r \
  --type number --quantity hostile_count \
  --claim "How many hostiles in region R at night?" \
  --evidence "repeated probe measures"

terra probe run mobs --to '{"kind":"region","id":"R"}'
terra unknown link-run hostiles_r <run_id>
terra unknown show hostiles_r   # shows n, mean, std

# Encode belief (starts provisional/low) — the only birth path
terra unknown graduate hostiles_r --as hostiles_r_est

terra known link-run hostiles_r_est <run_id2>
terra known promote hostiles_r_est med
terra known show hostiles_r_est
```

## Law

> Probes infinite. Map beliefs typed. Number = samples in, n/mean/std out.
