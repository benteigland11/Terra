# Probe validation — level 1

**Bare minimum contract** (what every probe must honor):

| Side | Field | Owner |
| ---- | ----- | ----- |
| **Input** | `to` | Probe — what we point at |
| **Output** | `to`, `status`, `artifacts` | Probe |
| **Stamp** | `time`, `from` | Substrate on **run** |

## Watch duration (one model)

**Probe owns the window.** Substrate does not re-invoke `run()` in a loop.

See [watch-duration.md](watch-duration.md).

| Metadata | Live `ctx` | Probe duty |
| -------- | ---------- | ---------- |
| `watch` + `duration_s=0` | `watch_mode=snapshot` | Single shot |
| `watch` + `duration_s=N` | `watch_mode=window`, `deadline`, `deadline_unix` | Poll until deadline |
| level-1 / dry_run | `dry_run` / `_terra_validation`; no waiting | Return immediately |

## What `terra probe validate` does (level 1)

1. Package / script shape  
2. `REQUIRED_EXPORTS` + `KIND` (+ `DURATION_S` for watch) match meta  
3. I/O exercise with dry_run (never waits a window):

| Step | Check |
| ---- | ----- |
| **INPUT** | non-empty `to` |
| **EXECUTE** | `run(ctx)` accepts ctx |
| **OUTPUT** | `{to, status, artifacts}` shape |

## Recommended `to`

See [to-schema.md](to-schema.md). Warn-only on live runs if `kind` missing.
