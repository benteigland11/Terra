# Recommended status vocabulary

Level-1 / run validation only require **non-empty string** `status`.  
Free strings (`missing_layout`, `rcon_timeout`, …) remain legal.

For **filterable map tooling** (`terra run list --status …`), prefer this set:

| status | Meaning |
| ------ | ------- |
| **ok** | Survey succeeded with usable evidence |
| **degraded** | Partial evidence; usable with care |
| **unavailable** | World / server / instrument down |
| **empty** | Succeeded; nothing in scope (valid zero) |
| **error** | Instrument failed |

## Policy

| Check | Level |
| ----- | ----- |
| non-empty string | **Block** (level-1 / run) |
| not in recommended set | **Warn** only on live runs |
| custom domain statuses | Allowed — document in the probe |

Domain detail can still live in artifacts or notes; keep `status` coarse so
agents and CLI can filter without parsing prose.

## Examples

```python
return {"to": to, "status": "ok", "artifacts": [...]}
return {"to": to, "status": "empty", "artifacts": [...]}   # no mobs in region
return {"to": to, "status": "unavailable", "artifacts": [...]}  # RCON down
return {"to": to, "status": "degraded", "artifacts": [...]}   # partial parse
return {"to": to, "status": "error", "artifacts": [...]}
```

## CLI

```bash
terra run list --status unavailable
terra run list --status empty --probe mobs_in_region

# CI: freeform status fails exit (run still stamped)
terra probe run p --to '{"kind":"region"}' --strict-status
```
