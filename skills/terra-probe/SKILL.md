---
name: terra-probe
description: >
  REQUIRED when building or fixing Terra map instruments (probes): writing or
  debugging probe.py, probe validate failures (INPUT/EXECUTE/OUTPUT), watch
  windows, dry_run / level1 validation, iterative solvers ("run until it
  settles" — convergence block, the solve is the sample, multi-start),
  suites (ordered probe recipes), measures
  for typed map nodes, to/status envelopes, map lib helpers. Fire on "probe
  won't validate", "implement the probe", suite create/run, watch duration,
  REQUIRED_EXPORTS, link-probe, OR when a claim-shaped route task has no probe
  yet (mass/CG, aero/mission, power/thermal, cost, payload fit, print regen
  checks) — build the instrument before asserting numbers in docs. Also fire
  when analysis only ran as a bare `python tools/…` without `terra probe run`.
  Does NOT fire for pure fog strategy, known promote, formula authoring
  (terra-survey), map scopes (terra-scopes), or route DAG alone (terra-route).
  After a successful probe run, hand off to terra-survey to link-run and encode
  beliefs; do not stop at validate or a one-off shell outside the probe.
---

# terra-probe — instruments that feed the map

Run from the **project under survey**. Probes live at  
`.terra/map/probes/<id>/` (**always global** — shared across session maps).  
(`terra` assumed if this skill is installed.)

## When to use this skill

| Situation | Skill |
| --------- | ----- |
| Implement / fix **`probe.py`** | **terra-probe** (this) |
| `terra probe validate` fails | **terra-probe** |
| Watch window, suite, measures shape | **terra-probe** |
| link-probe + then evidence | **terra-probe** then **terra-survey** |
| Open unknown / known / plan / void | **terra-survey** |
| global vs session | **terra-scopes** |
| route add/complete | **terra-route** |

**Start:** **terra-survey** opens the unknown and needs an instrument.  
**You:** create → implement → validate → run.  
**Handoff:** `run_id` → **terra-survey** link-run / known / plan; **terra-route** complete.

If using **`terra route`**: instrument work is a route task (`--skill terra-probe`) — **terra-route**.

Do **not** freehand domain behavior in product code while “just fixing the probe” — the probe is how you ask the world.

### Engineering packages (not only Minecraft fog)

Closed-form models (stall, radiator area, mass stations, ROM cost) **still need probes**.  
Pattern: enabler tool under `tools/` **and** a map probe that shells/imports it, emits **measures**, gets **`terra probe run`**, then **terra-survey** link-run / known / formula.

| Claim family | Typical probe | Measures (examples) |
| ------------ | ------------- | ------------------- |
| Aero / mission | `analyze_config` / `mission_perf` | `stall_kt`, `range_km`, `L_D` |
| Mass / CG | `mass_props` | `cg_pct_mac`, `mtow_kg` |
| Power / thermal | `power_thermal` | `power_margin`, `radiator_area_m2` |
| Cost | `cost_model` | `unit_cost_usd`, `cost_per_pflop` |
| Fit / envelope | `payload_fit` | `fits_fairing`, `mass_margin_frac` |
| Regen contract | `print_regen` / `cad_build` | boolean ok + artifact paths |

**One probe for the whole program is not enough** when multiple claim families exist.

---

## Laws (instrument side)

1. Probes are **open** (any code that can sense/drive this install).  
2. **Validate** = design bar (dry). **Run** = evidence (stamped). Both required before map trusts it.  
3. Typed map nodes need **`measures`** with stable **quantity** names.  
4. Honor **`dry_run`** / `_terra_validation=level1` (no live wait, no long polls).  
5. Prefer recommended **`to`** / **`status`** envelopes (`--strict-to` / `--strict-status` in CI).  
6. Probes stay **global**; which **map** records the run is active / `--map` (**terra-scopes**).  
7. Bare `python tools/foo.py` is **not** a map reading — use **`terra probe run`**.  
8. Hand off **`run_id`** (from `--json`) to **terra-survey**; never “it printed OK.”

---


## Loop: make an instrument

1. **Scaffold**

```bash
terra probe create <slug> --purpose "…" --kind watch   # duration 0 = snapshot
# --kind run to drive/simulate
# --duration N for watch window (seconds)
```

2. **Attach to research ticket** (belief side still owns the unknown):

```bash
terra unknown link-probe <unknown_id> <probe_id>
# or: terra unknown create … --probe <probe_id>
```

3. **Implement** `.terra/map/probes/<id>/probe.py`

```python
KIND = "watch"          # or "run"
DURATION_S = 0          # 0 = snapshot; >0 watch window when live
REQUIRED_EXPORTS = ["to", "status", "artifacts"]

def run(ctx=None):
    ctx = ctx or {}
    to = ctx.get("to") or {"kind": "default"}
    if ctx.get("dry_run") or ctx.get("_terra_validation") == "level1":
        return {"to": to, "status": "ok", "artifacts": []}
    # live work for THIS install only
    # watch: if ctx.get("watch_mode") == "window": poll until ctx["deadline_unix"]
    return {
        "to": to,
        "status": "ok",  # ok|degraded|unavailable|empty|error
        "artifacts": [{"path": str(path), "role": "out"}],
        "measures": [
            {"quantity": "hostile_count", "value": 3},   # number
            # {"quantity": "rcon_up", "value": True},    # boolean
        ],
    }
```

Shared helpers: put modules in `.terra/map/lib/` (on `sys.path` during validate/run).

4. **Validate** (must pass INPUT / EXECUTE / OUTPUT):

```bash
terra probe validate <probe_id>
```

5. **Run** (stamp evidence — pick active map if experiment; **terra-scopes**):

```bash
terra probe run <probe_id> --to '{"kind":"region","id":"R"}'
# optional: --strict-to --strict-status --json
```

6. **Hand off to terra-survey**

```text
run_id = …
→ terra unknown link-run <u> <run_id>
→ or terra known link-run / plan link-run --leg …
→ terra map status
```

---

## Suites (multi-probe same `to`)

```bash
terra suite create <id> --probes a,b,c
terra suite validate <id>
terra suite run <id> --to '{"kind":"town"}'
```

Each leaf run still links on the map (**terra-survey**). Suite is recipe/ops, not a domain plugin.

---

## Envelopes

**`to`:**

```json
{ "kind": "region|entity|path|server|literal|default", "id": "…", "limit": 50 }
```

**`status`:** `ok` | `degraded` | `unavailable` | `empty` | `error`

---

## CLI (instruments)

```bash
terra probe create <id> --purpose "…" --kind watch|run [--duration N]
terra probe validate <id>
terra probe run <id> --to '{…}' [--strict-to] [--strict-status]
terra probe list

terra suite create <id> --probes a,b,c
terra suite validate | run

terra unknown link-probe <u> <probe>
```

Beliefs → **terra-survey**. Scopes → **terra-scopes**. Route → **terra-route**.

---

## What not to do

- Do **not** skip validate and claim the instrument works  
- Do **not** live-block under dry_run / level1 validation  
- Do **not** omit **measures** when the unknown/known is typed  
- Do **not** invent domain APIs from training data — sense **this** install  
- Do **not** promote knowns or manage scopes here  
- Do **not** put product domain funnels into Terra core  
- Do **not** leave analysis only as ad-hoc shell scripts with no probe  
- Do **not** stop after one probe if the program has other claim families  

---

## Completion criterion (instrument)

1. Probe package exists under `.terra/map/probes/<id>/`,  
2. **`terra probe validate`** passes,  
3. ≥1 **live** `terra probe run` stamped (unless only scaffolding),  
4. Linked via **link-probe** when a research ticket exists,  
5. **`run_id` returned to terra-survey** (and **terra-route** evidence),  
6. Eng packages: probe covers the current claim family.

Stopping at scaffold, validate-only, or “ran the tool outside Terra” = incomplete.
## Sweep probes (relation knowns)

For `--type relation` knowns, emit (x, y) pairs as measures with an `x`
field — `{'quantity': 'cl', 'x': 4.0, 'value': 0.62}` — many per run (one
run = one sweep). Keep a **shared x grid** across sweeps and across methods:
stations match on exact x, and corroboration only judges shared stations.
Repeat the sweep for the ladder (n = sweeps, not points).

**State the condition basis of every station** — in the probe docstring AND the
known's claim. A sweep over one variable silently PINS the others, and the
pinned value is where curves lie while every number in them is "correct":
`margin vs mach` evaluated at sea-level density is *this Mach flown down low* —
a dynamic-pressure corner the vehicle may never reach — so it reads as failure
at a cruise point that is genuinely fine. If `x` is a **proxy** (Mach) for what
actually drives the physics (EAS / dynamic pressure / altitude), say so at every
station. Ask before emitting: *"is each station a condition the system can
really be in?"* Unreachable stations belong labelled as bounding corners, not
mixed into a curve someone will read as the flight envelope — and never let the
sweep contradict the single-point gate without explaining which one governs.

## Probes are methods (corroboration)

A second *independent* probe for the same quantity is how a known reaches
`high` — repetition of one instrument proves precision, not truth. Build the
second method differently (e.g. CAD mass-properties vs spreadsheet buildup),
emit the **same quantity name**, and link runs to the same known. Terra
groups stats per probe and judges agreement against the known's
`--within` tolerance (**terra-survey**).

## Iterative solvers (convergence)

When the only solver is "run until the system settles" (sizing loops,
fixed-point iteration, relaxation), **the solve is the sample** — the loop
runs INSIDE the probe and only the settled value leaves it:

```python
return {
    'to': to, 'status': 'ok',
    'artifacts': [...],                    # residual history goes here
    'measures': [{'quantity': 'we', 'value': we},      # all coupled
                 {'quantity': 's_wing', 'value': s}],  # outputs, one run
    'convergence': {'converged': True, 'iterations': k,
                    'residual': r, 'tol': tol,
                    'criterion': 'max|dx|/x < tol'},
}
```

Laws:
- Iterates NEVER stamp runs. One run-to-settle = n=1.
- `converged: false` runs stamp but are **unlinkable** as evidence — an
  unsettled iterate is not a value. Fix the solve, re-run.
- Independent evidence = **multi-start**: re-solve from a different initial
  guess/damping (different `--to`). Same-start re-solves don't add n (the
  CLI NOTEs when you try). Different starts agreeing = real corroboration
  AND catches multiple basins of attraction.
- Coupled outputs (valid only as a set) → cohort (**terra-survey**).
