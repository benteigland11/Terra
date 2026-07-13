# Adjusting the map (retract bad evidence)

Getting data **in** is not enough. A bad run, wrong link, or poisoned known
must be **retractable** before the next agent trusts the map.

## Preferred: void a run

Keeps audit trail; excludes from stats; cascade-unlinks by default.

```bash
terra run void <run_id> --reason "probe bug / wrong to / outlier"
# → voided=true on meta.json
# → unlinks from knowns + unknowns on active map
# → recomputes n/mean/rate (over-claimed confidence demotes)
```

```bash
terra run unvoid <run_id>   # clear flag only — re link-run if it should count
terra run delete <run_id>   # hard purge disk (prefer void)
```

`--no-cascade`: leave `run_ids` in place but still skip voided samples in stats.

## Surgical unlinks

```bash
terra known unlink-run <known_id> <run_id>
terra unknown unlink-run <unknown_id> <run_id>
```

Both recompute typed stats. Claimed confidence cannot stay above derived.

## Delete belief nodes

```bash
terra known delete <id>
terra unknown delete <id>
```

Only removes the record on the **active** map (session or global).  
Probes are global instruments — not deleted by these commands.

## Session isolation

Experiment mess → session map (`terra map create … --use`).  
Void/unlink there without touching global durable beliefs.

## Agent rule

If you discover a bad sample, **void or unlink before** promoting or building.
Leaving poisoned stats for the next agent is a process failure.
