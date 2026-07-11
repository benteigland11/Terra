---
name: terra-map
description: >
  REQUIRED for Terra map middleware and opaque domains: modded Minecraft, game
  engines, hardware, weird runtimes, "how does this world work", thrashing APIs,
  freehand from training data, or any work that needs survey before code.
  Covers unknowns, knowns (typed: number = n/mean/std, boolean = rate),
  probes, stamped runs, suites, link-run, promote ladder (n=1 cannot be high).
  Prefer this loop over silent guessing. Does NOT replace Cartograph widgets
  (bricks) — Terra is the map (understand). Fire on Terra CLI, fog, probes,
  knowns/unknowns, Minecraft/mod dev, or "looks good" after one sample.
---

# terra-map — map middleware above Cartograph

| Soft (forgets) | Hard (compounds) |
| -------------- | ---------------- |
| "Looks good" after one sample | **known** with sample ladder (n=1 → low only) |
| Chat dump of a command | Stamped **run** + **link-run** |
| Freehand domain from pretraining | **unknown** → **probe** → **run** → evidence |

**Laws**

1. Under fog: do **not** freehand the domain.  
2. **Probes are open** (infinite instruments). **Knowns/unknowns are typed** (finite).  
3. Types: **`number`** (mean±std), **`boolean`** (rate from true/false trials).  
4. Validate alone ≠ surveyed. **Run + link** is the reading.  
5. Resolve unknown ≠ encode high known. n=1 cannot `promote high`.

CLI: `pip install -e ~/Cartograph/Terra` → `terra`.  
Store (in the project under survey): `.terra/map/`.

Docs: `docs/number-type.md`, `docs/boolean-type.md`, `docs/watch-duration.md`,
`docs/to-schema.md`, `docs/status-vocab.md`, `docs/unknowns.md`, `docs/suites.md`.

---

## The full loop (do these — do not only suggest)

### Fog / stuck / opaque API

1. **STOP** freehand domain logic after one failed guess or clear uncertainty.

2. **Open an unknown** (non-negotiable if still stuck):

```bash
# Prefer typed when the answer is a measurable quantity:
terra unknown create <slug> \
  --type number --quantity hostile_count \
  --claim "How many hostiles in region R at night?" \
  --evidence "repeated probe measures of hostile_count"

# Untyped ticket still OK for mechanism fog:
terra unknown create <slug> \
  --claim "What we do not know" \
  --evidence "What reading would resolve this"
```

Default `blocks_build=true`. Stuck with no open unknown = process failure.

3. **Create a probe**:

```bash
terra probe create <slug> --purpose "…" --kind watch   # duration 0 = snapshot
# --kind run to drive/simulate; --duration N for watch window
```

4. **Link instrument** → status `probing`:

```bash
terra unknown link-probe <unknown_id> <probe_id>
# or: unknown create … --probe <probe_id>
```

5. **Implement `probe.py`** for *this* install:

```python
return {
    "to": to,                    # non-empty target
    "status": "ok",              # prefer: ok|degraded|unavailable|empty|error
    "artifacts": [{"path": str(p), "role": "out"}],
    "measures": [                # REQUIRED for typed map nodes
        {"quantity": "hostile_count", "value": 3},      # number
        # {"quantity": "rcon_up", "value": True},       # boolean
    ],
}
```

Honor `dry_run` / `_terra_validation=level1` (no live wait).  
Watch window: if `ctx["watch_mode"]=="window"`, poll until `ctx["deadline_unix"]`.  
Helpers: `.terra/map/lib/` on sys.path during validate/run.

6. **Validate instrument** (design bar only):

```bash
terra probe validate <probe_id>   # INPUT / EXECUTE / OUTPUT must pass
```

7. **Run and stamp** (evidence):

```bash
terra probe run <probe_id> --to '{"kind":"region","id":"R"}'
# multi-probe: terra suite create … --probes a,b,c && terra suite run … --to '…'
```

8. **Link the run** (structured evidence):

```bash
terra unknown link-run <unknown_id> <run_id>
terra unknown show <unknown_id>   # n/mean/std if type=number
```

9. **Close unknown** when the research ticket is done:

```bash
terra unknown status <id> resolved    # if run_ids linked
# or --resolved-by "…"
```

10. **Encode a known** when you will **build product on the claim** (typed belief):

```bash
terra known create <slug> \
  --claim "Night hostile count in R is about the sample mean" \
  --quantity hostile_count \
  --from-run <run_id>
terra known link-run <slug> <run_id2>    # second sample before med/high
terra known promote <slug> med           # BLOCKS if ladder fails
terra known show <slug>                  # n, mean, std
```

**Never** set confidence high on n=1. **Never** treat provisional low known as law for big features.

---

## Typed knowns/unknowns (number + boolean)

| | **number** | **boolean** |
| - | ---------- | ----------- |
| measures value | float | true/false (or 0/1) |
| stats | n, mean, std | n, k_true, k_false, **rate** |
| med | n≥3 or (n≥2 + std) | n≥3 |
| high | n≥5 + tight std/mean | n≥5 + unanimous rate 0 or 1 |

`terra known promote <id> high` **blocks** until the ladder allows it.

---

## Recommended envelopes (composition, not domain funnels)

**`to`** (warn if `kind` missing on live run; `--strict-to` fails CI):

```json
{ "kind": "region|entity|path|server|literal|default", "id": "…", "limit": 50 }
```

**`status`** (warn if freeform; `--strict-status` fails CI):  
`ok` | `degraded` | `unavailable` | `empty` | `error`

---

## Minecraft / mod dogfood

| Situation | Action |
| --------- | ------ |
| Count / rate / size question | `--type number --quantity …` + measures on probe |
| "How many hostiles in R" | unknown number → probe → run → link-run → known only after samples |
| One green run | known **low** / provisional only — **second sample** before med |
| "API like Forge X" | probe + run this loader — no pretraining |
| 3+ probes same `to` | `terra suite create/run` |

---

## CLI cheat sheet

```bash
terra unknown create <id> --claim "…" --evidence "…" [--type number --quantity q]
terra unknown link-probe <u> <probe>
terra unknown link-run <u> <run_id>
terra unknown show <u>
terra unknown status <u> resolved

terra known create <id> --claim "…" --quantity q [--from-run <run>]
terra known link-run <id> <run_id>
terra known promote <id> low|med|high
terra known show <id>
terra known validate

terra probe create <id> --purpose "…" --kind watch|run
terra probe validate <id>
terra probe run <id> --to '{…}' [--strict-to] [--strict-status]

terra suite create <id> --probes a,b,c
terra suite validate <id>
terra suite run <id> --to '{…}'

terra run list [--status unavailable] [--probe p]
```

Product path: **probes + unknowns + knowns + runs + lib + suites**.  
Ignore legacy `.terra/map/data/`.

---

## What not to do

- Do **not** invent domain behavior from memory when a probe can ask the world  
- Do **not** thrash without an **unknown**  
- Do **not** stop after **validate** — **run + link** is the reading  
- Do **not** resolve with empty trail  
- Do **not** `promote high` (or treat as law) on **n=1**  
- Do **not** put domain funnels in Terra core  
- Do **not** confuse Terra (map) with Cartograph (bricks)  

---

## Completion criterion

For each durable foggy gap:

1. **unknown** exists (typed `number` when the answer is a quantity),  
2. **probe** validates,  
3. ≥1 **stamped run** with **measures** if number-typed, **link-run**’d,  
4. if building on the claim → **known** at **earned** confidence (second sample before med),  
5. unknown **resolved** with trail when research ticket is done.

Stopping at validate or one green run = incomplete.
