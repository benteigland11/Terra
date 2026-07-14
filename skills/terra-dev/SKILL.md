---
name: terra-dev
description: >
  REQUIRED when developing the Terra codebase itself (Cartograph/Terra): src/terra,
  tests, CLI DX, map status envelopes, formula/plan/scopes, skills under
  skills/terra-*, AGENTS.md, or agent-facing output. Fire on "fix terra CLI",
  "DX pass", "gotcha", pytest for Terra, ship terra-map/terra-probe skill, or
  change probe/known/plan/map substrate. Does NOT replace terra-map/terra-probe
  for surveying a foreign product project — this skill is maintainer-only.
---

# terra-dev — maintain Terra (not survey a product)

**cwd:** `Cartograph/Terra` (or this repo root).  
**User skills (one job each):**  
`terra-start` · `terra-brief` · `terra-route` · `terra-survey` · `terra-scopes` · `terra-probe` · `terra-map` (thin index).  
Project kickoffs stay aiming vectors only.  
**This skill:** substrate, CLI agent-DX, tests, skill sync.

## When to use

| Situation | Skill |
| --------- | ----- |
| Working **in** Terra repo (`src/terra`, `tests/`, `skills/`) | **terra-dev** (this) |
| Product program with Terra | focused user skills / **terra-map** index |
| Reusable envelope/CLI atom | Cartograph **cg-plan** → `bp-agent-tool-cli` etc. |

---

## Always-check checklist (before claiming green)

Run from Terra repo unless noted.

### A. Automated bar

```bash
cd /path/to/Cartograph/Terra
PYTHONPATH=".:src" python -m pytest -q
# if you touched cg/bp_*:
cartograph validate cg/bp_agent_tool_cli_python
```

### B. Agent DX smoke (temp project)

Agents hit these paths every session — re-run after CLI/status changes:

```bash
DX=$(mktemp -d) && cd "$DX"
terra init
terra map status                    # must be agent envelope {status,data}
terra map status --human            # secondary
terra map create exp --use
terra unknown create u --type number --quantity q --claim "c?" --evidence "e"
terra probe create p --purpose "p" --kind watch
# implement measures; validate; run --json; link-run; unknown graduate → known
# known get/depend/reaffirm; design add/attach/check; terra gate; void
terra map status --all              # MUST see session attention when active=global

# budget / plan lock (if you touched brief.py / route.py)
terra brief init --title dx --mission m
terra brief set --budget-points 32
terra route init
terra route add a --title A --bucket low
terra route add b --title B --bucket medium
terra route add c --title C --bucket high
terra route budget                  # plan == actual ≤ budget
terra route lock-plan
# set-effort while locked may over-budget; unlock needs --confirm
terra route unlock-plan 2>/dev/null || true   # expect WARNING error
terra route unlock-plan --confirm
```

### C. Skill sync

After editing user skills:

```bash
USER_SKILLS="terra-start terra-brief terra-route terra-survey terra-scopes terra-map terra-probe"
for s in $USER_SKILLS terra-dev; do
  mkdir -p ~/.grok/skills/$s ~/.claude/skills/$s ~/.codex/skills/$s
  cp skills/$s/SKILL.md ~/.grok/skills/$s/SKILL.md
  cp skills/$s/SKILL.md ~/.claude/skills/$s/SKILL.md
  cp skills/$s/SKILL.md ~/.codex/skills/$s/SKILL.md
done
# product projects (skip terra-dev):
# for s in $USER_SKILLS; do
#   for d in .claude/skills .codex/skills .grok/skills; do
#     mkdir -p $PROJ/$d/$s && cp skills/$s/SKILL.md $PROJ/$d/$s/SKILL.md
#   done
# done
```

### D. Agent output contract

- Prefer **JSON-first** for agent surfaces (`map status` default).  
- Envelope via **`bp-agent-tool-cli`** / `terra.agent_io` — no parallel `terra.agent/v1`.  
- `probe run --json` / `run list --json` for parseable ids (do not scrape prose).

---

## Gotchas (from DX stress — always re-verify)

### 1. Active map vs full detail (fixed for attention)

`terra map status` **without** `--all` still shows **detail scopes** for the
active map only, but **`attention` / `next_actions` always scan every map**.
Session work cannot hide behind a quiet global.

- `maps_with_attention` lists maps that need work  
- `other_map_work` attention + `map.use` next_actions when active ≠ that map  
- argv pins `--map <id>` when not active  

`--all` still needed for **full per-map counts/tables**, not for honesty of attention.

### 2. Unknowns/knowns are map-scoped

```bash
terra map use global
terra unknown show hostiles   # → not found (lives on session)
terra --map night_trial unknown show hostiles
```

Probes are **global**; runs land on **active** map. Wrong active map = silent wrong store.

### 3. Scaffold probes validate PASS (now self-announcing)

Bare `terra probe create` scaffolds a dry-friendly stub that **level-1 validates**.  
Agents must not treat validate PASS as "surveyed" — still need live `probe run` + measures + link.  
`probe validate <id>` now prints agent NOTEs: scaffold-stub detection
("TODO: implement"/"scaffold stub" markers), no-measures detection, and the
standing "validate PASS ≠ surveyed" reminder.

**Agent-notes pattern** (house style): at likely-mistake moments, do not
block and do not stay silent — print a `NOTE:` with the copy-pasteable
correction (real ids, real run ids). Current sites: link-run on resolved
unknown, probe validate (stub/no-measures/not-surveyed), probe run (link-run
next hints, no-measures), map create --use / map use session (wrong-map),
run void (--no-cascade leftovers, cascade→unbacked), known unlink-run →
unbacked, prose resolve on graduatable unknown, route start (parallel
in_progress, via envelope meta.note), known delete (design params +
consumers), design refresh (attached artifacts → REGENERATE).
Tests: `tests/test_agent_notes.py`. When adding a surface, add a note test.

### 4. Run id is not in human status line alone

Parse:

```bash
terra probe run <id> --to '…' --json    # stamp has "id"
# or
terra run list --json                   # [{id, record, …}]
```

Human `run 2026…_mobs_…` line is easy for humans, brittle for agents.

### 5. Formula needs vars + expression

`--type formula` without `--var` fails hard (good).  
Promote med/high blocked when `n` ladder fails even if `holds=true` (good).  
Document both in user skills; keep tests in `tests/test_formula_type.py`.

### 6. Sequence plans block ahead of order

`plan link-run --leg later` fails until prior leg satisfied — intentional.  
Status `next_leg` must stay accurate.

### 7. Void target ≠ automatic "bad for sparse"

`run void` only cascade-unlinks records that **reference** that run.  
Voiding an unrelated rcon run does not touch a hostiles formula known.  
Agents must void the run id that polluted the known.

### 8. Quiet next_actions is a footgun

When attention is empty, next_actions may only re-invoke `map.status`.  
Prefer detecting `--all` or multi-map inventory before concluding "done."

### 9. Help text lag

Top-level `terra known` help may still say "number only" while formula/plan exist.  
After CLI help changes, re-read `--help` in DX smoke.

### 10. PYTHONPATH vs installed entrypoint

Dev: `PYTHONPATH=src` or `pip install -e .`.  
DX smoke should use the same `terra` users get (`~/.local/bin/terra` or venv).

### 11. Knowns are born only via `unknown graduate`

`terra known create` is retired (stub errors with the survey path); the
substrate (`create_known`, `set_known`) also refuses birth without a run.
Graduation needs a **typed** unknown + ≥1 live linked run; it resolves the
unknown (`resolved_by=known:<id>`) and stamps `origin_unknown_id`. Evidence
voided away later → `known_unbacked` attention in map status.
Funnel: `graduate --with u2,u3` merges same-type+quantity siblings at birth
(evidence unions, all resolve, origin_unknown_ids, conflicting tolerances
error); `--into <known>` merges into an existing known (type/quantity
checked; --as/--into exclusive). Tests: `tests/test_graduate.py`,
`tests/test_graduate_merge.py`.

### 12. Known graph: read path, staleness, gate

`terra known get` / `terra.readings.known()` is the consumption path — loud on
missing/unbacked/stale/low-conf; stamps consumer edges under
`.terra/map/<scope>/consumers/`. Deps (`known depend --on known:x|file:y`)
drive **computed** staleness (never stored): sha256 for files, `as_of` vs
upstream `updated_at` for knowns, cascade + cycles stale. Stamps refresh only
on link-run / reaffirm / depend. `terra gate` exits 1 on blocking unknowns,
stale/unbacked knowns, incomplete plans across ALL maps; `route complete` on
deliverable tasks runs it (`--skip-gate "<reason>"` is recorded).
`run_probe` sets consumer `probe:<id>` via `readings.consumer_scope`.
`terra known graph|tree` renders the chain (shared subtrees collapse with …,
cycles with ↺) — pure view over deps+staleness+consumers, no new state.
Tests: `tests/test_readings_staleness_gate.py`, `tests/test_known_graph.py`.

### 13. Corroboration: two evidence axes

`stats.by_probe` (samples grouped by run probe_id) + `stats.corroboration`
({methods, tolerance, spread, agree}) computed in `recompute_typed_node`,
judged by `corroboration.py` against `record.tolerance` ("5%" rel | abs).
Hard opinions: high needs ≥2 agreeing methods (single method caps at med;
`derive_confidence_*` + `can_claim_confidence` enforce); `agree is False`
collapses derived to low and blocks promote/get/gate (`--allow-disagree`
escape on get). Tolerance: `--within` at unknown create (carried through
graduate) or `terra known tolerance <id> --within X`. Formula type exempt.
Accept-spread: `known accept-spread --reason` stamps `accepted_spread`
{spread, band}; `reconcile_accepted_spread` (corroboration.py) re-judges on
every recompute — within stamp → corr.accepted=True (reads unblock with
uncertainty+band, derived caps med, gate/attention downgrade); spread grew →
accepted=False, full alarm; agree=True → stamp dropped. `methods_disagree()`
= unaccepted disagreement only.
Tests: `tests/test_corroboration.py`, `tests/test_accept_spread.py`.

### 14. Route hardening: evidence refs, cycles, aging

`complete_task` validates `--run`/`--known` refs across ALL maps
(`validate_evidence_refs`: run exists + not voided; known backed + methods
not disagreeing). SURVEY_SKILLS = {terra-map, terra-probe} (or role=survey)
refuse prose-only complete — `--freehand '<reason>'` is the recorded escape.
`validate_route` rejects dep cycles (load + save, so hand-edited files too).
`route_status().attention`: task_blocked, task_stalled (in_progress ≥7d,
STALL_DAYS). Tests: `tests/test_route_evidence.py`.

### 15. Relation type: F(x) knowns

`relation_type.py`: pairs from measures rows with `x`; stats per x-station
(exact match — shared grid is the contract); `n` = sweeps (runs with pairs),
not points. med ≥3 sweeps + ≥3 stations; high adds tight stations +
corroboration at ≥2 SHARED stations (disjoint grids → agree=None).
`evaluate_relation` = linear interp between station means, loud outside
x_range. read_known(at=...) / `known get --at` / records need
quantity + x_quantity. Tests: `tests/test_relation_type.py`.

### 16. Probe loader bypasses the pyc cache

`load_probe_module` compiles probe.py straight from source (no importlib
SourceFileLoader): pyc validation is mtime+size, so a probe edited twice in
the same second with equal file size silently ran STALE bytecode (surfaced
by accept-spread tests). Never reintroduce spec_from_file_location there.

### 17. Design layer: baseline + artifacts

`src/terra/design.py`, store `.terra/design.json` (project-wide, like
brief/route; params sourced from GLOBAL map only via scoped_map). Admission
bar in `_known_admission_problems` (≥med, backed, agree≠False, not stale).
Params pin known_updated_at; moved known → red + `design refresh` re-pins.
Artifacts stamp file sha256 + params_at; drift/regen detection in
`check_design` (computed, never stored). Gate appends design violations with
map_id="design". `design get` wraps read_known(min_conf=med) on global.
Tests: `tests/test_design.py`.

### 18. Budget vs plan vs actual vs sectors

- `brief.budget_points` = authorized total (terra-brief).  
- `route.sectors[]` = reserved provisions (`reserved_points`).  
- `task.plan_*` = locked baseline; `task.bucket/points` = working; `task.sector_id` optional.  
- Initial allocation: sector plan ≤ reserve; unsectored ≤ free pool; total ≤ budget.  
- Locked: add only with `--sector`; `set-effort` may over-budget.  
- `unlock-plan` without `--confirm` must fail with WARNING text.  
- Tests: `tests/test_brief_route.py`.

---

## Layout (mental model)

```text
.terra/brief.json   SSOT (needs, deliverables, enablers, **budget_points**)
.terra/route.json   task DAG + **plan_locked** + plan_*/working points
.terra/map/         survey / evidence

# Enablers = internal means of production (print harness, CAD bridge)
# Deliverables = customer pack (prints/, mission card)
# Enablers may graduate → Cartograph widgets when stable

src/terra/          substrate + CLI (brief.py, route.py, map_*)
tests/              pytest (required green)
skills/
  terra-start/      init project
  terra-brief/      design request + enablers
  terra-route/      task DAG + lead loop
  terra-survey/     unknown/known/plan/void
  terra-scopes/     global vs session
  terra-map/        thin index / router
  terra-probe/      instruments
  terra-dev/        maintainer: this file
docs/brief-route.md program layer
cg/                 Cartograph leaves + bp-agent-tool-cli
AGENTS.md           scars + validate-and-ship
```

Terra accumulates **scars** (DX gotchas, brief fields, route skill tags).  
Cartograph accumulates **careful bricks**. Don't pretent they're the same.

---

## Product change playbook

1. **Classify:** Terra glue vs Cartograph leaf/blueprint (`cg-plan` if reusable).  
2. **Implement** + pytest.  
3. **DX smoke** (section B) on a temp dir.  
4. Update the **focused user skill** that owns the loop (not only terra-map).  
5. **Sync** skills to `~/.grok|claude|codex/skills/`.  
6. Note new gotchas in **this** skill.

---

## What not to do

- Do **not** ship user-skill-only changes without DX smoke  
- Do **not** invent a second agent envelope  
- Do **not** treat scaffold validate as survey complete  
- Do **not** assume active map == all maps  
- Do **not** freehand generic libraries in `src/terra/` without cg-plan when reusable  

---

## Completion criterion (Terra change)

1. `pytest -q` green,  
2. DX smoke paths that you touched still make sense,  
3. User skills updated if agent procedure changed,  
4. Skills synced to install path,  
5. New footguns listed under **Gotchas** above.
