# Terra

Layers **above** Cartograph. v0 focus: **map probes** (instruments), not full planning.

| Layer | Role |
| ----- | ---- |
| **Cartograph** | Bricks |
| **Map / probes** | Survey instruments + (later) stamped runs |
| **Terra route** | Goal / phases — later |

## Install

```bash
pip install -e ~/Cartograph/Terra
terra --version
```
# Lives next to Cartograph for now; own git history (not pushed).

Global agent skill (Grok): `terra-map` under `~/.grok/skills/terra-map/`.

## Map scopes (global vs experiment)

One bag of knowns for the whole project gets **muddy**. Terra splits:

| Map | Path | Holds |
| --- | ---- | ----- |
| **global** | `.terra/map/` | Durable beliefs + default evidence; **all probes + lib** |
| **session** | `.terra/map/sessions/<id>/` | Experiment unknowns / knowns / runs / suites |

```bash
terra map create night_census --purpose "Night mob rates" --use
terra map list
terra map use global          # back to durable map
terra map status              # JSON default (agent-first)
terra map status --human      # pretty text
terra map status --html --open
terra --map night_census known list   # one-shot scope
```

Agent envelope follows Cartograph (`universal-agent-response`):  
`{status, data, meta?}` with `data.attention` + `data.next_actions`.  
See [docs/agent-io.md](docs/agent-io.md), [docs/maps.md](docs/maps.md).

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
.terra/
  active_map              # global | session id
  map/
    probes/<id>/          # SHARED instruments
    lib/                  # SHARED helpers
    unknowns/ knowns/ runs/ suites/   # global beliefs
    sessions/<exp>/       # experiment-scoped beliefs + evidence
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

**Knowns** (typed anchors) are born only by **graduating** an evidence-bearing
unknown — no run, no known:

```bash
# probe returns measures: [{"quantity":"hostile_count","value":3}]
terra unknown create est --type number --quantity hostile_count \
  --claim "…?" --evidence "probe reading"
terra unknown link-run est <run_id>
terra unknown graduate est [--as <known_slug>]  # → known (low, provisional); resolves unknown
terra known link-run est <run_id2>
terra known promote est med   # blocks if n too small
terra known show est          # n, mean, std
```

`terra known create` is retired; a known whose evidence is later voided away
shows up in `map status` attention as `known_unbacked`.

**Suites** (ordered recipes, shared `to` — not domain plugins):

```bash
terra suite create night_census --probes town_layout,agent_lens,anomalies
terra suite run night_census --to '{"kind":"town"}'
```

**Plans** (above types — multi-evidence + sequential):

```bash
terra plan create gate --mode sequence --claim "…" \
  --leg reach:boolean:rcon_up --leg smoke:boolean:smoke_ok:n=3
terra plan link-run gate <run> --leg reach
# sequence blocks linking smoke until reach is satisfied
```

See [docs/evidence-plan.md](docs/evidence-plan.md).

**Adjust (retract bad evidence)** — map is not append-only:

```bash
terra run void <run_id> --reason "probe bug"   # preferred
terra known unlink-run est <run_id>
terra known delete est
```

See [docs/adjust.md](docs/adjust.md).

**Product path:** `probes/` + `unknowns/` + `runs/` + `lib/` + `suites/`.  
**Legacy:** `.terra/map/data/` (old capture sketch) — ignore for agents.

See [docs/probe-level1.md](docs/probe-level1.md), [docs/unknowns.md](docs/unknowns.md).
