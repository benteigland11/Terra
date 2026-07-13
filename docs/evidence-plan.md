# Evidence plans — above types

Plans are **not** a peer of `number` / `boolean`.

```text
probes  →  runs  →  knowns/unknowns (type = number|boolean)
                              ↑
                           plans   multi (all) | sequential (prove A then B)
```

| Layer | What it is |
| ----- | ---------- |
| **type** | Leaf filter: scalar samples → stats + ladder |
| **plan** | Dossier: several legs that *use* types |

Store: `.terra/map/plans/<id>.json` (scoped like knowns — active map).

## Modes

| Mode | Meaning |
| ---- | ------- |
| **`all`** | Multi-evidence: every leg required; **any order** |
| **`sequence`** | Prove leg 0, then 1, … — link blocked if prior open |

Each **leg** is number|boolean with its own `run_ids`, `min_n`, `min_confidence`.

## CLI

```bash
# Multi (any order)
terra plan create night_safe \
  --mode all \
  --claim "Night path is safe enough to build" \
  --leg rcon:boolean:rcon_up \
  --leg hostiles:number:hostile_count:n=3:conf=med

# Sequential (A then B)
terra plan create deploy_gate \
  --mode sequence \
  --claim "Reach server, then smoke" \
  --leg reach:boolean:rcon_up:conf=med \
  --leg smoke:boolean:smoke_ok:n=3:conf=med

terra plan link-run deploy_gate <run> --leg reach
terra plan link-run deploy_gate <run2> --leg smoke   # blocked until reach ok
terra plan show deploy_gate
terra plan promote deploy_gate med
```

Leg spec: `id:type:quantity[:n=N][:conf=low|med|high]`

## Rules

1. Plan promote needs **all legs satisfied**.  
2. Derived plan confidence = **min** of legs once complete.  
3. Sequence gates `link-run --leg`; does not invent samples.  
4. Void a bad run → cascade unlinks plan legs too.  
5. Scalar knowns stay for single-measure claims; plans for multi-facet surfaces.

## vs suite vs known

| | **suite** | **known** | **plan** |
| - | --------- | --------- | -------- |
| Layer | ops recipe | scalar belief | composition of legs |
| Type field | n/a | number\|boolean | none (role=plan) |
| Promote | n/a | sample ladder | all legs + min derived |
