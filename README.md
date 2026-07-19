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

## Probes + unknowns + assumptions

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
    unknowns/ knowns/ calculations/ runs/ suites/   # global map state
    sessions/<exp>/       # experiment-scoped beliefs + evidence
```

**Level-1 probe validation:** input `to` → output `to`/`status`/`artifacts` (loud I/O steps).  
**Unknown validation:** claim, evidence_needed when open, no silent resolve.

Unknowns are hard gates. When design must proceed on a declared provisional
number or boolean, use an **assumption** instead:

```bash
terra assumption create efficiency --type number --quantity efficiency \
  --value 0.90 --claim "What efficiency will the converter sustain?" \
  --reason "Working vendor-class basis" --evidence "Bench measurement"
terra assumption get efficiency       # conditional=true; never a clean known
terra assumption set efficiency --value 0.86 --reason "EOL derating basis"
terra assumption graduate efficiency  # requires linked evidence; known uses evidence
```

Assumptions keep progress moving but remain loud in map status and gate
notices. See [docs/assumptions.md](docs/assumptions.md).

### Calculations: map values → derived values

Calculations compose only declared knowns and assumptions as external inputs.
Formula literals are valid logic and are inventoried in stamped results:

```bash
terra calculation create area --input width=known:width \
  --input height=assumption:working_height \
  --type number --quantity area --unit m2 --decimals 2
# edit .terra/map/calculations/area/calc.py
terra calculation validate area
terra calculation run area
terra calculation get area
```

For example, `(1 / 2) * mass * velocity**2` is valid. Terra assumes competent
formula authorship while keeping every external project value on the map.
`--decimals` controls only the separate display value; raw calculation values
remain full precision.

Input or source changes make the result stale. Assumptions propagate into the
result as explicit conditionality. See [docs/calculations.md](docs/calculations.md).

For multi-output scientific or engineering packages, use the model profile:

```bash
terra calculation create trajectory --profile model \
  --input mass=known:mass --input velocity=assumption:velocity \
  --output energy=number:kinetic_energy:J \
  --output moving=boolean:is_moving
```

Models support package-local and installed imports, typed output bundles,
an explicit `health.ok` verdict, diagnostics, hashed artifacts, and
runtime/dependency manifests. Failed health, changed/missing artifacts, or
runtime dependency drift make the result unusable and block the gate.

### Run (stamped evidence)

```bash
terra probe run mobs_in_region --to '{"kind":"region","x0":0,"z0":0,"x1":16,"z1":16}'
terra run list
# → .terra/map/runs/<run_id>/meta.json + artifacts/ (time, from, to, status, sha256)
```

Shared helpers: put modules in `.terra/map/lib/` (on `sys.path` during validate/run).

Probes that require map configuration declare it rather than copying values:

```bash
terra probe create calibrated_sensor --purpose "Read calibrated output" \
  --input scale=known:sensor_scale \
  --input ambient=assumption:ambient_temperature
# probe.py reads ctx["inputs"]
```

Runs stamp these inputs and become stale when they move. Assumptions contaminate
the run, resulting known, and downstream compositions. See
[docs/probe-inputs.md](docs/probe-inputs.md).

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
terra known show est          # n, mean, std + per-method stats
```

Types: `number`, `boolean`, `formula` (expr+vars), and `relation` — F(x)
curves measured by sweep runs, evaluated with `known get <id> --at <x>`
(linear interp, no extrapolation; ladder counts sweeps). See
[docs/relation-type.md](docs/relation-type.md).

Two evidence axes ([docs/corroboration.md](docs/corroboration.md)):
**repetition** (same probe, more runs → n-ladder) and **corroboration**
(different probes agreeing within `--within 5%`). `high` needs ≥2 agreeing
methods; disagreeing methods block promote/get/gate until resolved.

`terra known create` is retired; a known whose evidence is later voided away
shows up in `map status` attention as `known_unbacked`.

**Consume knowns, never copy them** — read path + deps + gate
(see [docs/known-graph.md](docs/known-graph.md)):

```bash
terra known get mtow --raw            # single home of the number (loud if stale)
terra known depend cg_pos --on file:airframe.stl --on known:mtow
terra known reaffirm cg_pos --reason "…"   # verified unchanged
terra gate                            # exit 1 on blocking unknowns / stale / unbacked
```

```python
from terra.readings import known      # in probes/tools
MTOW = known("mtow")["value"]
```

**Design layer** ([docs/design.md](docs/design.md)) — the validated baseline
deliverable files link to:

```bash
terra design add mtow                 # admit known (global, ≥med, agreeing, fresh)
terra design attach prints/three_view.pdf --uses mtow
terra design check --human            # red when knowns move / files drift
terra design get mtow --raw           # generators read THE design value
```

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

**Product path:** `probes/` + `unknowns/` + `knowns/` + `calculations/` +
`runs/` + `lib/` + `suites/`.

See [docs/probe-level1.md](docs/probe-level1.md), [docs/unknowns.md](docs/unknowns.md).
