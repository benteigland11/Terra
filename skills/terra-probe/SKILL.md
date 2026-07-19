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

### Engineering instruments (not only Minecraft fog)

An engineering tool needs a probe only when it interrogates an outside
authority: hardware, files, CAD/solver installations, services, or an
independently authoritative simulation. Deterministic manipulation of map
knowns/assumptions is a **calculation** (`terra-survey`), not a probe. Do not
wrap closed-form arithmetic in a fake instrument merely to stamp a run.

| Claim family | Typical probe | Measures (examples) |
| ------------ | ------------- | ------------------- |
| Aero / mission | `analyze_config` / `mission_perf` | `stall_kt`, `range_km`, `L_D` |
| Mass / CG | `mass_props` | `cg_pct_mac`, `mtow_kg` |
| Power / thermal | `power_thermal` | `power_margin`, `radiator_area_m2` |
| External cost source | `cost_source` | `unit_cost_usd`, `cost_per_pflop` |
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
9. Map values used by a probe are declared `known:` / `assumption:` inputs and
   read from `ctx["inputs"]`. The runner stamps them; moved inputs stale the
   evidence. Never hide a copied domain value in `probe.py`.

---


## Loop: make an instrument

1. **Scaffold**

```bash
terra probe create <slug> --purpose "…" --kind watch   # duration 0 = snapshot
# when the instrument needs map configuration:
terra probe create <slug> --purpose "…" \
  --input scale=known:sensor_scale \
  --input ambient=assumption:ambient_temperature
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
    inputs = ctx.get("inputs") or {}  # declared probe.json inputs only
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
  [--input NAME=known:ID|assumption:ID ...]
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

## Prove the input REACHES the output (perturb-and-check)

An error path for BAD input does not prove the probe reads GOOD input. A probe
that raises on a missing Mach and then solves with a **module-constant** Mach is
exactly as broken as one with no check at all — loud on garbage, silently deaf
to everything else. Both of these shipped here: a `ctx["to"]` Mach that never
reached the heat balance, and a solver-signature flag that proved a process RAN
while the reported number came from the stub it replaced.

"Prove it can fail" has three levels. Only the third is real:
1. **Does a check exist?** Weakest. A check that cannot fail is decoration.
2. **Does the check verify the proposition you NEED?** Provenance-of-EXECUTION
   ("the solver ran") is NOT provenance-of-VALUE ("this number came from it").
   Ask of every check: *what does this actually establish?*
3. **Does the input reach the output? PERTURB AND CHECK.** Move one input by a
   known amount, predict the output delta from first principles, confirm it
   lands (`hyd_aux 4kW→6kW` ⇒ `+71.43A @28V`, heat scaling as I² — all three
   matched). Sweep a condition and confirm the result moves as the physics says
   — monotonic, right power law. **If nothing moves, the input is decorative and
   every reading is a property of the code, not the world.**

Pair it with the negative test — bad/missing input ⇒ `status:"error"`, zero
measures, never a silently substituted default. **Both directions or neither.**

**Two scan rules for reading ANY check's output. Both are the same question:**
- **A completeness metric at 100% — ask what its DENOMINATOR excludes.** "31/31
  mating faces" was 100% of *documented* pairs, over a documented set touching
  30 of 54 parts. "Lumen area correct to <1%" — on a duct whose skin was never
  breached. "AC corroborated, comfortable margin" — with a −78% hole in the same
  dataset. Each ratio was true. Each denominator was chosen by someone else.
  The worst form is an **induction presented as an enumeration**: that pair list
  generalized "wing ribs mate to spars" from **one representative rib** and
  emitted the generalization as if it were the list. The remedy is mechanical —
  **a count that is a literal instead of a measurement is a lie waiting to
  happen.** Glob the population off disk, report `n_total` / `n_covered` /
  `n_uncovered`, and **fail below 100% coverage even when every checked item
  passes.**
- **A proof that CANNOT FAIL in the regime you care about is not evidence about
  that regime.** A 2-part assembly proof passing cleanly — real solver, hand-run
  agreement, can-fail demonstrated — says *nothing* about 30 parts when the
  suspected failure (many interfaces simultaneously active) is **structurally
  impossible to exhibit at 2**. That isn't weak evidence about scale; it is **no
  evidence**. Running it wasn't the error — reading it as reassurance was.

**Their shared spine, and the most useful question in this whole file:**
> **Ask what the check CANNOT see, not just what it reports.**

Every instrument that lied here was reporting truthfully: a search ceiling
reported as a flutter margin, a sweep parameter reported as a design property,
`n_degenerate_facets=0` from a threshold blind to the 32 real ones, a solver
signature proving a process ran while the number came from the stub it replaced.
**None of them were wrong. All of them answered a question nobody asked.**

## One quantity name = one condition (`number` knowns POOL; they ignore `x`)

A `number`-typed known **pools every sample under a quantity name as repeat
measurements of ONE thing — it does NOT read `x`.** `x` only means anything for
`--type relation`. So emitting the same quantity at two conditions in one run
silently **averages** them into a value describing no real condition — and it
graduates and sits in the map looking healthy. (Real case: a Mach-1.29
afterburning-dash airflow and a Mach-0.90 cruise airflow, same quantity name,
pooled into one meaningless mean.)

Two honest fixes — pick by **physics, not by looks**:
- **Put the condition in the quantity NAME** — `total_airflow_ab_dash_kg_s` vs
  `total_airflow_cruise_kg_s`. Correct whenever the conditions are distinct
  operating points rather than stations on one curve.
- **Use `--type relation`** ONLY if the conditions form a continuous schedule
  **your method actually covers**. A relation draws a curve, and a curve
  *asserts the regime between its stations*. If the method has no model there
  (e.g. a max-power-only corrected-flow schedule interrogated at part-power
  cruise), the curve is prettier and it lies. **Never reach for relation to
  smooth away a caveat.**

Carry validity WITH the reading: emit the caveat as a **measure/field**
(`method_valid_max_power: false`), never as prose in a comment someone will
lose. Same law as the condition basis below — a reading that can't state the
condition it was taken at is not a reading.

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
