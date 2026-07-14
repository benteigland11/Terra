# Design layer — the validated baseline files link to

The evidence ladder ends here:

```
probe run → unknown → graduate → known → promote → **design param** → attached artifacts
```

`.terra/design.json` is project-wide (like brief/route) and sourced only from
the **global** map — session experiments never become design.

## Admit knowns (design params)

```bash
terra design add mtow                    # live link, not a copy
terra design add cg_pos --as cg_percent_mac
```

Admission bar: global-map known, confidence ≥ **med**, backed, methods not
disagreeing, not stale. The param pins the value + the known's `updated_at`.
If the known later moves, degrades, or goes stale, the param goes **red**
(design check + gate) — never silently updated. After reviewing a legitimate
move: `terra design refresh <param>` re-pins (bar re-checked).

## The design card + read path

```bash
terra design show --human      # every param: value, confidence, health
terra design get mtow --raw    # generators read THE value (min-conf med, consumer stamped)
```

## Attach deliverable files

```bash
terra design attach prints/three_view.pdf --uses mtow,cg_pos
terra design attach geometry/airframe.stl --uses wing_area,mtow
```

Attach stamps the file sha256 + each used param's pin. `terra design check`
(exit 1) and `terra gate` go red when:

| Condition | Message |
| --------- | ------- |
| used param moved after stamp | REGENERATE this file |
| file changed without re-attach | unregistered edit |
| file missing | broken deliverable |

Regenerate the file, `design attach` again — green.

## The false-fresh chain, closed

Reloft the wing → `wing_area`'s file dep stale → known red → design param
red → every attached print/STL flagged for regen → gate refuses release
until the whole chain is green. Stale sheets cannot ship silently.
