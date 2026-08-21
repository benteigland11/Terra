---
name: terra-route
description: >
  REQUIRED when walking or expanding the Terra task DAG: route next/status/add/
  start/complete/block/log, lead-agent loop, off-graph work, claim-shaped complete
  evidence (run_id/known_id), skill tags (tooling/deliverable/terra-map/…). Fire
  on "what's next", "add a task", "complete this task", "route is stuck",
  "what happened today", the urge to keep a shadow md progress log,
  subagent task handoff, or finishing work without route complete. Does NOT
  fire for brief field edits alone (terra-brief), unknown/known/plan authoring
  (terra-survey), or init (terra-start).
---

# terra-route — task DAG / lead loop

Store: `.terra/route.json`  
Bootstrap if missing: **terra-start**.  
Claims need map evidence → **terra-survey** (+ **terra-probe** for instruments).

## Lead loop

**Open with `terra sitrep`** — ONE call for brief + route + budget + map +
gate, instead of the four separate reads agents used to start with. On a large
program that is 3.6 MB → 4.8 KB of output and four turns saved. See **Shell
economics** below for why turns, not bytes, are the unit of cost.

```bash
terra sitrep --human          # mission + counts + budget + attention rollup + gate
# default JSON to parse · --full for untruncated lists · ALWAYS exits 0
terra route start <id> --agent <you>   # claim ownership (attributes a stranded lead)
# do work (or subagent with task id, skill, acceptance)
terra route heartbeat <id>    # ping during long silent work — I'm still alive
terra route complete <id> --evidence "…"
# or: terra route block <id> --reason "…"
terra route next
```

**Claim + heartbeat, because status is not liveness.** `route start --agent`
stamps an owner and opens a heartbeat; a task that dies mid-work simply stops
pinging. Send `terra route heartbeat <id>` during long silent stretches so a
live lead stays distinguishable from a dead one. **Never infer liveness from
`in_progress` and re-dispatch** — that is how a stranded route caused a
double-writer collision. If `route status` shows `task_no_heartbeat`, verify
the owner is really gone before touching its work.

```bash
terra route status            # counts + next + blocked (FULL task table — large)
terra route status --human
terra route log --human       # chronological history: completions + evidence + blocks
terra route log --limit 20    # last N events (JSON envelope by default)
```

## Shell economics — batch, and never `&&`

An agent turn costs a re-read of its whole context (~14k–28k tokens) **whatever
the command is**: `terra route status` costs the same turn as a CFD run. On a
measured 11-day program, Terra-bearing turns were **26% of total token spend**
while the commands' own output was under 4% of that. The expense is the round
trip.

```bash
# ONE call, one turn — this is the default shape for reads/bookkeeping
terra sitrep
terra route log --limit 20
terra known get cd0_cruise
```

- **Separate with `;` or newlines — never `&&`.** Terra uses nonzero exits as
  *verdicts*: `terra gate` exits 1 whenever violations exist. An `&&` chain
  aborts there, every later command silently never runs, and the result still
  looks clean — you will report work you did not do. `sitrep` deliberately
  always exits 0 so it is safe anywhere in a chain.
- **Never `| head` a Terra command to make it fit.** That is silent truncation
  and you cannot tell a short list from a clipped one. Prefer `sitrep`, which
  truncates explicitly and declares what it dropped under `truncated`.
- **Never spend a turn waiting** — no `sleep`, `true`, or `until [ -f … ]`
  polling. A full context re-read to learn nothing.

**Routes ARE the record.** Do not keep a shadow markdown log/tracker of
what happened — `route complete --evidence/--run/--known` is the write,
`terra route log` is the read. Cross-route synthesis is a report
deliverable, not a parallel tracker file.

## Expand the route (required when work appears)

Seeded routes are **skeletons**. Off-graph work is invisible to monitors.

```bash
terra route add <slug> --title "…" \
  --skill terra-map|terra-probe|tooling|deliverable|cg-plan|any \
  --phase <phase> --dep <task> \
  [--role enabler|deliverable|survey|orchestration|any] \
  [--enabler <brief_enabler_id>] \
  [--sector <sector_id>] \       # draw from a provision
  [--bucket low|medium|high] \   # low=3 medium=8 high=21  — HOW MUCH effort
  [--priority p0|p1|p2|p3] \     # default p2             — WHICH work
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

### Phases — the lifecycle axis

`--phase` is only a real instrument when the brief DECLARES phases
(`terra brief phase <id> --title "…"`, order = lifecycle order). Then:

```bash
terra route phases --human    # per-phase open/done/blocked/unreachable + exit
terra route next --phase design
```

- **Declared phases validate.** Once any phase exists, `route add --phase` with
  an undeclared id is REFUSED. Projects declaring none keep free text.
- **Exit criterion:** a phase is exit-ready when it holds >=1 task and every
  task is `done` or `cancelled`. **An empty phase is NOT ready** — no tasks
  means unplanned, not complete.
- **Current phase** = first declared phase not yet exit-ready. Undeclared tags
  are reported but never become current; a typo must not redefine where the
  program is.
- **Unreachable tasks block phase exit** (`phase_exit_blocked_by_unreachable`).
  A phase of routes stranded on cancelled deps otherwise reads "almost done"
  forever.
- **Unphased tasks block NO phase exit and count toward no phase.** That hole is
  reported as `tasks_unphased` — if you use phases, tag everything.

### Priority (p0..p3) — orthogonal to effort

Bucket says **how much effort**; priority says **which work**. They are
different questions and a task can be any combination (a p0 can be `low`; a
p3 can be `high`). The letters are `p0..p3` on purpose — `low|medium|high`
already means effort, and a `--bucket high` typed when `--priority p0` was
meant is a silent wrong-field write nothing downstream would catch.

| Priority | Meaning |
| -------- | ------- |
| **p0** | Spine — the program cannot finish without this |
| **p1** | Required for the current phase |
| **p2** | Normal backlog (**default**) |
| **p3** | Deferred — kept as record, not scheduled |

```bash
terra route prioritize <id> [<id>…] --priority p0 --reason "on the spine"
terra route next                      # sorted p0 first
terra route next --priority p0        # only the spine
```

Rules that matter:

- **`route next` is priority-SORTED under a limit**, so low-priority work can
  sit unseen behind a full page of p0. `route status` →
  `counts.by_priority_open` is never truncated — that is how you learn what
  the window hid. `sitrep --human` prints the same rollup.
- **Re-ranking never moves the budget** — it does not touch points or the plan
  baseline, so it works under `plan_locked` with no unlock.
- **p3 is not cancel.** `cancel` asserts *this should never be worked* (dead
  premise, wrong object). p3 says *real, but not now*. Reach for p3 when you
  want a finding kept honestly on the record without it competing for
  attention; reach for `cancel` when the premise is dead.
- **Legacy tasks backfill to p2, never p0.** An unranked backlog silently
  promoted to urgent would make the first sorted `next` a lie.
- **Priority does NOT rescue an unreachable route.** If a task's dep was
  `cancelled`, it can never become pickable — a cancelled dep never turns
  `done` — and `route next` will not surface it at ANY priority. Check
  `route status` for `kind=task_dep_cancelled` (the root, severity block) and
  `kind=task_unreachable` (everything downstream, carrying `root`). Fix the
  ROOT: re-point its dep onto the live successor, or cancel the task too if
  its premise died with the dep. Ranking and reachability are independent
  failures — a p0 on a dead route is silence with a label on it.
- **Before you `cancel`, read the NOTE.** `route cancel` now names every live
  task the cancel will strand. Cancelling is how superseded approaches get
  retired, so the routes it strands are disproportionately the spine.
- `--reason` lands in `route log` as a `priority` event, so a re-rank is
  auditable and is *not* rendered as a completion.

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

## Concurrent leads — route.json can refuse your write

Several leads drive Terra at once, so `load -> mutate -> save` can race. If
another agent wrote `route.json` between your read and your write, the save is
**refused** with `ConcurrentRouteWrite` rather than silently discarding their
edit. Recovery is simply: re-read, re-apply your change, save again. Writes are
atomic, so you will never read a half-written route file.

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
- `route status` carries `attention`: `task_blocked` (with reason),
  `task_stalled` (in_progress untouched ≥7 days — complete/block or split),
  and `task_no_heartbeat` (owner's heartbeat quiet ≥6h — possible dead lead;
  carries `owner` + `hours_since_heartbeat`). Treat `task_no_heartbeat` as
  "verify before touching," not "free to re-dispatch."
