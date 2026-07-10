# Probe design workflow — v0 scope

**Status:** scope lock (build next, not built yet)  
**Layer:** Map (instruments + readings), above Cartograph, below Terra route  
**Lesson:** validation beats markdown; automate provenance; **force probe-building**, don’t funnel domains

---

## One-sentence goal

Give agents a **Python-only probe design + validation bar** so that under fog they **build an instrument**, run it, and produce **stamped evidence** (time, from, to, artifacts) — not freehand the domain.

---

## In scope (v0)

### 1. Python probes only

- Probe implementation language: **Python 3.11+**
- No JS/Java/OpenSCAD probe runners in v0
- A probe *may shell out* to other tools (gradle, game server CLI, etc.) — the **probe wrapper** is still Python

### 2. Probe as a first-class object (not ad-hoc shell)

A probe is a small, re-runnable instrument with:

| Field | Required | Meaning |
| ----- | -------- | ------- |
| `id` / name | yes | Stable slug (directory or module name) |
| `purpose` | yes | One sentence: what mystery this reduces |
| `entry` | yes | How to invoke (module/callable or `python path`) |
| implementation | yes | Python source under a fixed layout |

**Not in v0:** multi-file packages beyond a simple layout, probe “registry cloud”, non-Python bodies.

### 3. Design workflow (the product behavior)

Forced loop, not optional guidance:

```text
1. Name the mystery (purpose)     — what are we trying to learn?
2. Design the probe               — Python instrument that can ask the world
3. Validate the probe             — contract bar (below); must pass before "done designing"
4. Run the probe                  — execute against a target
5. Stamp the run                  — automated provenance + artifacts
6. Validate the run               — evidence bar; only then is it map data
```

v0 **builds 1–6 for Python**. Unknown/anchor graph can wait; purpose text is enough to start.

### 4. Validation bar — probe (design-time)

A probe **passes design validation** only if:

1. Layout and metadata present (exact layout TBD in implement pass; see proposed layout)
2. `purpose` non-empty
3. Entry point importable / runnable under the runner
4. Probe declares or implements a **run contract** that can emit required provenance fields (see exports)
5. Probe is deterministic enough to re-run (no interactive prompts; no required network unless explicitly flagged later — v0: local only preferred)
6. Soft timeout bound (e.g. design-time “dry” or run-time cap — exact numbers in implement)

**Fails design validation → not a probe.** Fix the instrument.

### 5. Validation bar — run (evidence-time)

A run **passes** only if:

1. Linked to a probe that itself would pass design validation (or is stamped at last validate)
2. Required **exports** present and well-formed (below)
3. At least one artifact (stdout, file path listed, etc.) with integrity (hash / non-empty rules as appropriate)
4. Exit / status recorded
5. Automated **when** and host-side provenance filled by the substrate (agent does not hand-write these)

**Fails run validation → not map data.** Re-run or fix probe.

### 6. Required exports (the hard contract)

Every **successful validation of a run** must expose at least:

| Export | Who fills it | Meaning |
| ------ | ------------ | ------- |
| **time** (`captured_at` / `started_at` + `finished_at`) | **substrate** (automate) | When the reading happened |
| **from** | probe and/or substrate | Where the reading came from (probe id, command, cwd, runner, host fingerprint) |
| **to** | **probe** (required claim) | What was targeted / asked (region, path, URL, server, query, scope) |
| **status** | substrate + probe | exit code / ok / error summary |
| **artifacts** | probe + substrate | Evidence bytes (paths relative to run dir) |

#### `from` / `to` semantics (v0)

- **`from`**: the instrument + execution context  
  - always includes: `probe_id`, runner (`python`), cwd, env fingerprint, argv  
  - may include: subprocess command the probe used  

- **`to`**: the **subject of the survey** (what we pointed the instrument at)  
  - freeform structured object, but **must be non-empty**  
  - examples (not product features): `{ "kind": "path", "path": "…" }`, `{ "kind": "region", "x":… }`, `{ "kind": "process", "pid":… }`  
  - probe **must set `to`** in its result payload; substrate does not invent domain targets  

**Law:** automate **time** and execution **from**; require the probe to name **to**.  
Interpretation (“so blocks work like X”) is still **not** automated.

### 7. Proposed layout (implement detail, directionally locked)

```text
.terra/map/
  probes/
    <probe_id>/
      probe.json          # id, purpose, entry, schema_version
      probe.py            # implementation
  runs/
    <run_id>/
      meta.json           # time, from, to, status, artifacts, probe_id
      …artifacts…
```

(Names can shift slightly at implement; the split **probe vs run** is locked.)

### 8. CLI surface (minimal)

```text
terra probe create <id> --purpose "…"
terra probe validate [<id>|--all]
terra probe run <id> [--to JSON or key=val]   # to may also be set inside probe
terra probe list
terra run validate [<run_id>|--all]
terra run show <run_id>
```

Exact flags flexible; **init → validate → run → validate run** is locked.

### 9. Agent-facing workflow (what we force)

Under uncertainty / “need to understand the world”:

1. `probe create` with a clear purpose (or edit purpose first)  
2. Implement `probe.py` to query **to** and write artifacts  
3. `probe validate` must pass  
4. `probe run` → substrate stamps time/from; probe supplies to + artifacts  
5. `run validate` must pass  
6. Only then treat evidence as real for coding decisions  

No domain funnels (no first-class “Minecraft block probe” type in the product).

---

## Out of scope (v0)

| Item | Why later |
| ---- | --------- |
| Non-Python probe bodies | Explicit v0 cut |
| Unknown / anchor graph | Req 1–2; runs should be enough substrate first |
| Auto-interpretation of artifacts into anchors | Judgment, not infrastructure |
| Domain-specific funnels (Minecraft, etc.) | Agent builds those probes |
| Cartograph checkin of probes as widgets | Nice later; project-local probes first |
| Terra phases / gantt / goals | Route layer |
| Cloud sync, multi-user | Me-first |
| Network-required probes as first-class | Prefer local; revisit |
| Rich UI / Gantt | Not this layer |

---

## Non-goals (sharp edges)

- **Not** a general command logger (that’s a degenerate case; probe is the hero)  
- **Not** “we support every domain” via adapters  
- **Not** soft README-only probe docs without validate  
- **Not** allowing empty `to` (“surveyed nothing”) to pass  

---

## Success criteria (v0 done when)

1. You can design a Python probe with purpose + entry and **fail validate** when contract broken  
2. You can run it and get a run record with **time**, **from**, **to**, **artifacts** without hand-writing provenance  
3. Invalid runs do not count as map data (`run validate` fails)  
4. A second agent/session can re-read `runs/<id>` and know when/from/to without chat  
5. Dogfood: one real opaque domain (e.g. mod/server peek) implemented as a **project probe**, not a Terra feature  

---

## Open decisions (resolve at implement, defaults below)

| Topic | Default unless you override |
| ----- | --------------------------- |
| How probe returns `to` + artifacts | Python: print final JSON on stdout **or** write `result.json` — pick one in implement and stick to it |
| `to` on CLI vs only in probe | Both: CLI can pass target; probe may override/enrich; final `to` in meta must be non-empty |
| Probe dry-run at validate | Prefer import + signature/contract check; full run optional via `validate --run` |
| Store root | `.terra/map/probes` + `.terra/map/runs` under project |

---

## Relationship to earlier “data capture” sketch

- **Keep:** automate **when** + execution context; hash/integrity; on-disk store; validate hard bar  
- **Demote:** naked “capture any command” as the hero path  
- **Elevate:** **probe design workflow** + **run of a probe** as the unit  

Ad-hoc command capture can later be “anonymous probe” if needed; not v0 priority.

---

## Build order (after scope lock)

1. Probe package layout + `probe.json` schema  
2. `probe validate` (design bar)  
3. Runner + required export schema (`time`, `from`, `to`, artifacts)  
4. `run validate`  
5. Thin CLI  
6. Dogfood one real probe in a real project  

---

## Lock line

> **v0 = Python probes only, forced design→validate→run, every run exports time / from / to / artifacts under a hard bar. No domain funnels. No unknowns/anchors yet.**
