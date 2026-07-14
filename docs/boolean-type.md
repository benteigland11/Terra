# Map type: `boolean`

Yes/no with a success **rate**, not a vibes claim.

## Shape

```text
type: boolean
quantity: rcon_reachable
claim: "RCON accepts auth on local dev"
samples: true/false trials from runs.measures
stats: { n, k_true, k_false, rate }
```

## Probe measures

```python
return {
    "to": to,
    "status": "ok",  # instrument status, not the boolean claim
    "artifacts": [...],
    "measures": [{"quantity": "rcon_reachable", "value": True}],
}
# value: true/false, 1/0, "true"/"false"
```

## Confidence ladder

| derived | when |
| ------- | ---- |
| **low** | n ≥ 1 |
| **med** | n ≥ 3 |
| **high** | n ≥ 5 **and** unanimous (rate 0 or 1) |

n=1 → low only. `promote high` blocks until enough trials.

## CLI

```bash
terra unknown create rcon_up \
  --type boolean --quantity rcon_reachable \
  --claim "Is RCON up on local dev?" \
  --evidence "repeated reachability trials"

terra unknown link-run rcon_up <run_id>
terra unknown graduate rcon_up --as rcon_ok   # → known; resolves the unknown

terra known link-run rcon_ok <run_id2>
terra known promote rcon_ok med
terra known show rcon_ok   # n, rate, k_true, k_false
```
