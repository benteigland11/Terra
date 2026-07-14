# Relation type — F(x) as a known

Measured curves: CL vs alpha, thrust vs RPM, capacity vs temperature.

## Sampling

Probes emit ordinary measures with an `x` field; one sweep run emits many:

```python
'measures': [
  {'quantity': 'cl', 'x': 0.0, 'value': 0.10},
  {'quantity': 'cl', 'x': 4.0, 'value': 0.60},
  {'quantity': 'cl', 'x': 8.0, 'value': 1.05},
]
```

## Declare + graduate (same survey loop)

```bash
terra unknown create u_cl --type relation --quantity cl \
  --x-quantity alpha_deg --x-unit deg \
  --claim "CL(alpha)?" --evidence "vlm sweeps" --within 10%
terra unknown link-run u_cl <sweep_run>   # repeat the sweep
terra unknown graduate u_cl --as cl_vs_alpha
```

Stats aggregate per **x-station** (exact x match — share a sweep grid):
each station has its own n/mean/std, plus `x_range`, station and sweep counts.

## Ladder — the unit is sweeps, not points

One dense sweep is a single observation of the curve.

| Level | Bar |
| ----- | --- |
| med | ≥3 sweeps AND ≥3 stations |
| high | ≥5 sweeps, ≥3 stations, tight stations, ≥2 methods agreeing |

## Evaluation

```bash
terra known get cl_vs_alpha --at 4.2 --raw   # linear interp between station means
terra known get cl_vs_alpha                  # full station table
```

```python
from terra.readings import known
CL = known("cl_vs_alpha", at=4.2)["value"]
```

Reads outside the measured `x_range` fail loudly — **no extrapolation**;
run a sweep that covers the x you need.

## Corroboration

Per-method curves compared at **shared stations** (≥2 required to judge —
disjoint grids are not evidence either way). Agree iff every shared station
is within tolerance; spread reported is the worst station. Two tools
disagreeing only post-stall shows up as exactly that. `accept-spread`
applies unchanged.
