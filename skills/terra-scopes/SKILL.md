---
name: terra-scopes
description: >
  REQUIRED when choosing or switching Terra map scopes: global vs session maps,
  the map parent tree, terra map create/use/list, --parent, known/cohort adopt
  (promote up the tree), read-through/shadowing, terra --map <id> for one-shot
  commands, TERRA_MAP per-shell pinning for concurrent sessions, or when work
  is missing because the wrong map is active. Fire on "peer session switched
  the map", "two sessions on one project",
  "session map", "experiment map", "switch to global", "adopt this known",
  "promote to global", multi-map attention, "unknown not found but I created
  it", hide session work behind quiet global. Does NOT fire for unknown/known
  authoring details (terra-survey), route DAG (terra-route), or project init
  (terra-start).
---

# terra-scopes — the map tree (global root + session branches)

## What lives where

| Map | Holds |
| --- | ----- |
| **global** | Durable beliefs; **all probes + lib** (instruments shared); tree root |
| **session** | Experiment unknowns / knowns / runs / plans / suites; has a **parent** (default global) |

Probes are always **global**. Runs land on the **active** map (or `--map`).
Maps form a **tree**: session maps parent to global or to another session
(`--parent`). **Reads fall through** child → parent → … → global; **writes
stay local** to the active map.

## Commands

```bash
terra map status                 # attention/next_actions scan ALL maps
terra map status --all           # full per-map tables

terra map list                   # tree-rendered, parent-indented
terra map create <exp> --purpose "…" [--use] [--parent <map>]
terra map use <id|global>

terra --map <exp> known list     # one-shot pin (any subcommand)
TERRA_MAP=<exp> terra …          # per-shell pin (concurrent sessions)

terra known adopt <id> --from <map>    # promote ONE HOP up (to <map>'s parent)
terra cohort adopt <id> --from <map>   # coupled knowns move as a set
```

## Concurrent sessions

`.terra/active_map` is ONE shared pointer per project — two sessions running
`map use` clobber each other (last writer wins, failures are silent wrong
stores). When any peer session shares the project:

- **Pin per shell**: `export TERRA_MAP=<map>` — every terra command in that
  shell targets that map; peers flipping the pointer can't redirect you.
- Precedence: `--map` flag > `TERRA_MAP` > `.terra/active_map` > global.
- `map use` under `TERRA_MAP` prints a NOTE and does not change your shell's
  target; `map status`/`map list` show `(via env)` when pinned.
- A `TERRA_MAP` naming a nonexistent map raises `active_map_missing`
  (high) in map status — writes would land in a store no one reads.

## Read-through + shadowing

- `known get/show` resolve through the chain; the reading carries `"map"`
  (owner) and `"inherited": true` when it came from an ancestor. Consumer
  edges land on the **owning** map.
- A child known with the same id **shadows** the ancestor's for that subtree
  (graduate prints a NOTE). Rename if unintended.
- Deps (`known depend`) resolve through the chain too; an ancestor dep moving
  makes the child known stale.

## Adoption (climbing the tree)

- One hop per adopt: `--from <map>` lands on that map's parent. Climb by
  repeating; the CLI prints the next hop.
- Border bar re-checked every hop: backed, **>= med** confidence, methods not
  disagreeing, not stale. No `--force` — fix the evidence.
- Live runs are **copied** with the known; provenance stamped
  (`adopted_from` / `adopted_to`). Voided runs stay behind.
- Deps must already resolve from the destination — adopt dependency chains
  bottom-up (refusal lists the commands).
- Cohort members refuse solo adopt; `terra cohort adopt` moves the set
  (refused while inconsistent).

## Rules

1. Risky / messy trials → **session** map (`--use`); sub-experiments of an
   experiment → `--parent <exp>`.
2. No auto-merge up the tree; promotion is explicit `known adopt` per
   known/cohort, one hop at a time.
3. Wrong active map → silent wrong store for **writes** (“not found” on
   unknowns/runs). Check `map status` / `map list`.
4. `map status` without `--all` still **surfaces attention** across maps; use
   `--map` or `map use` when attention points elsewhere.
5. Freeze beliefs: either keep on a named session and document it, or adopt
   durable knowns up to **global** — don’t assume global filled itself.

## Done when

Active map matches the work; attention on other maps is handled or
intentional; proven session beliefs adopted up (or the stay is documented);
no accidental shadowing left behind.

*Beliefs: **terra-survey**. Program: **terra-route**.*
