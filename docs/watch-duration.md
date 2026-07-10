# Watch duration — one model

**Decision: the probe owns the watch window.**  
The substrate does **not** re-invoke `run()` in a loop.

| `kind` + `duration_s` | Meaning |
| --------------------- | ------- |
| `watch` + `0` | **Snapshot** — single shot, return ASAP |
| `watch` + `N` (`N > 0`) | **Window** — probe polls/listens until deadline (~N seconds) |
| `run` | No duration; drive once (omit `duration_s`) |

## Why not substrate loops?

Re-calling `run()` N times implies independent surveys and broken state (open RCON, subscriptions).  
One stamp = one window. The instrument holds the connection and samples until time is up.

## What the substrate injects into `ctx`

On every live/design run of a `kind=watch` probe:

```python
ctx["duration_s"]   # float, from probe.json (0 = snapshot)
ctx["watch_mode"]   # "snapshot" | "window"
# only when duration_s > 0 and not dry_run / not level1:
ctx["deadline"]       # ISO-8601 UTC absolute deadline
ctx["deadline_unix"]  # float epoch seconds (easy for time.time() loops)
```

Also always:

```python
ctx["to"]
ctx["dry_run"]          # if design/dry
ctx["_terra_validation"]  # "level1" during validate only
```

**Timeout:** process kill limit is `max(cli_timeout, duration_s + 5)` so the probe can use the full window.

## Probe duties

```python
def run(ctx=None):
    ctx = ctx or {}
    to = ctx["to"]
    if ctx.get("dry_run") or ctx.get("_terra_validation") == "level1":
        return {"to": to, "status": "ok", "artifacts": []}  # no wait

    mode = ctx.get("watch_mode") or "snapshot"
    if mode == "snapshot" or float(ctx.get("duration_s") or 0) <= 0:
        # one reading
        ...
        return {"to": to, "status": "ok", "artifacts": [...]}

    # window: poll until deadline (probe owns the loop)
    import time
    deadline = float(ctx["deadline_unix"])
    readings = []
    while time.time() < deadline:
        readings.append(sample(to))  # domain-specific
        time.sleep(poll_interval)
    ...
    return {"to": to, "status": "ok", "artifacts": [...]}
```

## What Terra does **not** do

- Does not call `run()` repeatedly  
- Does not sleep for `duration_s` on behalf of the probe  
- Does not invent sampling intervals  

## Soft guardrail

If `watch_mode=window`, not dry_run, and wall time ≪ `duration_s`, the run stamp gets a **warning** (does not fail): probe likely ignored the window.

## Level-1 validate

Always **single shot** with `dry_run` / `_terra_validation=level1`.  
Duration metadata is checked for declaration match only — validate never waits N seconds.
