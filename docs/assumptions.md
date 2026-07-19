# Map assumptions

Assumptions are typed provisional values that let work continue without
pretending the value is known. They occupy the middle state deliberately:

- an **unknown** has no usable value and always blocks the gate;
- an **assumption** has a usable value, but every read is conditional;
- a **known** is born from linked evidence, never from the assumed value.

Assumptions live in the active map's `unknowns/` store with
`role: "assumption"`. This keeps the evidence and graduation lifecycle shared
without adding a third execution system.

## CLI

```bash
terra assumption create radiator_emissivity \
  --type number --quantity radiator_emissivity --value 0.85 --unit 1 \
  --claim "What emissivity will the flight coating sustain?" \
  --reason "Working beginning-of-life coating basis" \
  --evidence "Vendor thermal-vacuum data across the operating range"

terra assumption get radiator_emissivity
terra assumption set radiator_emissivity --value 0.78 \
  --reason "Use the conservative end-of-life basis"
terra assumption link-probe radiator_emissivity coating_test
terra assumption link-run radiator_emissivity <run_id>
terra assumption show radiator_emissivity
terra assumption graduate radiator_emissivity
```

`get` returns the provisional value together with `conditional: true` and an
`assumptions` list. `set` requires a reason and preserves every revision.
Linked evidence is displayed beside the assumed value; it does not silently
replace it. Graduation requires live linked evidence and derives the known
from that evidence.

Active assumptions appear in `terra map status` and as non-blocking notices in
`terra gate`. Active unknowns always fail the gate, including legacy records
that contain `blocks_build: false`; convert that intent into an explicit
assumption instead.
