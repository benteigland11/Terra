# Known graph — read path, dependencies, staleness, gate

The map is a graph, not a ledger. Three mechanisms keep it honest:

1. **Read path** — knowns are consumed, never copied
2. **Deps + staleness** — when a source moves, dependents go red
3. **Gate** — debt mechanically fails release

## 1. Read path (`terra known get` / `terra.readings`)

A number lives in exactly one place: its known. Probes, sheet generators,
and models **import** it — hardcoded copies are the drift disease.

```bash
terra known get mtow                 # reading JSON (value, unit, conf, n, stale)
terra known get mtow --raw           # bare value, shell-able
terra known get mtow --min-conf med  # refuse below med confidence
```

```python
# inside a probe or tool (project cwd):
from terra.readings import known
MTOW = known("mtow")["value"]        # loud if missing/unbacked/stale/low-conf
```

Reads are **loud by default**: missing, unbacked (n=0), stale, or below
`min_conf` all fail. `--allow-stale` exists but is recorded in the reading.

Every read stamps a **consumer edge** (`.terra/map/consumers/<id>.json`).
Identity: explicit `--consumer` / kwarg > probe context (`probe:<id>`, set
automatically by `terra probe run`) > `TERRA_CONSUMER` env > `tool:<argv0>`.
Tools shelling out should set `TERRA_CONSUMER` so the edge names them.

## 2. Dependencies + staleness

```bash
terra known depend cg_pos --on file:geometry/airframe.stl --on known:mtow
```

File deps stamp sha256 now; known deps stamp the upstream `updated_at`
(`as_of`). Staleness is **computed at status time, never stored**:

| Condition | Result |
| --------- | ------ |
| file sha256 changed / missing | stale |
| upstream known updated after `as_of` | stale |
| upstream known stale | stale (cascade) |
| dependency cycle | stale (loud) |

Stale knowns: refuse `known get`, show `known_stale` attention in
`terra map status`, and fail the gate.

Freshness returns only by honest re-derivation:

```bash
terra probe run … && terra known link-run cg_pos <run_id>   # re-derive
terra known reaffirm cg_pos --reason "reloft doesn't move CG"  # verified unchanged
```

Both refresh the dep stamps; reaffirm keeps a trail in `record.reaffirmed`.

## 3. Gate (`terra gate`)

Mechanical, CI-able: exit 0 iff clean, exit 1 with the violation list.
Default scans **every map** — session debt cannot hide.

```bash
terra gate            # agent envelope + exit code
terra gate --human
terra gate --map global
```

Violations: `unknown_blocking` (active + blocks_build), `known_unbacked`,
`known_stale`, `plan_incomplete`.

Route integration: `terra route complete` on a **deliverable** task
(skill or role) runs the gate and refuses on failure. Override is explicit
and recorded:

```bash
terra route complete ship --skip-gate "demo build; debt tracked in route"
```
