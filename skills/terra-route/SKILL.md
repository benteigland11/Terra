---
name: terra-route
description: >
  REQUIRED when walking or expanding the Terra task DAG: route next/status/add/
  start/complete/block, lead-agent loop, off-graph work, claim-shaped complete
  evidence (run_id/known_id), skill tags (tooling/deliverable/terra-map/…). Fire
  on "what's next", "add a task", "complete this task", "route is stuck",
  subagent task handoff, or finishing work without route complete. Does NOT
  fire for brief field edits alone (terra-brief), unknown/known/plan authoring
  (terra-survey), or init (terra-start).
---

# terra-route — task DAG / lead loop

Store: `.terra/route.json`  
Bootstrap if missing: **terra-start**.  
Claims need map evidence → **terra-survey** (+ **terra-probe** for instruments).

## Lead loop

```bash
terra brief show              # still the mission? (details: terra-brief)
terra route next              # pickable / in_progress
terra map status              # attention (details: terra-scopes / terra-survey)
terra route start <id>
# do work (or subagent with task id, skill, acceptance)
terra route complete <id> --evidence "…"
# or: terra route block <id> --reason "…"
terra route next
```

```bash
terra route status            # counts + next + blocked
terra route status --human
```

## Expand the route (required when work appears)

Seeded routes are **skeletons**. Off-graph work is invisible to monitors.

```bash
terra route add <slug> --title "…" \
  --skill terra-map|terra-probe|tooling|deliverable|cg-plan|any \
  --phase <phase> --dep <task> \
  [--role enabler|deliverable|survey|orchestration|any] \
  [--enabler <brief_enabler_id>] \
  [--sector <sector_id>] \       # draw from a provision
  [--bucket low|medium|high] \   # low=3 medium=8 high=21
  [--points 3|8|21] \
  --accept "…"
```

| Discover | Do |
| -------- | -- |
| New harness | `--skill tooling --role enabler --enabler <id>` |
| Split big task | children with `--dep` parent |
| Detail a provision | `--sector cad --bucket medium` |
| Multi-step blocker | `route add` steps — not chat-only |
| New need/deliverable/enabler | **terra-brief** propose/accept, then `route add` |

### Effort buckets (points)

| Bucket | Points | Mode |
| ------ | ------ | ---- |
| **low** | **3** | Implement — path known |
| **medium** | **8** | Validate — branches then conclude |
| **high** | **21** | Explore — novel / deep |

Project total: `terra brief set --budget-points N` (**terra-brief**).

### Sectors (provisions)

Reserve budget before you know fine tasks:

```bash
terra route sector-add cad --title "CAD package" --points 89
terra route sector-add thermal --title "Thermal" --points 40
# free_pool = budget − sum(reserves)
terra route add trays --title "…" --sector cad --bucket medium
```

While **plan locked**, only `route add … --sector <id>` is allowed (explode reserves).

### See allocation

```bash
terra route budget --human
```

Shows budget, free_pool, each sector reserved/plan/actual, and tasks.

### Plan lock + set-effort

| | plan_* | working |
| - | ------ | ------- |
| `route add` | = working | set |
| `set-effort` unlocked | rewritten (≤ budget) | rewritten |
| `set-effort` locked | frozen | may exceed budget |
| `route add` locked | only with `--sector` | draws reserve |

```bash
terra route lock-plan
terra route set-effort <id> --bucket medium
terra route unlock-plan              # WARNING — fails
terra route unlock-plan --confirm
```

## Complete with hard evidence

| Task shape | Evidence on `complete` |
| ---------- | ---------------------- |
| **Claim-shaped** (gates, mass, cost, fit, …) | `run_id=` and/or `known_id=` / `plan_id=` (and probe id if new) |
| **Instrument build** | live run via **terra-probe**; pass `run_id=` |
| **Pure artifact** (prose after freeze) | paths OK **if** freeze knowns exist; cite `known_id=` |

```bash
terra route complete <id> --evidence "run_id=… known_id=… path=…"
```

File path alone is **not** enough for claim-shaped work.

## Block / unblock

```bash
terra route block <id> --reason "…"
terra route unblock <id>
```

## Subagents

Give: task id, `skill`, acceptance from route, “read `terra brief show` first.”

## Done when

Pickable work is done or honestly blocked; claim tasks have map-linked evidence; new work was `route add`ed, not only chatted.

*Brief fields: **terra-brief**. Readings: **terra-survey**. Instruments: **terra-probe**.*

## Deliverable tasks run the gate

`terra route complete` on a task with skill/role `deliverable` runs
`terra gate` (all maps). Blocking unknowns, stale/unbacked knowns, or
incomplete plans **refuse the complete**. Fix the debt, or record an explicit
override:

```bash
terra route complete ship --skip-gate "reason"   # override lands in task evidence
```

## Claim-shaped tasks need evidence refs

`route complete` on a task with skill `terra-map`/`terra-probe` (or role
`survey`) refuses prose-only completion. Cite the map:

```bash
terra route complete survey --run <run_id> [--run …] [--known <known_id>]
terra route complete survey --freehand "why no instrument applies"  # recorded
```

Refs are validated: runs must exist and not be voided; knowns must be backed
and their methods must not disagree. Evidence entries carry structured
`runs`/`knowns` lists, not just prose.

## Route hygiene

- Dep cycles are rejected at add/save time (`dependency cycle: a -> b -> a`) —
  a cycle would silently make tasks never-pickable.
- `route status` carries `attention`: `task_blocked` (with reason) and
  `task_stalled` (in_progress untouched ≥7 days — complete/block or split).
