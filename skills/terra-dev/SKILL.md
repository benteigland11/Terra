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
terra assumption create a --type number --quantity q --value 1 \
  --claim "working q?" --reason "DX basis" --evidence "measure q"
terra assumption get a               # conditional=true; map status notice
terra calculation create c --input a=assumption:a --type number --quantity q
# edit calc.py; calculation validate/run/get; changing a must stale c
terra gate                            # assumption passes; active unknown fails
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
# ARRAY, not a string. zsh does NOT word-split an unquoted scalar, so
# `for s in $USER_SKILLS` iterates ONCE over the whole string and silently
# mkdir's a literal dir named "terra-start terra-brief terra-route …".
# This bit us for real — check for it: ls -d ~/.claude/skills/*' '*
USER_SKILLS=(terra-start terra-brief terra-route terra-survey terra-scopes terra-map terra-probe)
for s in "${USER_SKILLS[@]}" terra-dev; do
  mkdir -p ~/.grok/skills/$s ~/.claude/skills/$s ~/.codex/skills/$s
  cp skills/$s/SKILL.md ~/.grok/skills/$s/SKILL.md
  cp skills/$s/SKILL.md ~/.claude/skills/$s/SKILL.md
  cp skills/$s/SKILL.md ~/.codex/skills/$s/SKILL.md
done
# Verify the sync actually landed (md5s match, no junk dirs):
# for s in "${USER_SKILLS[@]}" terra-dev; do
#   diff -q skills/$s/SKILL.md ~/.claude/skills/$s/SKILL.md || echo "OUT OF SYNC: $s"
# done
# product projects (skip terra-dev):
# for s in "${USER_SKILLS[@]}"; do
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

### 2a. Unknown vs assumption is a hard semantic boundary

All active records with `role: unknown` gate, including legacy
`blocks_build: false` records. Only `role: assumption` carries a consumable
typed value. Assumption reads must remain `conditional: true`, revisions need
a reason, evidence must not silently replace the provisional value, and
graduation must derive the known from linked evidence.

### 2aa. Calculation values have one legal doorway

`calculation` bindings accept only `known:<id>` and `assumption:<id>`.
Numeric/boolean literals are valid mathematical logic under assumed competence;
validation returns and results stamp a literal inventory instead of blocking
them. Results also stamp source+input hashes. A changed source or input makes
`calculation get` refuse the stale value. Assumptions propagate into
`conditional` plus the result's `assumptions` list; they never disappear behind
arithmetic.
Output `display.decimal_places` is presentation metadata: `run_calculation`
must preserve raw `value` and add a separate `{value, formatted,
decimal_places}` display envelope. Never round intermediates in the substrate;
engineering quantization belongs in `calculate(inputs)`.
Successful calculation runs stamp a shared evidence run with
`source_type=calculation`; `unknown link-calculation` attaches it and ordinary
graduation births a derived known. Never fabricate a probe id. Preserve source
hash, input snapshots, conditional assumptions, and dependency edges; moved
inputs/source must block the derived known as stale evidence.
Model `relation` outputs use finite, strictly x-ordered `points`; stamp every
point as a relation measure and require unknown type/quantity/x_quantity match.

`calculation profile=model` is the rigorous package rung: full imports,
`calculate(inputs, ctx)`, exact declared multi-output names, JSON-safe
diagnostics, explicit `health: {ok: bool}`, in-package artifacts with hashes,
and runtime/requirements stamping. Package hash covers top-level `*.py` plus `requirements.txt`; evict
package-local modules around each run so same-process reruns cannot execute
stale bytecode. Missing requirements block validate. Never infer solver health
from arbitrary diagnostics: model code owns the domain checks and must set
`health.ok`; false is preserved but stales the result and gates. Re-check
artifact existence/hash and Python/platform/installed dependency versions on
every read/gate. Reject non-finite numeric outputs.

### 2ab. Probe inputs are evidence provenance, not consumer trivia

Probe `inputs` accept only `known:<id>` / `assumption:<id>`. `run_probe`
resolves them into `ctx["inputs"]` and stamps bindings, snapshots, source hash,
conditionality, and assumptions. `record_input_state` is dynamic: moving an
input makes linked evidence stale, known reads refuse it, and gate/status block.
Conditionality must propagate through a known into later probes/calculations.
Source changes are audit provenance, not automatic invalidation of historical
observations; repeated tests often legitimately edit an instrument between runs.

### 2b. Active map: one shared pointer + TERRA_MAP per-shell pin

`.terra/active_map` is project-wide — concurrent sessions calling `map use`
clobber each other. Resolution (`paths.resolve_active_map`, returns
`(id, source)`): CLI `--map` context → `TERRA_MAP` env → pointer file →
global. Concurrent sessions must pin via `TERRA_MAP` or `--map`, never the
pointer. Surfaces: `map status` envelope carries `active_map_source` +
`active_map_missing` attention (env/file naming a nonexistent map);
`map use` under `TERRA_MAP` prints a NOTE (env still wins);
`map list`/status human lines tag `(via env)`. Watch out in-process:
`write_active_map` syncs the ContextVar, so after `map use` the source reads
"cli" even when the env is set — tests reset with `set_active_map_id(None)`
to model a fresh shell. Tests: `tests/test_map_env.py`.

### 2c. Write-target banner + inherited/stale scream on read

The active map was invisible until a write hit the wrong copy (a delete
landing on a silently-active session map). `cli._announce_write_target(root,
what)` prints a stderr line naming the target from `resolve_active_map`:
`→ … writes to map 'global'` (quiet) vs a louder `⚠ … writes to map 'sim_vv'
- NOT global …` when off-global (the actual footgun). Wired into the
mutators: unknown create/graduate/delete, known set/link-run/delete, probe
run (skipped on --dry-run), run void. `known delete` announces BEFORE the
destructive unlink. stderr so it never pollutes the JSON envelope on stdout;
banners land on both the `--json` and human return paths. On the read side,
`cmd_known_get` screams (stderr NOTE) when the reading is `inherited`
(map-chain read-through from an ancestor) or `stale` (returned under
--allow-stale) - both were previously tucked in quiet fields.
Tests: `tests/test_write_target.py`. When adding a new state-changing
command, call `_announce_write_target` and add a banner test.

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
Formula confidence follows the `n` ladder independently of `holds`; a failed
formula can be high confidence, and `holds=false` blocks `terra gate`.
The default `terra map status` row must expose `holds` + `verdict`, and failure
must produce blocking `known_formula_failed` attention + `known.show` action.
Promote med/high remains blocked when the `n` ladder is not met.
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

### 9b. Advertised commands must be wired

`known set` existed as cmd_known_set + substrate (and error messages
advertised it) but the argparse parser was never registered — agents hit
a phantom command and detoured through `status --notes`. When a message
or NOTE names a command, grep `func=cmd_...` to confirm it's wired; add
a CLI-level test (tests/test_graduate.py::test_known_set_cli_edits_claim).

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

### 12b. known supersede: soft tombstone (retire wrong belief)

`superseded` and `refuted` already existed in `KNOWN_STATUSES`
(number_type.py) but were INERT - the read path never checked status, so a
bug-derived value was handed out as current. `RETIRED_STATUSES = {superseded,
refuted}` + `knowns.supersede_known(reason, superseded_by=None, refuted=False)`
stamp a `superseded` block and set status. The scream lives in the READ path
(`readings._read_known_here`, keyed on status, `allow_superseded` escape
threaded through `read_known`) - NOT in the verb, because `set_known` /
`set_known_status` can also write those statuses; keying the refusal on status
closes that back-door. Reads with `--allow-superseded` return the historical
value tagged `superseded:true` + `superseded_info`. `supersede_known` requires
a reason and validates `--by` exists + isn't self. Map status:
`known_retired` (info) short-circuits the debt checks so a deliberately
retired known doesn't also alarm as unbacked/stale. CLI: `known supersede`,
`known get --allow-superseded`; `known delete` NOTE now points at supersede as
the non-destructive path. Tests: `tests/test_known_supersede.py`.

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
uncertainty+band, derived caps med, gate violation clears but surfaces as a non-blocking `notices` entry, attention downgrades to info); spread grew →
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

### 14b. route log is the timeline — no shadow trackers

`terra route log` (route.py `route_log`) is a **pure view** over
route.json: one event per evidence entry (note/runs/knowns/freehand),
bare events for evidence-less done tasks, `blocked` events for currently
blocked tasks, sorted by `at`. Added because agents were keeping shadow
markdown drive-logs when they couldn't read a chronological story out of
routes. Keep it stateless — never write log entries as separate state.
Tests: `tests/test_route_evidence.py` (route_log cases).

### 14e. Route liveness: status is not a heartbeat

`in_progress` is not a liveness signal — a lead that dies mid-task strands
its route in_progress forever, indistinguishable from active work (this
caused a real double-writer master-model corruption). Tasks now carry
`owner_agent` / `started_at` / `last_heartbeat_at` (route.py). `start_task`
takes `agent=` and stamps all three; `heartbeat_task` refreshes
`last_heartbeat_at` (and re-asserts owner) and REFUSES on non-in_progress;
`complete`/`block` null owner+heartbeat (started_at kept as history).
`route_attention` emits `task_no_heartbeat` (severity high, carries `owner`
+ `hours_since_heartbeat`) when a claimed task's heartbeat exceeds
`HEARTBEAT_STALE_HOURS = 6`; the day-scale `task_stalled` (updated_at ≥
`STALL_DAYS`) stays as the legacy backstop. Design invariants:
heartbeat does NOT touch `status` or task `updated_at` (updated_at tracks
real status/effort changes, so the 7-day stall check keeps working);
`task_no_heartbeat` only fires when `last_heartbeat_at` is present, so legacy
tasks (None) fall back to stall, never spam. Fields are optional + backfilled
in `load_route` (no schema bump) and type-checked in `validate_route`. CLI:
`route start --agent`, `route heartbeat <id> [--agent]`.
Tests: `tests/test_route_liveness.py`.

### 14c. Convergence + cohorts: coupled solves

`cohorts.py` + convergence block in `probe_run.py`. Two invariants:
(1) **the solve is the sample** — probes running iterative loops emit one
run with `convergence:{converged,iterations,residual,tol,criterion}`;
`converged:false` runs stamp but are refused by BOTH link paths
(knowns.link_run_known + unknowns.link_run). Iterates never stamp runs.
(2) **cohort = coupled knowns valid only as a set** (one solve → many
quantities). Membership is the only stored state
(`.terra/map/<scope>/cohorts/`); consistency is COMPUTED (members must
share identical live run sets) — never store it. Mixed cohort →
`cohort_inconsistent` in gate + map-status attention, `known get` refuses
on every member (`--allow-cohort-mismatch` escape). Fan-out refresh:
`terra cohort link-run <id> <run>`; `unknown graduate --cohort` joins at
birth; per-member `known link-run` prints a NOTE (plus a same-start
re-solve NOTE — identical `to` on a converge probe adds no n). Cohort CRUD:
`cohort set --members` replaces membership (and can update `--title`);
`cohort delete` removes only the declaration, preserving knowns/evidence.
Tests: `tests/test_cohorts.py`.

### 14d. Map tree: read-through, shadowing, adopt

Maps form a parent tree (`map create --parent`, meta `parent` field;
`paths.map_chain` walks child→global, loud on cycles). Reads
(`known get/show`, dep resolution, staleness overlay in
`staleness._load_all_knowns`) fall through the chain child-first; **writes
stay local**. A child known with the same id SHADOWS the ancestor's for its
subtree — graduate prints a NOTE; a post-adopt local copy keeps shadowing
until deleted (intentional: adoption never mutates the source map's beliefs
beyond the `adopted_to` stamp). `known adopt` / `cohort adopt` promote ONE
hop up: admission bar (`knowns._adoption_problems`, >= med, backed, agree,
not stale) re-checked per hop; live run dirs are COPIED to the destination
(maps stay self-contained — never cross-map run refs); deps must resolve
from the destination (bottom-up refusal). Cohort members refuse solo adopt.
`compute_staleness` now returns inherited ids too — `.get(kid)` callers are
unaffected, but don't iterate it assuming local-only keys.
Tests: `tests/test_map_tree.py`.

### 15. Relation type: F(x) knowns

`relation_type.py`: pairs from measures rows with `x`; stats per x-station
(exact match — shared grid is the contract); `n` = sweeps (runs with pairs),
not points. med ≥3 sweeps + ≥3 stations; high adds tight stations +
corroboration at ≥2 SHARED stations (disjoint grids → agree=None).
`evaluate_relation` = linear interp between station means, loud outside
x_range. read_known(at=...) / `known get --at` / records need
quantity + x_quantity. Tests: `tests/test_relation_type.py`.

### 15b. Formula known bindings + parent evidence

Formula vars accept run quantities (`--var measured=mtow`) or visible knowns
(`--var limit=known:spec_mtow`). Known bindings use the canonical read path,
become stamped known dependencies, and therefore stale the formula when the
bound belief moves. Formula-only run lookup walks the active map parent chain
child-first; ordinary known/unknown run links remain local. This lets session
closure formulas consume global evidence without duplicating run directories.
Tests: `tests/test_formula_type.py`.

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

### 17b. Gate self-check vs the DoR baseline

A gate (formula known) whose bar the certified-good design-of-record itself
fails is a bug in the gate, not a wall (Ben's dome acceptance bars measured
symmetry a master couldn't pass). `design._gate_baseline_notices` builds
`quantity → accepted value` from number/boolean design params
(`value_at_admission`, fallback live), scans GLOBAL formula knowns, and for
each uses `formula_type.extract_thresholds` (var-OP-constant comparisons;
n()/rate()/std() guards and var-to-var ignored; var-on-right normalized) to
resolve `var → quantity` via the known's `vars` map. If the baseline value
does NOT `satisfies_threshold` the bar, it emits a NON-BLOCKING
`gate_stricter_than_baseline` notice ("your pass threshold is stricter than
the design of record; intended?"). `check_design` returns it under `notices`
(+ counts.notices); `check_gate` folds design notices into gate `notices`
(map_id="design"), never `violations`. Scoped to global formula knowns
(design is global-sourced). Tests: `tests/test_gate_dor_selfcheck.py`.

### 18. Budget vs plan vs actual vs sectors

- `brief.budget_points` = authorized total (terra-brief).  
- `route.sectors[]` = reserved provisions (`reserved_points`).  
- `task.plan_*` = locked baseline; `task.bucket/points` = working; `task.sector_id` optional.  
- Initial allocation: sector plan ≤ reserve; unsectored ≤ free pool; total ≤ budget.  
- Locked: add only with `--sector`; `set-effort` may over-budget.  
- `unlock-plan` without `--confirm` must fail with WARNING text.  
- Tests: `tests/test_brief_route.py`.

### 19. sitrep: turns are the unit of cost, and exit codes break chains

`src/terra/sitrep.py` — composite READ (`collect_sitrep`) over `route_status` +
`collect_status_board` + `check_gate` + `brief_summary`. Pure view: no new
state, nothing stored (test asserts `.terra` mtimes are unchanged).

Motivation is measured, not aesthetic. An agent turn costs a re-read of its
whole context (~14k specialist / ~22k lead / ~28k PM tokens) **regardless of
the command**, so the CLI's one-command-per-invocation shape made orientation
cost 5 turns. On a real program (CG-01, 11 days): Terra-bearing turns were 26%
of total token spend while Terra's own OUTPUT was <4% of that — optimizing
verbosity would have been a rounding error; collapsing round trips was the win.

Three invariants, each with a test that can actually fail (mutation-checked):

1. **ALWAYS exits 0 on success, even when the gate fails.** `terra gate` exits
   1 by design; 64 CLI paths return nonzero as a *verdict*. Agents batch with
   `cmd_a && cmd_b`, so a verdict-nonzero silently aborts the rest of the chain
   and the run still looks clean. sitrep puts the verdict in `data.gate.ok`.
   If you add a composite/orientation verb, copy this rule.
2. **Rollup before sample.** 340 open unknowns produce 340 near-identical
   attention rows; naive truncation to 12 shows twelve copies of one fact and
   hides every other KIND. `_summarize_attention` counts by
   (plane, kind, severity) and is never truncated; `_diverse_sample`
   round-robins across kinds so a rare kind is reached before a common one
   repeats. This is what made 6 unbacked knowns and 88 blocked tasks visible
   under a flood of unknowns.
3. **Truncation is declared, never silent.** `truncated{}` reports what was
   dropped; `--full` removes caps. Agents were previously doing `| head` on
   `route status` — `route status` is **2.5 MB** on a large program — which is
   silent truncation an agent cannot distinguish from a short list.

Route attention rows carry no `map_id`; sitrep tags both planes (`plane:
route|map`) so the two debts stay distinguishable in one merged list.
Beware `budget_rollup` key names: `points_plan` / `points_actual` /
`points_remaining_budget` (NOT `planned_points`) and it embeds every sector row
— `_slim_budget` strips it. Tests: `tests/test_sitrep.py`.

**Shell gotcha that bit this work:** zsh does not word-split unquoted scalars,
so `for c in "route status"; do terra $c; done` passes ONE argv `"route
status"` and every command silently returns empty. Use `${=c}` or an array —
same family as the skill-sync bug in section C.


### 20. Agent-DX fixes from the 2026-07-27 lead handbacks

Five real defects, all of the same family: **the tool let an agent believe
something false.** Tests: `tests/test_agent_dx_fixes.py` (mutation-checked).

1. **A failure that reads as success.** The error envelope ends
   `"code": "route_complete"` + closing braces, so `| tail` shows the
   operation name and an agent reads it as done — a lead marked THREE routes
   complete that had failed. Fix: `agent_io.emit` now prints
   `TERRA ERROR [code]: <first line>` to **stderr** on any non-success.
   stdout stays strictly JSON. When you add an output path, do not bypass
   `emit`.
2. **`route start` on an in_progress task said "waiting on None".** An
   in_progress task carries `pickable=False`, so it fell into the deps
   branch — meaningless for the exact stranded-lead case `--agent` documents.
   Now an explicit RECLAIM path: reclaim when owner is None OR heartbeat
   ≥ `HEARTBEAT_STALE_HOURS`; **refuse loudly when the owner is alive**
   (that refusal is the double-writer interlock — keep it can-fail); a
   same-agent restart is just a heartbeat. Stamps `reclaimed_at` /
   `reclaimed_from`.
3. **Probe env reads were invisible.** Declared `inputs` only cover
   `known:`/`assumption:`; a probe reading `os.environ` consumed an input the
   run record never mentioned, so a hand-pinned run and a bare run were
   byte-indistinguishable and the forced one could graduate a belief. New
   `src/terra/env_reads.py` swaps `os.environ` for a recording proxy during
   the call and stamps `env_reads` on the run. Secret-looking keys are
   redacted; ambient shell vars filtered; `complete: false` because
   **subprocesses are not instrumented** — say what you cannot see rather
   than implying coverage.
4. **`route log` had no `--task`.** A lead hand-parsed `route.json` to read
   one task's history — the shadow-tracker habit `route_log` exists to kill.
   `route_log(..., task_id=)` + `--task`; unknown id raises.
5. **`unknown get` did not exist** while `known get` does, and the
   nearest-looking verb `unknown status` is a **SETTER**. Aliased to
   `unknown show`.

**Three of seven reported "bugs" did NOT reproduce** — the symptoms were real
but the diagnoses were wrong. Reproduce before fixing:
- "`known get` emits a NOTE preamble on stdout" — it is already on stderr;
  stdout parses clean.
- "consumer registration bumps `updated_at` and cascades staleness" —
  isolated it; a read leaves `updated_at` untouched. Something else moved it.
- "`sitrep --json` has non-JSON preamble" — stdout was pure JSON; the real
  fault was that `--json` was **not an accepted flag**, so argparse exited 2
  with EMPTY stdout and the caller's `json.load` failed at char 0. Symptom
  "corrupt JSON", cause "bad flag". **Lesson: an unrecognized flag that
  empties stdout is indistinguishable from corrupt output — accept the
  no-op flag when every sibling verb takes it.**

**Known inconsistency deliberately NOT changed:** `unknown show/get` prints
human text by default and JSON under `--json`; `known get` is JSON-first.
Flipping it would break existing agent parsing. Left as-is; revisit only with
a deprecation path.


### 21. Run provenance: a run must say what it was computed against

`readings.record_reads(sink)` + `known_reads` on the run record (mirrors
`env_reads`, §20.3). Declared probe `inputs` only cover explicit
`known:`/`assumption:` bindings; **most probes declare none** and call
`read_known()` from inside their own code, so the record never said which
beliefs produced the number. Screening ~6,000 orphaned runs by design-of-record
basis was therefore only possible by bucketing on timestamp — the tech lead
named this a *prerequisite enabler* before any mass-linking campaign.

Each row: `known_id`, `map`, `value`, `confidence`, **`as_of`**, plus
`stale`/`inherited`/`conditional`/`superseded` flags when set. `as_of` is the
screening field — a value alone cannot tell you which design era produced it.

Design notes:
- The record lookup for `as_of` runs **only when a sink is active** (inside a
  probe run), so ordinary CLI/consumer reads pay nothing.
- `_note_read` swallows every exception: **provenance must never break a
  measurement.**
- Dedupes per `(known_id, map)` — a probe reading the same belief in a loop
  records one row.
- **`--dry-run` returns before the stamp block**, so dry runs show neither
  `known_reads` nor `env_reads`. Verify with a real run; the tests do.

### 22. Reported DX bugs need REPRODUCING — 4 of 9 did not exist

Running total from the 2026-07-27 handbacks. Real: error-envelope silence,
`route start` "waiting on None", env-read invisibility, `route log --task`,
`unknown get`, `sitrep --json`, gate-counts-superseded, missing run provenance.
**Not reproducible:** `known get` NOTE on stdout (already stderr), consumer
registration cascading staleness (isolated — a read leaves `updated_at`
untouched), `sitrep` JSON preamble (real cause: unaccepted flag → argparse
rc=2 → EMPTY stdout), **`known show --json`** (it has existed all along).

The recurring shape is an agent inferring a cause from a symptom and reporting
the cause as fact. Reproduce first; a "fix" to a non-bug adds surface and hides
the real defect. The `unqualified_scalar_source_audit` case is the sharpest:
the PM (me) called its `rules.py` dep a mis-pinned lint dep and told a lead to
unpin it — the lead checked the probe, found it `importlib`s `rules.py` by path
and executes its detectors, and **correctly refused**. The dep is real; the
"fix" would have deleted a live alarm.

### 23. Probe validation stamps: run refuses an unvalidated instrument

`src/terra/probe_stamp.py`. `validate_probe_dir` now writes
`<probe>/.validation.json` = {ok, level, source_sha256, validated_at,
terra_version, blocks, warnings}. `run_probe` calls `ensure_validated(pdir)`
BEFORE loading the module: hash matches a passing stamp → run; missing / stale
/ last-failed → revalidate inline, PASS proceeds (CLI prints a stderr NOTE),
FAIL raises with the blocks and **stamps no run**. Provenance lands on the run
record as `validation` {state, revalidated, source_sha256, validated_at}.

Design points that matter:
- Hash covers `probe.json` + every `*.py` in the package (recursive, minus
  `__pycache__`) + `requirements.txt`. **probe.json is in the set** — entry,
  kind, duration, and inputs change what the instrument is, not just its code.
- The stamp file is deliberately NOT hashed (it lives in the package so it
  travels with the probe; hashing it would self-stale on every write).
- `write_probe_stamp` swallows `OSError` — a read-only probe dir must not
  break validation itself; the missing stamp just means run revalidates.
- **This is a real behavior change for existing probes.** Level-1 declaration
  checks (`REQUIRED_EXPORTS`, `KIND`/`DURATION_S`) were previously enforced
  only by `probe validate`, never by `probe run` — 15 test fixtures wrote
  probes that ran fine and could never have validated. They were fixed, not
  exempted. Expect the same in live projects: the first run after upgrading
  reports the debt.
- Map lib (`.terra/map/lib/`) is NOT in the hash — a helper edit does not
  stale probe stamps. Deliberate scope, but it is a hole; revisit if lib
  churn starts producing surprises.
Tests: `tests/test_probe_stamp.py`.

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
  terra-survey/     unknown/assumption/known/calculation/plan/void
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
