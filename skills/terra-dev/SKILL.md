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

### 24. Route priority: WHICH work, orthogonal to HOW MUCH effort

`TASK_PRIORITIES = ("p0","p1","p2","p3")`, `DEFAULT_PRIORITY = "p2"` in
route.py. Added because a real program (CG-01) reached 118 open routes with
**no ordering at all** — `next` returned 88 pickable in insertion order, so the
four load-bearing physics gaps sat unworked for days behind cockpit-ergonomics
and probe-hygiene routes. Effort buckets were the only dial, and effort is the
wrong question when the failure is allocation.

Design decisions worth not re-litigating:

- **`p0..p3`, NOT `low|medium|high`.** Those words already mean the effort
  bucket. `--bucket high` typed when `--priority p0` was meant is a silent
  wrong-field write with no downstream detector. Distinct vocabulary is the
  whole defense.
- **Legacy backfill is `p2`, never `p0`** (`load_route`). Promoting an
  unranked backlog to urgent would make the first priority-sorted `next` a
  lie about what the program had decided. Test:
  `test_legacy_task_backfills_to_default_not_urgent`.
- **Priority never touches points / plan_points / budget**, so
  `set_task_priority` works under `plan_locked` with no unlock. If it required
  an unlock nobody would ever deprioritize, which defeats the feature.
  Tests: `test_prioritize_does_not_move_budget_or_effort`,
  `test_prioritize_works_under_plan_lock`.
- **`next` sorts but `counts.by_priority_open` never truncates** — same
  rollup-before-sample rule as sitrep (§19.2/19.3). A sorted window hides the
  tail; the rollup is the declaration of what it hid. `_slim_task` carries
  `priority` so sitrep (the first command of every session) shows it — a rank
  the orientation digest drops is a rank nobody acts on.
- `set_task_priority` is **atomic**: unknown id raises before any write.

**Bug this surfaced in existing code:** `route_log` hardcoded
`"kind": "complete"` for **every** evidence row, so any non-completion event
would have been rendered in the timeline as a COMPLETION. Now
`entry.get("kind") or "complete"` — backward-compatible (legacy rows carry no
kind). Whenever you add a new evidence kind, check the log renderer actually
distinguishes it.

**Pre-existing flake, not caused by this work:**
`test_agent_dx_fixes.py::test_json_flag_accepted_on_every_read_verb[argv6]`
(map.status) fails intermittently in the full suite and passes in isolation —
it compares two sequential CLI invocations and something time-dependent
differs. Worth root-causing separately; do not chase it from a route change.

### 25. A CANCELLED dep strands its dependents FOREVER — and used to do it silently

`_recompute_ready` computes `waiting = [d for d in deps if status != "done"]`.
A **cancelled** dep is not done, so it stays in `waiting_on` permanently: the
dependent reads `status=ready`, `pickable=false`, `waiting_on=[dead_id]` —
byte-indistinguishable from work that is merely queued. There was no attention
item, no gate violation, no error.

Measured on CG-01 the day this was found: **22 of 118 open routes transitively
unreachable**, including `cfd_drag_polar_supersonic` (the program's ONLY open
CFD route, gating two of five program gates) and `simreal_airborne_basis_freeze`
(root of the entire 11-route flight-demo chain). The backlog looked healthy
while every pickable item was a loose defect-fix.

**Why this shape recurs:** cancellation is how you retire a superseded
approach, so the routes most likely to have cancelled deps are exactly the ones
downstream of work you REDIRECTED — i.e. the spine. The failure targets your
most important work by construction.

Design decisions:

- **We do NOT auto-unblock.** A cancelled basis often means the dependent's
  premise died with it; silently making it pickable is the worse lie. The
  defect was the SILENCE, not the blocking. Make it visible, let a lead decide:
  re-point the dep, or cancel the dependent too.
- **Unreachability is TRANSITIVE and computed to a fixpoint.** The first cut
  checked one hop and reported 9 where 22 were dead — a 2.4x undercount on an
  instrument whose entire job is "what can never be worked." Roots emit
  `task_dep_cancelled` (severity **block**) and name themselves; downstream
  tasks emit `task_unreachable` (severity high) carrying `root` so you fix the
  root, not the symptom. Both computed in `_recompute_ready`, never stored.
- **Prevention at the write site:** `cmd_route_cancel` calls `dependents_of()`
  BEFORE cancelling and prints a stderr NOTE naming every live task the cancel
  is about to strand; the payload carries `stranded_dependents`.
- **Priority does not rescue a dead route.** `test_p0_ranking_cannot_rescue_a_
  dead_route` asserts `next --priority p0` still returns nothing — which is why
  the attention item is the only thing between a dead spine and silence. Ranking
  and reachability are independent failures; do not let one mask the other.

Tests: `tests/test_route_priority.py` (transitive closure, root-vs-downstream,
alarm clears on re-point, live-dep can-fail, `dependents_of`).

### 26. Lifecycle stress: terminal-state resurrection + phases were a no-op

Found by adversarially walking a whole project lifecycle
(`tests/test_route_lifecycle.py`), asking at every verb: *can this silently do
nothing, or report something untrue?* Ten candidates, six real.

**A. Terminal states were re-openable.** `done` and `cancelled` each assert a
settled outcome that later records hang off. All of these silently succeeded:
`cancelled --complete--> done` (launders a dead premise into a completion,
which `route_log` then renders as a genuine completion event),
`cancelled --unblock--> ready` (dead work straight back into the pickable
queue), `cancelled --block-->`, `done --block-->`, and re-`complete` on done
(appends a SECOND evidence block as if the work happened twice).

The rule already existed — `cancel_task` refused on `done` with "would erase
its evidence; supersede instead" — **in exactly one place, never generalised**.
Now `TERMINAL_STATUSES` + `_refuse_if_terminal(task, verb)` guards every
state-changing verb, and the error names the legitimate escape (supersede the
belief / add a NEW task). The one pre-existing test asserting the old message
was updated; behaviour is unchanged there, which is the confirmation the
generalisation absorbed it correctly.

**Deliberate non-defect:** `blocked --complete--> done` is ALLOWED and pinned by
`test_blocked_can_still_complete`. A blocker is often resolved by the work
itself; refusing would be over-reach. Do not "fix" it.

**B. `cancel` bypassed the double-writer interlock.** `start_task` refuses to
touch a task whose owner is alive; `cancel` destroyed live claimed work with no
check at all — same hazard, same incident class. Now refused unless the
heartbeat is stale or `--force` is passed.

**C. Out-of-order completion is SURFACED, not refused.** A `done` task with an
unfinished dep means the DAG and the record disagree. Deps are often soft
ordering and a hard refusal would push agents to freehand around the route, so
this emits `task_done_before_deps` (med) instead of raising.

**D. `task.phase` was WRITE-ONLY.** Stored in `add_task`, echoed in
`route_log`, used nowhere else — no validation, no filter, no rollup — while
`brief.phases` was a separate list with its own `add_phase` verb. Two
half-features that never met, which is exactly why nearly every task left it
blank: it did nothing, so nobody filled it.

Now `phase_rollup()` + `terra route phases` + `next --phase` + a slim current-
phase line in sitrep. Design rules:

- **Validate only when the brief declares phases.** A project using none keeps
  free text — do not break it, and do not nag it (`_phase_attention` returns
  early). Once phases ARE declared, an undeclared tag is refused at `add_task`.
- **Empty phase is NOT exit-ready.** No tasks means UNPLANNED, not complete;
  otherwise the lifecycle skips straight through unplanned work.
- **Unreachable tasks block phase exit** and emit
  `phase_exit_blocked_by_unreachable`. Without this, a phase full of routes
  stranded on cancelled deps (§25) reads as "almost done, just waiting"
  forever.
- **Undeclared tags are reported but can never become `current`** — a typo must
  not silently redefine where the program is.
- **Unphased open tasks are declared** (`tasks_unphased`, info): they block no
  phase exit and count toward no phase, which is a real hole and must be stated
  rather than discovered.

**What it found on CG-01 the moment it went live:** declared phases `p1..p5`,
but the actual work tagged `phase1` — undeclared — holding 20 open routes with
19 unreachable, while declared `p1` read **exit-READY** and the lifecycle
reported "current phase: p2". Seven spellings of the same phase (`phase1`,
`detailed_design`, `p1_detailed_design`, `P1`, `Phase 1`, `1`, `p1_detail`) and
**99 of 118 open tasks carrying no phase at all**. The program would have
reported Phase 1 complete. The division of labour is the point: the count stays
honest about what it counted, and a SEPARATE alarm says the tagging is broken.

### 27. Derived fields must never be persisted — and stripping them means EVERY read must recompute

Two halves of one lesson, both found on live work.

**Half 1 — the trap.** `pickable` / `waiting_on` were written into `route.json`
even though both are computed from `deps`+`status` on every load. A lead
repairing the dead DAG (§25) edited `waiting_on` directly, read the file back,
saw its edit, and had it silently clobbered by the next `terra` command — its
follow-up audit still reported the unrepaired count. **Had it trusted its own
read-back it would have reported a clean spine over a dead DAG.** A computed
field sitting in the file is an invitation to edit it. `save_route` now strips
`DERIVED_TASK_FIELDS` so `deps` is the only lever, and
`test_hand_edited_derived_field_cannot_fake_reachability` asserts that
hand-clearing `waiting_on`/`pickable` cannot make a dead route look alive.

**Half 2 — the regression that fix caused, which is the more important half.**
`load_route` did NOT recompute; only `save_route`/`route_status` did. So with
the fields stripped from disk, every consumer reading through `load_route` got
`None` instead of `False` — and **`start_task`'s dependency interlock
(`if t.get("pickable") is False or t.get("waiting_on")`) silently stopped
firing**, letting a task with unmet deps be claimed. Caught only because
`test_brief_route.py::test_route_deps_and_next` asserts the refusal.

**The rule:** removing persisted computed state is only safe if the READ path
always rebuilds it. `load_route` now calls `_recompute_ready`. Cost measured on
a 1,283-task program: ~14 ms per load, negligible.

**The generalisable shape:** a guard written as `x is False` fails OPEN when `x`
becomes absent. Prefer `not t.get("pickable")` for interlocks, or guarantee the
field's presence at the read boundary — do not leave a safety check depending
on a key some code path may stop writing. Regression guard:
`test_start_refuses_task_with_unmet_deps`.

### 28. route.json is written CONCURRENTLY — it needed atomicity and a lost-update guard

Several leads drive Terra at once. `save_route` was a bare
`path.write_text()`: no atomicity, no locking, no staleness check. Two real
failures on CG-01:

1. **Torn reads.** A lead hit "raw JSON parse errors mid-batch" while a peer
   wrote concurrently. `write_text` truncates then writes, so a reader landing
   in that window parses a partial file — on the program's central record.
2. **Silent lost updates**, which is worse. `load_route -> mutate ->
   save_route` is a read-modify-write. Two leads that both load, both mutate
   and both save mean **one edit vanishes with no error at all**. Nothing in
   the system could detect it after the fact.

Fixes, both in `save_route`:

- **Atomic publish**: same-dir `mkstemp` + `flush` + `fsync` + `os.replace`,
  with the temp unlinked on any exception. Readers now see only whole files.
  Same-dir matters — `os.replace` is only atomic within a filesystem.
- **Optimistic concurrency**: `load_route` stamps `_BASELINE_KEY`
  (`_loaded_sha256`) with the sha256 of the bytes it read; `save_route`
  re-hashes the file and raises **`ConcurrentRouteWrite`** if it moved. This
  converts a silent lost update into a loud refusal naming the recovery
  (re-read, re-apply). The key is popped before serialisation and is
  asserted never to reach disk.

Design notes:

- **Records with no baseline are allowed through** (init paths, hand-built
  dicts). A missing baseline means "not loaded from disk", not "stale" —
  refusing those would break `init_route`.
- We did NOT reach for `fcntl.flock`. A lock would have to be held across
  load->mutate->save (a caller-side API change touching every mutator) and
  would deadlock across the agent boundary if a lead died holding it.
  Detect-and-refuse is weaker than mutual exclusion but it is honest, has no
  liveness hazard, and the retry is trivially safe.
- **This is an ALREADY-LIVE change under an editable install.** Source edits
  take effect for running agents immediately — there is no deploy step to
  gate on. When patching Terra while leads are working, run the full suite AND
  smoke the live program (`route status`, `sitrep`, one real write) in the
  same turn.

Tests: `tests/test_route_concurrency.py` — lost-update refused, reload-retry
succeeds, uncontended save unaffected (can-fail), baseline never on disk, and
a simulated crash mid-write leaves the original byte-identical with no temp
leftovers.

### 29. A warning that keeps being missed is decoration — escalate it to a refusal

`link_run` printed a stderr NOTE when a linked run added **zero samples**
(quantity-name mismatch: the unknown declares `foo`, the probe emits
`foo_bool`). The note shipped 2026-07-28 after five FlightGear sessions were
silently worth nothing. **By 2026-08-08 the identical defect had voided
evidence at least three more times in a single day** — canon empennage
presence, the D9 washout trade verdict, and a tmp-path-literals sweep. Each
time the link "succeeded", `n` stayed 0, and a real finding could not graduate
despite good evidence sitting behind it.

`link_run` now RAISES `LinkAddedNoSample` unless `allow_no_sample=True`
(`--allow-no-sample`). The message names the declared quantity, what the run
actually emitted, `NAME MISMATCH` when they differ, and the way forward.

The generalisable rule: **stderr NOTEs are for things an agent should notice;
they are NOT sufficient for things that silently destroy evidence.** If a
warning has fired repeatedly on real work and the defect still recurs, the
warning is not working — make the operation fail and give it a deliberate
override. Track recurrence: one miss is bad luck, three in a day is a design
verdict.

Where the override is legitimately needed: cohort fixtures link a run to a
member whose quantity that solve does not emit, to exercise RUN-SET
consistency rather than evidence weight (`tests/test_cohorts.py`). Forcing
those to say `allow_no_sample=True` documents the edge case instead of hiding
it — which is the point.

Tests: `test_link_run_REFUSES_when_it_adds_no_sample` (refusal, message
content, record left untouched, override works) plus the can-fail
`test_link_run_still_succeeds_when_it_DOES_add_a_sample`.

### 30. Quantity NAME is the only match key — and it bites in BOTH directions

Terra corroborates by grouping runs on the quantity name. Two failure modes,
both observed on CG-01 within hours of each other:

- **False negative:** a `pml_` prefix on an otherwise genuine second method
  made it invisible — `methods` stuck at 1, so a real corroboration never
  counted. (Same family as §29's zero-sample link.)
- **False POSITIVE, which is worse:** two probes both emitting `n_stale` over
  **different denominators** (65 live working sheets vs 44 frozen release
  files) produced `methods=2` and a reported value of **3.5 — the mean of 7
  and 0.** A number describing nothing, presented as corroborated.

The false positive was completely silent: with no `tolerance` declared,
`compute_corroboration` sets `agree=None` and deliberately "surfaces the
spread, doesn't judge". Honest about not judging — but nothing said the
reported mean was averaging across an unjudged gap.

`methods_unjudged(stats)` now fires when **methods>=2 AND no tolerance AND
`spread_rel > UNJUDGED_SPREAD_REL` (0.10)**, emitted by `check_gate` as a
NON-blocking notice. It cannot claim disagreement (that is
`methods_disagree`'s job and requires a tolerance) — it says agreement is
*unjudgeable* and names both remedies: declare a tolerance, or check the two
probes measure the SAME proposition.

Deliberately a notice, not a violation: a wide spread with no tolerance is
often just an un-tuned young belief, and making it blocking would wall off
ordinary survey work. It found **2 real instances on the live program the
first time it ran**, one at 300% across 3 methods.

Design note: do NOT try to auto-detect "different populations". Terra cannot
know a denominator. The honest move is to surface that the question is
unanswered and make a human name the tolerance — which is exactly the act
that forces someone to ask what the two probes are measuring.

Tests: `tests/test_methods_unjudged.py` — flagged when far apart and
untoleranced, cleared (into real `methods_disagree`) once a tolerance is
declared, plus can-fails for near-agreement and single-method.

### 31. A flaky test is a lying instrument — fix it, do not work around it

`test_json_flag_accepted_on_every_read_verb` compared the payloads of TWO
separate CLI invocations byte-for-byte. Those runs happen at different
wall-clock times and the payloads carry `updated_at`, `as_of` and
age-derived fields like `hours_since_heartbeat` — so it failed whenever the
pair straddled a second boundary, on a rotating cast of `argv` ids (it hit
`argv6`, then `sitrep`, then `argv6` again).

I worked around it THREE times before fixing it — re-running the suite to
confirm "it's just the flake." That habit is the damage: a test that fails
randomly trains everyone, including me, to discount real failures. It also
cost a verification cycle every time Terra changed.

Fix: `_stable()` recursively strips `_VOLATILE_KEYS` (clock-derived fields)
before comparing. The claim under test is that `--json` is an accepted
**no-op**, not that the clock stood still.

**Do not just widen the assertion — prove it still has teeth.** Verified by
hand that `_stable` compares EQUAL when only volatile fields differ, and still
CATCHES a changed value and an extra list row. Then ran it 12× in isolation:
12/12 green.

Rule: when a test fails intermittently, treat it as a defect in the test's
claim, not as noise. Ask what the test actually asserts, narrow it to that,
and add a can-fail proving the narrowed version can still fail.
