---
name: terra-map
description: >
  Router for Terra program+map work when the specific surface is unclear, or
  when the user says "terra-map" / "use terra". Prefer the focused skill when
  known: terra-start (init), terra-brief (needs/enablers/propose), terra-route
  (DAG/lead loop/complete), terra-survey (unknown/assumption/known/calculation/plan/void), terra-scopes
  (global vs session), terra-probe (probe.py). Fire on general Terra campaign
  questions, "how do I use terra here", or mixed brief+route+map in one turn —
  then open the matching child skill(s). Does NOT replace those skills; does
  NOT implement probe.py (terra-probe); does NOT develop Terra CLI (terra-dev).
---

# terra-map — index (not the whole manual)

Terra program layer sits **above** Cartograph bricks.  
Procedure is split so each skill is one job. **Open the child skill** and follow it.

| Skill | One job |
| ----- | ------- |
| **terra-start** | `terra init` + brief + route skeleton + budget |
| **terra-brief** | needs, deliverables, enablers, **budget_points**, propose/accept |
| **terra-route** | lead loop, buckets 3/8/21, **lock-plan / set-effort / budget** |
| **terra-survey** (incl. `terra design` baseline + artifacts) | unknown/assumption → evidence → known; calculation composition; plan/void |
| **terra-scopes** | global vs session maps |
| **terra-probe** | implement/validate/run instruments |

## Soft vs hard (always)

| Soft | Hard |
| ---- | ---- |
| “Looks good” after one sample | known at earned confidence (**terra-survey**) |
| Chat dump of work | **terra-route** complete + run_id/known_id |
| Freehand domain | **terra-survey** + **terra-probe** |
| Off-graph side quests | **terra-route** add |
| Silent scope creep | **terra-brief** propose/accept |
| Route green, map empty | incomplete — **terra-survey** |
| Infinite thrash | **budget_points** + buckets; check `route budget` |

## Typical lead sequence

1. No `.terra/`? → **terra-start** (set `budget_points`, bucket tasks, prefer `lock-plan`)  
2. Each cycle → **terra-route** (`route next`, `route budget`, complete with evidence)  
3. Work got harder → **terra-route** `set-effort` (actual only if plan locked)  
4. Claim-shaped task → **terra-survey** (+ **terra-probe** if no instrument)  
5. Wrong map / experiment isolation → **terra-scopes**  
6. Scope / raise budget / enablers → **terra-brief**  
7. Reusable code → **cg-plan** / Cartograph  

## Handoffs

```text
terra-route  --need instrument-->  terra-probe  --run_id-->  terra-survey
terra-route  --scope change----->  terra-brief
terra-survey --wrong map-------->  terra-scopes
```

## Not here

- Full CLI catalogs and step-by-step playbooks → **child skills**  
- Kickoff markdown templates → project files / human  
- Cartograph widget create → **cg-plan** / **cg-create**  

If you only remember one rule: **open the skill for the surface you are touching; do not freehand Terra from memory.**
