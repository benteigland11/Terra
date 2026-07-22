---
name: terra-survey
description: >
  REQUIRED for Terra map beliefs and evidence: unknown create/link/resolve,
  assumption create/get/set/link/graduate (conditional consumable values),
  calculation create/validate/run/get (known+assumption composition),
  unknown graduate (known birth), known get/depend/tolerance/reaffirm/supersede/link/promote,
  corroboration (methods agree), cohorts (coupled knowns from one converged
  solve — create/check/link-run fan-out, mixed-set refusals),
  design add/attach/check (stable baseline), gate,
  plan create/link/promote, run void/list, typed
  number|boolean|formula, claim-shaped analysis without freehand, n-ladder /
  promote rules. Fire on fog, "open an unknown", encode a known, formula gate,
  multi-leg plan, void bad run, "looks good after one sample", or asserting
  mass/aero/power/thermal/cost without a linked run. Does NOT fire for probe.py
  implement (terra-probe), route DAG only (terra-route), brief edits
  (terra-brief), or global/session map switching alone (terra-scopes).
---

# terra-survey — beliefs and evidence

Store: `.terra/map/` (active map; pin with `terra --map <id>` — **terra-scopes**).  
Instruments: **terra-probe**. Program tasks: **terra-route**.

## Laws

1. Under fog: do not freehand the domain — open an **unknown**. Unknowns are
   hard gates. If progress genuinely requires a provisional typed value, make
   it an explicit **assumption** with a reason; never hide it in a probe.
2. Validate alone ≠ surveyed — **run + link** is the reading.  
3. n=1 cannot promote **high**. Formula confidence measures confidence in the
   verdict, independently of pass/fail; a confident failure is valid knowledge
   and `holds: false` blocks the gate.
4. Outside claims need unknown → **probe run** → known. Deterministic map-to-map
   models are calculations; do not manufacture probe evidence for arithmetic.
5. Bare `python tools/…` is not evidence — `terra probe run`.  
6. Resolve unknowns only with linked runs.
7. Knowns are born only via `unknown graduate` — no run, no known.  
8. Consume knowns, never copy them: `terra known get` / `readings.known()` —
   a number hardcoded in a tool/sheet is drift waiting to happen.  
9. Declare deps (`known depend --on known:x --on file:y`); stale knowns must be
   re-derived (link-run) or `reaffirm`ed with a reason — never consumed silently.
   A belief **nothing depends on is inert**. Tracking a constraint (flutter,
   clearance, margin) with no edge to what it endangers means a later refute
   cascades nowhere and the design never de-closes — coordination by attention,
   not by gate. `known tree <id>` printing `upstream/downstream: (none)` on a
   **safety- or constraint-shaped** known is a finding, not a detail: wire it to
   what it would knock over. A plain `depend` edge accepts a `low`/uncertain
   known (design params need ≥med) and still arms the cascade — that is the job.  
10. `terra gate` is the debt collector: active unknowns, stale/unbacked
   knowns, disagreeing methods, incomplete plans mechanically fail it
   (deliverable route tasks run it). Accepted spreads don't fail it but are
   surfaced as non-blocking `notices` — a release on an accepted band says so.
   Active assumptions are notices too: they permit progress but never become
   clean results by silence.
11. Two evidence axes: repetition (same probe, more runs) proves precision;
   **corroboration** (different probes agreeing `--within` tolerance) proves
   truth. `high` needs ≥2 agreeing methods; methods in disagreement collapse
   to low and block promote/get/gate — void the lying instrument's runs, OR
   if the spread is genuinely irreducible:
   `terra known accept-spread <id> --reason "…"` — reads unblock carrying
   `uncertainty`+`band`, confidence caps at med, widening spread re-trips,
   agreement clears. Related-but-distinct quantities are NOT a disagreement;
   med is their honest ceiling until a real second method exists.
   **Both methods must be measuring the SAME THING.** Same quantity name is not
   enough: two instruments running *different models*, or one running outside its
   valid regime, are not two methods — they are two answers to two questions, and
   their agreement and their disagreement are **equally meaningless**. Real cases:
   a corroborator still running the *rejected* model after its partner converted
   (they'd diverge for a reason unrelated to the axis under test); an unsteady
   method interrogated at a Mach its aero doesn't cover. **A corroborating
   instrument measuring something different from its partner is worse than no
   corroboration** — it manufactures a confidence interval out of a category
   error. Before linking a second method, state what proposition each one
   establishes and confirm it is the same proposition.
   **The inverse costs you too: DIFFERENT names for the SAME proposition
   silently forfeit corroboration you already earned.** Terra counts methods by
   **quantity name** — two independent instruments that physically agree to
   0.03 A but emit `dc_tru_continuous_margin_a` and `tru_continuous_margin_a`
   register as `methods=1`, and the known is capped at a confidence it has
   already outgrown. **Name the proposition, not the instrument.** Agree the
   quantity name across methods BEFORE running them, or you pay for a second
   method and don't get it.
   **And a SHARED IMPLEMENTATION is not independent corroboration.** If method B
   imports method A's function, their agreement is a **tautology** — guaranteed
   by construction, carrying zero information about the world. That is an
   integration sanity check, not a second opinion, and it is the purest form of
   this trap because the numbers match *perfectly*. Before crediting
   corroboration, ask **what could make these two disagree?** If the honest
   answer is "nothing, they run the same code," you have one method twice.  
12. Prefer `terra map status` over chat memory.
13. Calculations are inside the map. Every **external** input is a declared
   `known:` or `assumption:` binding; unknowns are rejected. Numeric/boolean
   literals are allowed as mathematical logic and stamped as an audit inventory
   (assume competence; do not mistake `1/2*m*v**2` for hidden data). Known-only
   results are clean. Assumptions propagate conditionality and their ids.
   Changed inputs or source make the result stale until rerun.
14. A probe may consume knowns/assumptions only as declared instrument inputs.
   Runs stamp those values. Moved inputs stale the evidence; assumptions make
   the run, known, and all downstream compositions conditional.

## Survey loop

```bash
terra map status
```

### 1. Open unknown

```bash
terra unknown create <slug> --type number --quantity <q> \
  --claim "…?" --evidence "…" [--within 5%]   # method-agreement tolerance

terra unknown create <slug> --type boolean --quantity <q> \
  --claim "…?" --evidence "…"

terra unknown create <slug> --type formula \
  --expression "mean(h) <= 10 and n(h) >= 3" --var h=<quantity> \
  --claim "…?" --evidence "…"

# bind a live requirement belief instead of duplicating a literal
terra unknown create closes_mtow --type formula \
  --expression "measured <= limit" \
  --var measured=mtow --var limit=known:spec_mtow \
  --claim "MTOW closes against the current requirement" --evidence "…"

terra unknown create <slug> --type relation --quantity <y> \
  --x-quantity <x> --claim "F(x)?" --evidence "…" [--within 10%]
# probes emit {"quantity","x","value"} pairs; one sweep run = many points

terra unknown create <slug> --claim "…" --evidence "…"   # untyped OK
```

If there is a defensible working value, model the different state explicitly:

```bash
terra assumption create <slug> --type number --quantity <q> --value 0.85 \
  --claim "…?" --reason "why this basis is acceptable for now" \
  --evidence "what replaces it with a known"
terra assumption get <slug>  # always conditional=true + assumptions=[<slug>]
terra assumption set <slug> --value 0.78 --reason "why the basis changed"
```

Evidence links do not overwrite the provisional value. Graduate only after a
live run exists; the resulting known is calculated from evidence, not the
assumed value:

```bash
terra assumption link-probe <slug> <probe_id>
terra assumption link-run <slug> <run_id>
terra assumption graduate <slug> [--as <known_slug>]
```

Formula `known:<id>` bindings read through the map parent chain and create
dependency edges; moving the bound known makes the formula stale until it is
honestly re-derived. Formula evidence runs also resolve child-first through
parent maps, so session formulas can evaluate already-global evidence without
copying its run.

### 2. Instrument → **terra-probe**, then

```bash
terra unknown link-probe <unknown_id> <probe_id>
terra probe run <probe_id> --to '{…}'    # prefer --json for run id
```

### 3. Link and resolve

```bash
terra unknown link-run <unknown_id> <run_id>
terra unknown show <unknown_id>
terra unknown status <id> resolved       # answered, no known needed (needs trail)
```

### 4. Encode known (product will build on it)

Knowns are **born only by graduating** an evidence-bearing unknown —
`terra known create` is retired; no run, no known:

```bash
terra unknown graduate <unknown_id> [--as <known_slug>]
# requires: unknown typed + ≥1 live linked run
# carries type/quantity/expression/runs over; resolves the unknown; known starts low/provisional

# Funnel: sibling unknowns asking the SAME question (type+quantity) → one known
terra unknown graduate mass_cad --with mass_sheet,mass_mockup --as mtow
# evidence unions (often multi-method at birth → corroboration); all resolve;
# origin_unknown_ids records every contributor; conflicting --within errors

# Late-arriving question → merge into the existing known (no competitor minted)
terra unknown graduate mass_fuel_check --into mtow

terra known link-run <slug> <run_id2>
terra known promote <slug> med           # blocks if ladder / !holds
```

### 4b. Consume + wire the graph

```bash
terra known get <slug> [--raw] [--min-conf med]   # THE number; loud if stale/unbacked
terra known depend <slug> --on known:<up> --on file:<relpath>
terra known graph --human                         # whole chain: which upstream moved
terra known tree <slug> --human                   # one node up/down + consumers
terra known reaffirm <slug> --reason "…"          # verified-unchanged only
terra known supersede <slug> --reason "…" [--by <replacement>] [--refuted]
terra gate                                        # exit 1 while debt remains
```

**Retire a wrong belief - don't delete it.** When a known is bug-derived or
just wrong, `known supersede` is the soft tombstone: keep it as history,
refuse it as current. `known set` can't touch a value; `known delete` is
destructive and leaves dangling consumers/design params. Supersede stamps a
reason (and optional `--by <replacement>`), sets status `superseded`
(replaced) or `refuted` (`--refuted`, just wrong), and the read path then
REFUSES `known get` unless `--allow-superseded` (which returns the historical
value, loudly flagged). Map status shows it as `known_retired` (info), not
debt.

```python
from terra.readings import known    # in probes/tools — never hardcode a copy
mtow = known("mtow")["value"]
```

### 4c. Compose map values with a calculation

```bash
terra calculation create area \
  --input width=known:width --input height=assumption:working_height \
  --type number --quantity area --unit m2 --decimals 2
# edit calc.py: calculate(inputs) -> {"value": ...}
terra calculation validate area
terra calculation run area
terra calculation get area       # refuses stale; carries conditional+assumptions
```

Formula coefficients and exponents may live in `calc.py`; validation inventories
them. Values obtained from the project or world still belong in a known or
assumption and must be bound explicitly.
`--decimals N` is presentation-only: raw `value` stays full precision and
`display` carries the rounded numeric/string rendering. Quantization that
changes the engineering value belongs explicitly in calculation logic.

Rigorous multi-output work stays under the same head with `--profile model`:

```bash
terra calculation create trajectory --profile model \
  --input mass=known:mass --input velocity=assumption:velocity \
  --output energy=number:kinetic_energy:J \
  --output moving=boolean:is_moving
# calculate(inputs, ctx) -> {outputs, health: {ok: bool}, diagnostics, artifacts}
terra calculation validate trajectory
terra calculation run trajectory
```

Every successful calculation stamps `evidence_run_id`. A matching typed
unknown can consume it without disguising the derivation as a probe:

```bash
terra unknown link-calculation <unknown> <calculation> [--output <model_output>]
terra unknown graduate <unknown>
```

The derived known carries calculation inputs, source hash, assumption
conditionality, and known dependency edges. Input/source changes stale the
evidence and block reads/gate until rerun + relink.

Model calculations may declare relation output as
`NAME=relation:Y_QUANTITY:X_QUANTITY[:Y_UNIT[:X_UNIT]]` and return
`{"points": [{"x": ..., "value": ...}]}`. Points must be finite and strictly
ordered by x; they feed matching relation unknowns through the same command.

Model packages may import installed/package-local modules. Terra stamps output
bundles, diagnostics, artifact hashes, Python/platform, requirements and
installed versions. The model must explicitly decide domain validity through
`health.ok`; false health is recorded but blocks composition and gate. Changed
helpers/requirements/inputs, runtime versions/platform, or artifact bytes stale
the result, and missing artifacts do too. Numeric outputs must be finite.

### 4d. Graduate into the design (stable baseline)

```bash
terra design add <known> [--as <param>]   # global map, ≥med, backed, agreeing, fresh
terra design attach <file> --uses <p1,p2> # stamp deliverable against params
terra design check                        # red: known moved / file drifted / missing
terra design refresh <param>              # re-pin after a reviewed move
terra design get <param> --raw            # generators read the design value
```

Design is project-wide, sourced from **global** only; params are live links
(known moves → param red → attached files flagged REGENERATE → gate fails).

**Gate self-check vs the baseline.** `design check` / `terra gate` also warn
(non-blocking `gate_stricter_than_baseline` notice) when a formula gate's
threshold is stricter than the accepted design-of-record: if a gate requires
`sm <= 0.01` but the admitted baseline for `sm` is `0.015`, the bar the
design of record itself fails is flagged - loosen the gate, or the DoR is out
of spec. Don't manufacture false walls against a bar your own baseline can't
pass.

### 5. Multi-leg → plan

```bash
terra plan create <id> --mode all|sequence --claim "…" \
  --leg name:boolean:qty:conf=med \
  --leg name2:number:qty:n=3
terra plan link-run <id> <run> --leg name
terra plan promote <id> med
```

### 6. Bad sample

```bash
terra run void <run_id> --reason "…"     # cascade unlink preferred
```

## Types

| Type | Meaning | Promote note |
| ---- | ------- | ------------ |
| number | quantity (n, mean, std) | med n≥3; high n≥5 + tight + 2 agreeing methods |
| boolean | yes/no rate | med n≥3; high n≥5 unanimous + 2 agreeing methods |
| formula | expr + vars → holds | med/high need holds + n |
| relation | F(x) curve, per-x stations | n = SWEEPS: med ≥3 sweeps + ≥3 stations; high +2 agreeing methods at shared stations. Read: `known get <id> --at <x>` (interp, no extrapolation) |

```text
probes → runs → knowns/unknowns (number | boolean | formula)
                         ↑ plans (all | sequence)
```

## CLI (beliefs)

```bash
terra unknown create | link-probe | link-run | graduate [--with|--into] | show | status | unlink-run | delete
terra known get | set (metadata: --claim/--notes/--unit; never values) | depend | graph | tree | tolerance | accept-spread | reaffirm | supersede (retire wrong belief) | link-run | promote | show | unlink-run | delete
terra cohort create | add | set | delete | list | check | link-run   # coupled sets, fan-out refresh
terra calculation create | validate | run | get | show | list | delete
terra design add | attach | check | refresh | get | remove | detach
terra gate       # mechanical debt check (all maps + design)
terra plan create | link-run --leg | promote | show
terra run list | show | void | delete
terra map status
```

## Done when

Unknown → run → link → known/plan as needed; no empty resolves; bad runs voided; status honest.

*Scopes: **terra-scopes**. Probes: **terra-probe**. Route complete evidence: **terra-route**.*

## Cohorts (coupled knowns from one solve)

Quantities that settle TOGETHER in one converged solve (sizing loop:
empty weight + wing area + power) are only mutually consistent within
one solve. Individually healthy knowns can jointly describe a design
that never existed. Declare the coupling:

```bash
terra unknown graduate we --cohort sizing_set        # join at birth
terra unknown graduate s_wing --cohort sizing_set    # (created on first)
# or later: terra cohort create sizing_set --members we,s_wing
terra cohort list / check sizing_set                 # computed, never stored
terra cohort set sizing_set --members we,s_wing,p_req --title "Sizing outputs"
terra cohort delete sizing_set                       # knowns/evidence survive
```

Laws:
- Members must carry **identical live run sets**. Mixed cohort →
  `cohort_inconsistent` attention, gate failure, and `known get` refuses
  on EVERY member (`--allow-cohort-mismatch` is the recorded escape).
- Refresh is ONE action, never per-known:
  `terra probe run <solver> --json && terra cohort link-run <id> <run_id>`
  — fans the solve out to all members; one multi-start re-solve advances
  n for the whole family.
- Per-known `link-run` on a member prints a NOTE for a reason: stop and
  use the cohort fan-out.
- A known has ONE coupling context (one cohort max).
- `cohort set --members` replaces the complete member list; `cohort delete`
  removes only the coupling declaration and preserves member knowns/evidence.
