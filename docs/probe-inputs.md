# Declared probe inputs

Probes may consume map values when those values configure how the instrument
observes or drives the outside world. Declare each dependency in `probe.json`:

```json
{
  "inputs": {
    "calibration": "known:sensor_calibration",
    "ambient": "assumption:ambient_temperature"
  }
}
```

Or scaffold them directly:

```bash
terra probe create sensor --purpose "Read the calibrated sensor" \
  --input calibration=known:sensor_calibration \
  --input ambient=assumption:ambient_temperature
```

The runner resolves inputs and injects only their current values:

```python
def run(ctx=None):
    inputs = ctx["inputs"]
    return measure(inputs["calibration"], inputs["ambient"])
```

Every run stamps the bindings, resolved values, source maps and timestamps,
probe source hash, conditional flag, and transitive assumption ids. If a
declared map input changes, the historical run remains auditable but is stale
for current use. Known reads and the release gate refuse evidence with stale
inputs until the probe is rerun. A changed probe source does not rewrite or
invalidate historical observations; its stamped hash identifies which
instrument version produced each run.

Assumption-conditioned evidence may graduate, but the known remains explicitly
conditional and carries those assumptions into downstream probes and
calculations. Clean evidence replacing it removes the contamination.

Do not use this mechanism to disguise deterministic map-to-map logic as an
instrument. If there is no outside authority being sensed or driven, use a
calculation instead.
