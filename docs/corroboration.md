# Corroboration — the second evidence axis

There are two ways to prove something:

| Axis | Mechanism | Catches | Terra surface |
| ---- | --------- | ------- | ------------- |
| **Repetition** | same probe, more runs | noise (precision) | n-ladder (n≥3 med, n≥5 high-eligible) |
| **Corroboration** | different probes, same answer | systematic error (truth) | per-probe stats + tolerance |

Five runs of one biased instrument agree with each other perfectly and are
still wrong. That's why:

- **`high` requires ≥2 independent probes agreeing.** Single-method knowns
  cap at `med` no matter how many runs.
- **Disagreement is louder than absence.** Methods outside tolerance means
  one instrument is lying: derived confidence collapses to `low`, promote
  (med and high) blocks, `known get` refuses (`--allow-disagree` escape,
  recorded), `methods_disagree` fails the gate and shows in attention.

## Mechanics

Every linked run already carries its `probe_id`; recompute groups samples
per probe into `stats.by_probe` and judges `stats.corroboration`:

```json
"corroboration": {"methods": 2, "tolerance": "5%", "spread": 2.5, "agree": false}
```

- **numbers**: per-probe means within tolerance — relative (`5%`) or
  absolute (`0.5`). No tolerance declared → spread surfaced, not judged
  (`agree: null`), and high stays blocked until you declare one.
- **booleans**: per-probe majority verdicts must match (no tolerance needed).
- **formula**: n/a — corroborate the underlying quantities.

## CLI

```bash
terra unknown create cg --type number --quantity cg_mac \
  --claim "CG at %MAC?" --evidence "CAD + sheet buildup" --within 5%
# link runs from BOTH probes, graduate as usual

terra known tolerance cg --within 5%     # declare/adjust later (re-judges)
terra known show cg                      # per-method stats + verdict
terra known promote cg high              # needs 2+ agreeing methods
```

`known graph` marks multi-method nodes: `2 methods ✓` / `2 methods ✗ DISAGREE`.

## Resolving a disagreement

The 8%-MAC playbook: `known show` compares per-probe means; find the lying
instrument; `terra run void <bad_runs> --reason "…"` (or fix the probe and
re-run); link corrected runs. Agreement recomputes automatically.
