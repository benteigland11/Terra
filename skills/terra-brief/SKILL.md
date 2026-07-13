---
name: terra-brief
description: >
  REQUIRED when reading or changing the Terra design request: brief show/set,
  needs, deliverables, non-goals, enablers lifecycle (needed|building|ready|
  graduated), budget_points / budget_notes, phases, or brief propose/accept/reject.
  Fire on "what's the mission", "set the budget", "add a need", "mark enabler
  ready", "scope change", "propose brief change", silent urge to edit
  .terra/brief.json. Does NOT fire for route DAG, lock-plan, or set-effort
  (terra-route), map beliefs (terra-survey), or project init (terra-start).
---

# terra-brief — design request SSOT

Store: `.terra/brief.json`  
Bootstrap if missing: **terra-start**.

## Show

```bash
terra brief show           # JSON default
terra brief show --human
```

Fields: `mission`, `budget_points`, `budget_notes`, `needs`, `deliverables`,
`non_goals`, `enablers`, `phases`, `version`.

## Set (bumps version)

```bash
terra brief set \
  --need "…" \
  --deliverable "…" \
  --non-goal "…" \
  --enabler "id:Title:path" \
  --budget-points 100 \
  --budget-notes "one-week package / single phase" \
  --title "…" --mission "…" --status active
# --clear-budget-points to null out budget
# --replace-lists to replace needs/deliverables/… instead of append
```

```bash
terra brief phase <id> --title "…"
```

## Budget (program effort — brief owns the total)

| Field | Meaning |
| ----- | ------- |
| `budget_points` | **Total licensed effort** for the program (absolute size) |
| `budget_notes` | Horizon / team / depth note for humans |

Task weights live on the **route** (**terra-route**):

| Bucket | Points | Mode |
| ------ | ------ | ---- |
| **low** | **3** | implement — path known |
| **medium** | **8** | validate — branches then conclude |
| **high** | **21** | explore — novel / deep |

### Rules involving brief budget

1. When `budget_points` is set, **`route add` must use `--bucket` / `--points`**.  
2. **Initial plan** (sum of task points before/while plan unlocked) **cannot exceed** `budget_points`.  
3. Shrinking `budget_points` below current **plan** allocation fails.  
4. **Plan lock / rebucket / unlock** → **terra-route** (`lock-plan`, `set-effort`, `unlock-plan --confirm`).  
5. See allocation anytime:

```bash
terra route budget           # plan vs actual vs budget_points
terra route budget --human
```

Brief does **not** store plan lock (that is `route.plan_locked`). Brief stores **how big the program is authorized to be**.

## Enablers (means of production — not customer pack)

| Status | Meaning |
| ------ | ------- |
| needed | declared, not built |
| building | in progress |
| ready | usable path on disk |
| graduated | extracted to Cartograph (`--graduates-to`) |
| abandoned | dropped |

```bash
terra brief enabler <id> building --path tools/…
terra brief enabler <id> ready --path tools/…
terra brief enabler <id> graduated --graduates-to <widget-id>
```

**Deliverables** = human pack. **Enablers** = harnesses that produce it.  
Route work on enablers: skill `tooling`, role `enabler`, `--enabler <id>` → **terra-route**.

## Change control

Subagents **read** the brief. Do not hand-edit `brief.json` for scope creep.

```bash
terra brief propose --summary "…" [--need …] [--deliverable …] [--enabler id:title] [--mission …]
terra brief accept <proposal_id>
terra brief reject <proposal_id>
```

Raising budget mid-flight: `terra brief set --budget-points N` (must still cover **plan** allocation if you only shrink).

## Done when

Brief reflects mission + **budget_points** (when effort-capped); enablers honest; scope via propose/accept.

*Tasks / plan lock / set-effort: **terra-route**. Init: **terra-start**. Beliefs: **terra-survey**.*
