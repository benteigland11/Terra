---
name: terra-survey
description: >
  REQUIRED for Terra map beliefs and evidence: unknown create/link/resolve,
  unknown graduate (known birth), known get/depend/tolerance/reaffirm/link/promote,
  corroboration (methods agree), design add/attach/check (stable baseline), gate,
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

1. Under fog: do not freehand the domain — open an **unknown**.  
2. Validate alone ≠ surveyed — **run + link** is the reading.  
3. n=1 cannot promote **high**; failed formula cannot promote as true.  
4. Claim-shaped work (even closed-form models you wrote): unknown/known + **probe run** + link.  
5. Bare `python tools/…` is not evidence — `terra probe run`.  
6. Resolve unknowns only with linked runs.
7. Knowns are born only via `unknown graduate` — no run, no known.  
8. Consume knowns, never copy them: `terra known get` / `readings.known()` —
   a number hardcoded in a tool/sheet is drift waiting to happen.  
9. Declare deps (`known depend --on known:x --on file:y`); stale knowns must be
   re-derived (link-run) or `reaffirm`ed with a reason — never consumed silently.  
10. `terra gate` is the debt collector: blocking unknowns, stale/unbacked
   knowns, disagreeing methods, incomplete plans mechanically fail it
   (deliverable route tasks run it).  
11. Two evidence axes: repetition (same probe, more runs) proves precision;
   **corroboration** (different probes agreeing `--within` tolerance) proves
   truth. `high` needs ≥2 agreeing methods; methods in disagreement collapse
   to low and block promote/get/gate — void the lying instrument's runs, OR
   if the spread is genuinely irreducible:
   `terra known accept-spread <id> --reason "…"` — reads unblock carrying
   `uncertainty`+`band`, confidence caps at med, widening spread re-trips,
   agreement clears. Related-but-distinct quantities are NOT a disagreement;
   med is their honest ceiling until a real second method exists.  
12. Prefer `terra map status` over chat memory.

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

terra unknown create <slug> --claim "…" --evidence "…"   # untyped OK
```

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
terra gate                                        # exit 1 while debt remains
```

```python
from terra.readings import known    # in probes/tools — never hardcode a copy
mtow = known("mtow")["value"]
```

### 4c. Graduate into the design (stable baseline)

```bash
terra design add <known> [--as <param>]   # global map, ≥med, backed, agreeing, fresh
terra design attach <file> --uses <p1,p2> # stamp deliverable against params
terra design check                        # red: known moved / file drifted / missing
terra design refresh <param>              # re-pin after a reviewed move
terra design get <param> --raw            # generators read the design value
```

Design is project-wide, sourced from **global** only; params are live links
(known moves → param red → attached files flagged REGENERATE → gate fails).

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

```text
probes → runs → knowns/unknowns (number | boolean | formula)
                         ↑ plans (all | sequence)
```

## CLI (beliefs)

```bash
terra unknown create | link-probe | link-run | graduate [--with|--into] | show | status | unlink-run | delete
terra known get | depend | graph | tree | tolerance | accept-spread | reaffirm | link-run | promote | show | unlink-run | delete
terra design add | attach | check | refresh | get | remove | detach
terra gate       # mechanical debt check (all maps + design)
terra plan create | link-run --leg | promote | show
terra run list | show | void | delete
terra map status
```

## Done when

Unknown → run → link → known/plan as needed; no empty resolves; bad runs voided; status honest.

*Scopes: **terra-scopes**. Probes: **terra-probe**. Route complete evidence: **terra-route**.*
