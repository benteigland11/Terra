---
name: terra-survey
description: >
  REQUIRED for Terra map beliefs and evidence: unknown create/link/resolve,
  known create/link/promote, plan create/link/promote, run void/list, typed
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
7. Prefer `terra map status` over chat memory.

## Survey loop

```bash
terra map status
```

### 1. Open unknown

```bash
terra unknown create <slug> --type number --quantity <q> \
  --claim "…?" --evidence "…"

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
terra unknown status <id> resolved       # needs trail
```

### 4. Encode known (product will build on it)

```bash
terra known create <slug> --type number --claim "…" \
  --quantity <q> --from-run <run_id>

terra known create <slug> --type formula --claim "…" \
  --expression "…" --var x=<quantity> --from-run <run_id>

terra known link-run <slug> <run_id2>
terra known promote <slug> med           # blocks if ladder / !holds
```

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
| number | quantity (n, mean, std) | med n≥3; high n≥5 + tight |
| boolean | yes/no rate | med n≥3; high n≥5 unanimous |
| formula | expr + vars → holds | med/high need holds + n |

```text
probes → runs → knowns/unknowns (number | boolean | formula)
                         ↑ plans (all | sequence)
```

## CLI (beliefs)

```bash
terra unknown create | link-probe | link-run | show | status | unlink-run | delete
terra known create | link-run | promote | show | unlink-run | delete
terra plan create | link-run --leg | promote | show
terra run list | show | void | delete
terra map status
```

## Done when

Unknown → run → link → known/plan as needed; no empty resolves; bad runs voided; status honest.

*Scopes: **terra-scopes**. Probes: **terra-probe**. Route complete evidence: **terra-route**.*
