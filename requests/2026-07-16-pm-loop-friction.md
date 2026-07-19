# Terra optimization requests — from the CG-01 autonomous PM loop

Source: CG-01 Phase-1 program, ~1,750 pts of real use, hands-off PM running an
autonomous 24/7 loop over three leads. These are friction points that **actively
cost time or caused an incident**, ranked. Written per the owner's invite to
request optimizations rather than keep hand-patching. Not a wishlist — each item
cites the specific incident that motivates it.

---

## P0 — Route liveness signal (the one that caused a real incident)

**Problem.** `route status = in_progress` is not a liveness signal. It means
"started, not marked done." A lead/agent that dies or strands mid-task leaves its
route `in_progress` indefinitely, indistinguishable from active work. The PM
(especially an autonomous loop) is structurally blind to "is this actually being
worked, or is it stranded?"

**Incident.** Earlier in this program the PM inferred liveness from ledger state
("no runs stamped → the lead must be stranded"), re-dispatched on that inference,
and caused a **double-writer corruption of the master OML** (two agents writing
`airframe.stl` concurrently). The lesson stuck ("never act on liveness inference,
ask the lead") — but the tool gives no way to *know*, so the PM must either ask
(costs a round-trip) or guess (caused the corruption).

**Proposed change.** Add a heartbeat / `last_touched` timestamp (and ideally an
owning-agent id) to `in_progress` routes, surfaced in `route status`/`route
budget --human`. Then "working" (recent heartbeat) vs "stranded" (stale) is
mechanically distinguishable, and an autonomous PM can reclaim stranded routes
safely instead of guessing.

**Acceptance.** `route status` shows time-since-last-touch on in_progress routes;
a route untouched beyond a threshold is flaggable as `stranded`.

---

## P1 — Gate should sanity-check its own thresholds against the DoR baseline

**Problem.** Nothing stops an acceptance gate from being specified with thresholds
the current design-of-record baseline itself fails. The gate silently rejects
every candidate against an impossible bar.

**Incident.** The dome-rebuild gate was specified with `symmetry_MAX` and
*absolute* self-intersection count. The **certified-good frozen master** measures
91 mm max / 12,097 self-int — i.e. it fails those very bars. Real candidates were
rejected against a bar the DoR can't pass, manufacturing multiple false "walls"
across several rounds before a human caught that the *metric definition* (should
have been `mean` / *delta-over-baseline*) was wrong.

**Proposed change.** Let a gate/probe validate its pass thresholds against the
current accepted baseline and warn: "threshold stricter than the DoR baseline on
metric X — intended?" Optionally support delta-vs-baseline thresholds natively.

**Acceptance.** Defining a gate whose bar the baseline fails emits a warning at
definition time, not a silent per-candidate FAIL.

---

## P2 — A "retire/supersede a known-wrong belief" verb

**Problem.** When a belief is bug-derived and *wrong* (not merely stale), the only
tools are `known set` (metadata only — can't touch the value) or `known delete`
(destructive, loses history, and has map-chain targeting hazards — see P3). There
is no soft tombstone between "leave it stale-flagged" and "nuke it."

**Incident.** Two beliefs this session were known-wrong from fixed bugs
(`sm_relaxed_floor_standard` -5.27% on a superseded mass-centroid bug;
`dash_margin_unaffected_by_ballast_221` on two dead premises). `adopt` refused the
corrected value (correctly — low conf), so global was left asserting a wrong
number; `delete` felt too destructive/risky to reach for.

**Proposed change.** `known supersede <id> [--by <run|known>] --reason` that
tombstones a belief: retained as history, refused (or loudly flagged) as current,
non-destructive. Louder than a stale flag, softer than delete.

**Acceptance.** A superseded known is excluded from `known get` as current (or
returns non-zero/loud), still visible in history/audit.

---

## P3 — Map-targeting is a footgun (active-map invisibility + quiet stale reads)

**Problem.** (a) The active map can silently be a session map (`sim_vv`), and a
state-changing command (`known delete`) will act on whatever the chain resolves —
discovered only when a delete was about to hit the wrong copy. (b) `known get` on
a stale, known-wrong *global* value returned **exit 0** with the bad number, with
staleness only in a field (`inherited: true`), not loud.

**Proposed change.** Echo the target map on state-changing commands ("writes to
`sim_vv`"); make `known get` return non-zero / loud when the value it resolves is
stale or superseded, rather than a quiet field.

**Acceptance.** `known delete`/`set` print the map they mutate; `known get` of a
stale/superseded value is unmistakable in exit code or stderr.

---

## P4 — minor

- Superseding a route doesn't reclaim its points — a phantom 8 pts sits on
  `p1_flutter_gate_wire`. Superseding should reconcile the allocation.
- Corroboration counts methods by *quantity name*; a name mismatch
  (`dc_tru_..._a` vs `tru_..._a`) silently forfeited an earned second method.
  Documented in the skill now, but an explicit proposition-id + independence
  attestation would be more robust than name-equality.

---

## P5 — Formula vars should bind to KNOWNS, not only run-measures (the "spec as a belief" gap)

**Problem.** A formula unknown resolves its `--var` quantities ONLY from linked-run
measures, keyed by quantity NAME, per-run. So an acceptance criterion of the natural
shape `measured ≤ spec` cannot reference the spec as a live belief — the spec isn't
run-emitted, and if it shares the measured quantity's name it collides into a
tautology or silently yields no data (falsely OPENing a healthy formula). You are
forced to bake the spec in as a literal constant, which means the spec is no longer a
first-class, auditable, single-source belief — change the requirement and every
closure formula must be hand-edited.

**Incident.** Building the CG-01 "final-design space" — 9 `closes_*` acceptance
formulas (`mtow_final ≤ spec_mtow`, `combat_radius_final ≥ spec_combat_radius`, …).
The intended encoding (measured var + spec var, both beliefs) was impossible; we
reverse-engineered the eval mechanics and settled on measured-var + **literal**
spec-constant to avoid polluting the map with tautological formulas. Works, but the
spec values are now hardcoded in 9 files instead of wired to `spec_*` knowns.

**Proposed change.** Let a formula `--var` bind to a KNOWN by id (its current value),
not only to a run measure by quantity-name. Then `measured_var ≤ spec_known` is
expressible, the spec stays one auditable belief, and re-baselining a requirement
re-flags every dependent closure formula automatically (Law 9, at the formula layer).

**Acceptance.** A formula can reference a known's value as a bound; changing that
known re-flags the formula. No literal duplication of a value that already lives in a
belief.

---

## P6 — Formula var resolution should read through the map parent chain

**Problem.** `known get` honors the map parent tree (a session map reads through to
its global parent). Formula var resolution does NOT — `link-run` refuses a
global-map run into a session-map formula. So a closure formula authored on a session
map cannot consume evidence that lives on global, even though every other read path
sees it. This strands criteria whose backing evidence is (correctly) already
graduated to global.

**Incident.** In the same closure build, `closes_ceiling` and `closes_thrust` show
OPEN despite their measured values (16 500 m ≥ 15 500; 140 kN = 140) satisfying spec
— purely because the backing runs are on the global map and the session formula
can't link them. Two healthy criteria read as unproven for a plumbing reason. The
workaround is to author the whole final-design space on global, but that forfeits the
session map as a prototyping surface for the pattern.

**Proposed change.** Formula var resolution should read through the parent chain the
way `known get` does — a formula on a child map may resolve a var from a run/known
visible via its parent. (Or: an explicit `--through-parents` opt-in if silent
read-through is judged too magic for evidence linking.)

**Acceptance.** A session-map formula can resolve a var backed by a global-map run
without re-stamping the evidence locally; behavior matches `known get` read-through.

---

## P7 — Cohorts are grow-only with no refresh/replace, blocking a coherent design-of-record promotion

**Problem.** A cohort cannot be refreshed or replaced. Once a `sizing_set` cohort
exists on a map, `cohort adopt` from a child map refuses with "already exists,"
and there is no `cohort supersede` / `cohort refresh` / `--force`. Individual
member `known adopt` also refuses ("member of cohort — adopts as a set"). So a
stale cohort on a parent map is a permanent roadblock to promoting the coherent
child-map cohort up.

**Incident.** Closing CG-01 Phase-1: the global map held a stale Phase-0
`sizing_set` (mtow 12346.4 / empty 7400) and the coherent Phase-1 `sizing_set`
(mtow 11719.1 / empty 6772.7) lived on the `closure_design` child. I could
`known supersede` the standalone stale DoR copies cleanly (P2 verb — worked great,
global now loudly refuses the stale values), but the COHORT could not be replaced:
`cohort adopt` refused "already exists," and there is no cohort-level supersede.
Result: the coherent design-of-record cohort is stuck on the child map, reachable
only via read-through, never consolidated onto the durable global node. Deleting
the stale global cohort is the only path and `known/cohort delete` is
permission/classifier-blocked (correctly — it's destructive).

**Proposed change.** A non-destructive `cohort supersede <id> --by <child-cohort>`
(mirroring `known supersede`), OR let `cohort adopt --from <child>` replace a
superseded parent cohort. Grow-only is the right default for *members*; it should
not prevent promoting a newer coherent solve of the whole set up the map tree.

**Acceptance.** A child-map cohort can replace a superseded parent-map cohort of
the same id without a destructive delete; the old one tombstones, the coherent one
becomes current on the parent.

---

*What's working well (so the signal isn't all friction): accept-spread surfacing
method disagreement at the gate, the tripwire/cascade wiring, and corroboration's
"two methods, same proposition" rule are the things that caught this program's
worst bugs — including forcing an optimistic single-method stability number to be
corroborated instead of shipped. The friction is at the operational edges, not the
core belief model.*
