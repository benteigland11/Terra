# Recommended `to` schema (convention)

Terra does **not** own domain targets (no Minecraft funnels).  
`to` stays freeform for **hard** validation: non-empty is enough to run.

For **composition** across probes, use this thin envelope. Extra keys are fine;
probes may ignore what they do not understand.

## Recommended shape

```json
{
  "kind": "entity|region|path|server|literal|default",
  "id": "…",
  "at": "ISO-8601 optional wall intent",
  "window": { "day_phase": "night|day|any" },
  "limit": 50
}
```

| Key | Role | Required by Terra? |
| --- | ---- | ------------------ |
| **kind** | What class of target (shared vocabulary) | **Warn** if missing on **live** runs |
| **id** | Primary handle (uuid, path, name, …) | No |
| **at** | Wall-clock intent for the survey | No |
| **window** | Soft temporal filter (e.g. day phase) | No |
| **limit** | Cap on results | No |

### Builtin `kind` values (recommended)

| kind | Typical use |
| ---- | ----------- |
| `entity` | One actor / mob / block entity |
| `region` | Spatial bounds (probe-defined fields ok: x0,z0,…) |
| `path` | Filesystem or resource path |
| `server` | Live process / RCON / host endpoint |
| `literal` | Opaque string target (`parse_to_arg` fallback) |
| `default` | Probe’s built-in default target |

**Project-specific kinds are allowed** (e.g. `farm_plot`, `citizen_job`).  
Terra only soft-notes that they are non-builtin.

## Examples

```json
{ "kind": "region", "id": "spawn_chunk", "x0": 0, "z0": 0, "x1": 16, "z1": 16, "limit": 50 }

{ "kind": "server", "id": "local-dev", "host": "127.0.0.1", "port": 25575 }

{ "kind": "entity", "id": "uuid-or-name", "window": { "day_phase": "night" } }

{ "kind": "path", "id": "world/region/r.0.0.mca" }
```

## Validation policy

| Check | Level |
| ----- | ----- |
| `to` non-empty | **Block** (level-1 / run) |
| `kind` missing on live run | **Warn** only |
| unknown / project kind | **Warn** (optional note) |
| odd `limit` / `window` types | **Warn** only |
| dry_run / level-1 fixture | No schema warns |

## CLI

```bash
terra probe run mobs_in_region --to '{"kind":"region","x0":0,"z0":0,"x1":16,"z1":16,"limit":50}'

# CI: treat to-schema warnings as failures (run is still stamped)
terra probe run mobs_in_region --to '{"uuid":"x"}' --strict-to
```

Default: warnings only. **`--strict-to`** fails exit code after stamping.
