# Terra

Layers **above** Cartograph. v0 focus: **map probes** (instruments), not full planning.

| Layer | Role |
| ----- | ---- |
| **Cartograph** | Bricks |
| **Map / probes** | Survey instruments + (later) stamped runs |
| **Terra route** | Goal / phases — later |

## Install

```bash
pip install -e /path/to/Terra
terra --version   # terra 0.1.0
```

Global agent skill (Grok): `terra-map` under `~/.grok/skills/terra-map/`.

## Probes + unknowns (now)

```bash
cd /your/modded-minecraft-project

# Named gap (stuck → do this, never silent)
terra unknown create mob_query \
  --claim "How do we list hostiles in a region on this loader?" \
  --evidence "probe dump of mobs or command surface"

# Instrument (auto-inits .terra/map)
terra probe create mobs_in_region \
  --purpose "Hostiles in a given region" \
  --kind watch

terra unknown link-probe mob_query mobs_in_region
# edit .terra/map/probes/mobs_in_region/probe.py for THIS install
terra probe validate mobs_in_region
terra unknown validate
```

Layout:

```text
.terra/map/
  probes/<id>/probe.json + probe.py
  unknowns/<id>.json
```

**Level-1 probe validation:** input `to` → output `to`/`status`/`artifacts` (loud I/O steps).  
**Unknown validation:** claim, evidence_needed when open, no silent resolve.

### Run (stamped evidence)

```bash
terra probe run mobs_in_region --to '{"kind":"region","x0":0,"z0":0,"x1":16,"z1":16}'
terra run list
# → .terra/map/runs/<run_id>/meta.json + artifacts/ (time, from, to, status, sha256)
```

Shared helpers: put modules in `.terra/map/lib/` (on `sys.path` during validate/run).

**Recommended `to` envelope** (warn-only if `kind` missing on live runs):

```json
{ "kind": "region|entity|path|server|literal|default", "id": "…", "limit": 50 }
```

See [docs/to-schema.md](docs/to-schema.md). Probes may ignore extra keys.

**Recommended `status`:** `ok` | `degraded` | `unavailable` | `empty` | `error`  
(freeform still allowed; live runs warn). Filter: `terra run list --status unavailable`.  
See [docs/status-vocab.md](docs/status-vocab.md).

**Suites** (ordered recipes, shared `to` — not domain plugins):

```bash
terra suite create night_census --probes town_layout,agent_lens,anomalies
terra suite run night_census --to '{"kind":"town"}'
```

**Product path:** `probes/` + `unknowns/` + `runs/` + `lib/` + `suites/`.  
**Legacy:** `.terra/map/data/` (old capture sketch) — ignore for agents.

See [docs/probe-level1.md](docs/probe-level1.md), [docs/unknowns.md](docs/unknowns.md).
