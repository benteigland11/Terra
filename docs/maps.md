# Map scopes (global vs experiment)

If everything lands in one bag, **knowns get muddy**. Terra has two tiers:

| Map | Path | Holds |
| --- | ---- | ----- |
| **global** | `.terra/map/` | Durable beliefs + default evidence; **all probes + lib** |
| **session** | `.terra/map/sessions/<id>/` | Experiment unknowns / knowns / runs / suites |

**Probes and lib are always global** — instruments are reusable.  
**Beliefs and evidence are scoped** — a night experiment does not pollute global knowns.

## CLI

```bash
terra map create night_census --purpose "Night mob rates" --use
terra map list
terra map show
terra map use global

# Status board — agent-first (JSON default, like cartograph status)
terra map status                 # active map → JSON + attention/next_actions
terra map status --all           # global + every session
terra map status --human         # pretty text for humans
terra map status --html --open   # browser view

# one-shot scope (does not change active_map file):
terra --map night_census known list
terra --map night_census probe run mobs --to '{"kind":"region"}'
```

Also: env `TERRA_MAP=night_census`.

Active map file: `.terra/active_map` (single line id).

## Layout

```text
.terra/
  active_map                 # optional: global | session_id
  map/
    map.json                 # global meta
    probes/                  # SHARED
    lib/                     # SHARED
    unknowns/ knowns/ plans/ runs/ suites/   # global beliefs
    sessions/
      night_census/
        map.json
        unknowns/ knowns/ plans/ runs/ suites/
```

## Workflow

1. Stable project claims → **global** map  
2. Risky trial / multi-run stats campaign → **`map create` session** + `--use`  
3. Promote to global later by hand (copy known + supporting runs) when ready  

No automatic merge (avoids accidental pollution).
