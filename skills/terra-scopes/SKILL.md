---
name: terra-scopes
description: >
  REQUIRED when choosing or switching Terra map scopes: global vs session maps,
  terra map create/use/list, terra --map <id> for one-shot commands, or when
  work is missing because the wrong map is active. Fire on "session map",
  "experiment map", "switch to global", multi-map attention, "unknown not found
  but I created it", hide session work behind quiet global. Does NOT fire for
  unknown/known authoring details (terra-survey), route DAG (terra-route), or
  project init (terra-start).
---

# terra-scopes — global vs session maps

## What lives where

| Map | Holds |
| --- | ----- |
| **global** | Durable beliefs; **all probes + lib** (instruments shared) |
| **session** | Experiment unknowns / knowns / runs / plans / suites |

Probes are always **global**. Runs land on the **active** map (or `--map`).

## Commands

```bash
terra map status                 # attention/next_actions scan ALL maps
terra map status --all           # full per-map tables
terra map status --human

terra map list
terra map create <exp_slug> --purpose "…" [--use]
terra map use <id|global>

terra --map <exp> known list     # one-shot pin (any subcommand)
terra --map <exp> unknown show <id>
```

## Rules

1. Risky / messy trials → **session** map (`--use`).  
2. No auto-merge session → global; promote by re-encoding or re-linking deliberately.  
3. Wrong active map → silent wrong store (“not found”). Check `map status` / `map list`.  
4. `map status` without `--all` still **surfaces attention** across maps; use `--map` or `map use` when attention points elsewhere.  
5. Freeze beliefs: either keep on a named session and document it, or deliberately land durable knowns on **global** — don’t assume global filled itself.

## Done when

Active map matches the work; attention on other maps is handled or intentional; session dirt not dumped into global by accident.

*Beliefs: **terra-survey**. Program: **terra-route**.*
