# Map calculations

Calculations are the inside-map composition head. A probe brings observations
from outside into the map; a calculation combines values already admitted to
the map.

Every external input must be declared as `known:<id>` or `assumption:<id>`.
Unknowns, environment variables, files, imports, and network access are not
calculation inputs. Numeric and boolean literals are allowed as mathematical
logic—`(1 / 2) * m * v**2` is an ordinary calculation. Validation inventories
those literals in the result for transparency; it does not presume misuse.

```bash
terra calculation create area \
  --input width=known:width \
  --input height=assumption:working_height \
  --type number --quantity area --unit m2 --decimals 2
```

Edit `.terra/map/calculations/area/calc.py`:

```python
def calculate(inputs):
    return {"value": inputs["width"] * inputs["height"]}
```

Then run `terra calculation validate area`, `terra calculation run area`, and
`terra calculation get area`.

The stamped result records exact inputs, source maps, the source hash, and
calculation time. Changed input or source makes it stale; `get` refuses it
until rerun. Known-only results are clean. Any assumption makes the result
conditional and propagates its id.

`--decimals` is presentation metadata only. Terra preserves the full Python
result in `value` and adds a separate display envelope:

```json
{
  "value": 0.3333333333333333,
  "display": {
    "value": 0.33,
    "formatted": "0.33",
    "decimal_places": 2
  }
}
```

Calculations never round intermediate values automatically. If quantization is
part of the engineering logic (for example a 0.5 mm manufacturing increment),
perform it explicitly in `calculate(inputs)`.

The initial surface returns number or boolean values and does not consume other
calculations. Compound logic can live within one calculation while every leaf
value remains a known or assumption.

## Model profile

Use `profile=model` when one restricted expression is no longer enough:

```bash
terra calculation create trajectory --profile model \
  --input mass=known:mass --input velocity=assumption:velocity \
  --output energy=number:kinetic_energy:J \
  --output moving=boolean:is_moving
```

Model calculations use `calculate(inputs, ctx)`, may import standard or
installed Python packages and package-local helper modules, and return:

```python
def calculate(inputs, ctx):
    return {
        "outputs": {
            "energy": {"value": 0.5 * inputs["mass"] * inputs["velocity"] ** 2},
            "moving": {"value": inputs["velocity"] > 0},
        },
        "health": {"ok": True, "summary": "all declared checks passed"},
        "diagnostics": {"method": "closed_form", "finite": True},
        "artifacts": [{"path": "trajectory.csv", "role": "time_history"}],
    }
```

Output names must exactly match the declarations. Artifacts must exist inside
the calculation package and are stamped with size and SHA-256. The runtime
manifest records Python, platform, `requirements.txt`, installed dependency
versions, and the requirements hash. Missing declared requirements block
validation. Changes to `calc.py`, package-local Python helpers, requirements,
map inputs, installed dependency versions, Python/platform runtime, or stamped
artifact bytes stale the result. Missing artifacts stale it too.

Every model must return an explicit `health` object containing boolean `ok`.
Terra does not guess validity from arbitrary diagnostics: the model owns its
domain checks and sets `health.ok`. A false verdict and its optional `summary`
are preserved with the run for diagnosis, but the result is stale/non-composable
and blocks the gate. Non-finite numeric outputs are rejected regardless of the
verdict. Diagnostics remain unrestricted JSON evidence for explaining the
decision.
