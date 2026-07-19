# Map unknowns

Named gaps. If an active unknown exists, the result is not composable and the
gate fails. The legacy `blocks_build: false` escape hatch no longer softens an
unknown; a usable provisional value must be modeled as an
[assumption](assumptions.md).

## Record (`.terra/map/unknowns/<id>.json`)

| Field | Required | Notes |
| ----- | -------- | ----- |
| id | yes | slug = filename |
| claim | yes | what we do not know |
| status | yes | open \| probing \| blocked \| resolved \| wont_care |
| blocks_build | yes | default true |
| evidence_needed | yes when open/probing | what reading would close it |
| probe_id / probe_ids | optional | linked instrument(s) |
| run_ids / primary_run_id | optional | **stamped evidence** (first-class) |
| resolved_by / notes | for resolve | prose trail |

### Resolve trail (no silent resolve)

At least one of:

- `resolved_by` or `notes`
- `probe_id` / `probe_ids`
- **`run_ids`** (preferred when you have a real reading)

## CLI

```bash
terra unknown create <id> --claim "…" --evidence "…"
terra unknown list
terra unknown link-probe <id> <probe_id>
terra unknown link-run <id> <run_id> [--primary]
terra unknown unlink-run <id> <run_id>
terra unknown show <id>          # probes + linked runs + last status
terra unknown status <id> resolved   # ok if run_ids already linked
terra unknown status <id> resolved --resolved-by "…"
terra unknown validate
```

Preferred close loop — **graduate** when the answer should live on as a known
(the only way knowns are born), plain resolve when it should not:

```bash
terra probe run <probe> --to '{…}'
terra unknown link-run <unknown> <run_id>
terra unknown graduate <unknown> [--as <known_slug>]   # typed + live run → known
terra unknown graduate <u1> --with <u2,u3> --as <slug> # siblings funnel into ONE known
terra unknown graduate <late_u> --into <known_id>      # merge into existing known
# or, answered but no durable anchor needed:
terra unknown status <unknown> resolved
```
