# Suites (recipes)

**Composition, not domain plugins.** A suite is an ordered list of probe ids
plus an optional default `to`. Terra still knows nothing about Minecraft.

## Why

Running 12× `terra probe run` by hand is noise. A suite is one verb:

```bash
terra suite create night_census \
  --probes town_layout,agent_lens,anomalies,settlement_census

terra suite run night_census --to '{"kind":"town","id":"spawn"}'
```

Each probe still stamps its own run under `.terra/map/runs/`. The suite only
sequences them and shares `to`.

## Record (`.terra/map/suites/<id>.json`)

```json
{
  "schema_version": 1,
  "id": "night_census",
  "purpose": "…",
  "probes": ["town_layout", "agent_lens", "anomalies", "settlement_census"],
  "default_to": { "kind": "town" }
}
```

| Field | |
| ----- | - |
| probes | ordered list (required, non-empty) |
| default_to | optional shared target if `suite run` omits `--to` |

## CLI

```bash
terra suite create <id> --probes a,b,c [--to '{…}'] [--purpose "…"]
terra suite list
terra suite show <id>
terra suite validate [<id>]          # meta + level-1 each probe
terra suite run <id> --to '{…}' [--continue-on-error] [--dry-run]
                                   [--strict-to] [--strict-status]
```

- Missing probe at create → error (create probes first).  
- `suite validate` → suite record + each probe L1 (no live survey).  
- Probe failure mid-suite → stop (default) or continue with `--continue-on-error`.  
- `--strict-to` / `--strict-status` → same as `probe run` (CI).  
- Output lists each probe’s `run_id` for `unknown link-run`.

## Non-goals

- No domain-specific suite types  
- No parallel fan-out (v0 is ordered)  
- No auto-link to unknowns (agent still `link-run` if needed)  
