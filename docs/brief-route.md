# Brief + route (program layer)

Terra is more than the map. Program control lives **in Terra**, not a separate PM app.

```text
BRIEF  SSOT design request (needs, deliverables, change control)
ROUTE  task DAG — main agent walks this, spawns subagents
MAP    survey / evidence (probes, knowns, formula, scopes)
```

**Agent skills (one job each):**

| Skill | Job |
| ----- | --- |
| **terra-start** | init map + brief + route skeleton |
| **terra-brief** | needs, deliverables, enablers, propose/accept |
| **terra-route** | lead loop, add/complete/block |
| **terra-survey** | unknown / known / plan / void |
| **terra-scopes** | global vs session maps |
| **terra-probe** | probe.py instruments |
| **terra-map** | thin index if surface unclear |

**Evidence `plan`** (multi/sequence legs) is map-layer belief composition — different word from route.

## Brief

```bash
terra brief init --title "YF-demo" --mission "concept fighter study"
terra brief set --need "stall gate holds" --deliverable "mission card + OML"
terra brief set --budget-points 100 --budget-notes "one-week package"
terra brief set --enabler "print_harness:Multi-view orthographic harness:tools/make_prints.py"
terra brief phase concept --title "Concept freeze"
terra brief show
terra brief propose --summary "tighten stall" --need "mean(stall_kt) <= 55"
terra brief accept <proposal_id>
terra brief enabler print_harness ready --path tools/make_prints.py
```

### Budget + task buckets (two ledgers)

| Layer | Where | Meaning |
| ----- | ----- | ------- |
| **Budget** | brief `budget_points` / `budget_notes` | Total authorized effort |
| **Plan** | task `plan_bucket` / `plan_points` | Baseline commitment (lockable) |
| **Actual** | task `bucket` / `points` | Working effort (may diverge) |

| Bucket | Points | Mode |
| ------ | ------ | ---- |
| **low** | **3** | implement |
| **medium** | **8** | validate |
| **high** | **21** | explore |

```bash
terra brief set --budget-points 100 --budget-notes "single phase"
terra route sector-add cad --title "CAD package" --points 40   # provision
terra route add foo --title "…" --bucket medium                # free pool
terra route add trays --title "…" --sector cad --bucket medium # from provision
terra route budget --human
terra route lock-plan
terra route add more_cad --title "…" --sector cad --bucket low # explode while locked
terra route set-effort foo --bucket high    # actual only if locked; may OVER BUDGET
terra route unlock-plan                     # WARNING — fails
terra route unlock-plan --confirm           # rewrites plan / sector reserves allowed
```

| Rule | |
| ---- | - |
| Initial plan | ≤ budget; sector plan ≤ reserve; unsectored ≤ free pool |
| Sectors | reserved point provisions to detail later |
| Plan locked | unsectored add blocked; `--sector` add OK; set-effort → actual only |
| Unlock | requires `--confirm` after warning |

Store: `.terra/brief.json` (budget) · `.terra/route.json` (tasks + `plan_locked`).

### Deliverables vs enablers

| | **Deliverables** | **Enablers** |
| - | ---------------- | ------------ |
| What | Customer / human pack | Internal means of production |
| Examples | mission card, `prints/`, mesh | drawing harness, CAD bridge, sim wrapper |
| Done means | files the brief promised | tooling **ready** (or graduated to Cartograph) |
| Route skill | `deliverable` | `tooling` |

Enablers are how you *make* blueprints/prints (AutoCAD-like harness), not the print pack itself. When stable, `graduates_to` a Cartograph widget id.

Subagents **read** the brief; they do not silent-edit it — use propose/accept.

## Route

```bash
terra route init
terra route add survey_aero --title "Survey aero tools" --skill terra-map \
  --phase concept --bucket medium
terra route add harness --title "Build print harness" --skill tooling --role enabler \
  --enabler print_harness --dep survey_aero --bucket medium
terra route add bricks --title "Extract widgets" --skill cg-plan --dep survey_aero \
  --bucket low
terra route next
terra route start survey_aero
terra route complete survey_aero --evidence "map status clean"
terra route budget
terra route lock-plan
terra route status
terra route block bricks --reason "waiting on registry"
```

Store: `.terra/route.json`.

`skill` hints which skill the subagent should load (`terra-map`, `terra-probe`, `tooling`, `cg-plan`, …).  
`role=enabler` + `--enabler <id>` links a task to `brief.enablers`.

## Main agent loop

1. `terra brief show` — still the mission?  
2. `terra route next` — what is pickable?  
3. Spawn subagent with task + skill + acceptance.  
4. `terra route complete|block` with evidence.  
5. **`terra route add`** when new work appears (skeleton routes are not closed).  
6. `terra map status` when the task was survey-shaped.  

Off-graph work is invisible to monitors. Scope change → brief propose; work breakdown → route add.

## Scars, not ceremony

Cartograph needed careful bricks. Brief/route get better when real projects
leave scars: missing fields, bad skill tags, weak acceptance lines. Ship thin;
amend when DX hurts.
