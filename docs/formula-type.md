# Map type: `formula`

**Observation = formula + vars.** A checkable predicate over probe measures —
not freeform prose.

## Idea

```text
claim + expression + vars{name → quantity} + run_ids
  → substrate evaluates → holds, holds_rate, bindings, by_run
```

Agents own the expression and var bindings. Terra recomputes stats.

## Example

```bash
terra unknown create sparse_night \
  --type formula \
  --claim "Night hostiles in R stay low?" \
  --expression "mean(h) <= 10 and n(h) >= 3" \
  --var h=hostile_count \
  --evidence "repeated probe measures"

terra unknown link-run sparse_night <run_id>
terra unknown graduate sparse_night   # → known; resolves the unknown

terra known link-run sparse_night <run2>
terra known show sparse_night
terra known promote sparse_night med   # blocks if formula does not hold / n too small
```

Probe still returns open measures:

```python
"measures": [{"quantity": "hostile_count", "value": 4}]
```

## Expression (allowlist)

| | |
| - | - |
| **aggs** | `mean(v)` `min(v)` `max(v)` `std(v)` `n(v)` `sum(v)` `rate(v)` |
| **ops** | `+ - * /`  `and` `or` `not`  `<= >= < > == !=` |
| **vars** | bound via `--var name=quantity[:number\|boolean]` |

No arbitrary Python, imports, or attribute access.

## Confidence ladder

| derived | when |
| ------- | ---- |
| **low** | n≥1 evaluable |
| **med** | n≥3 |
| **high** | n≥5 |

Confidence describes confidence in the verdict, not whether the verdict is
favorable. A failed formula can therefore be high confidence. A formula known
with `holds: false` fails `terra gate` until new evidence makes it hold or the
belief is retired/replaced. `terra map status` exposes this as
`verdict: "fail"` plus blocking `known_formula_failed` attention and a
`known.show` next action, so agents see the negative result without first
running the release gate.

## Stack

| Type | Job |
| ---- | --- |
| number / boolean | estimate |
| **formula** | observation / gate (holds?) |
| plan | multi / sequence composition |

Voided runs are skipped (same as other types).
