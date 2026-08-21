# Terra

Terra is an evidence-backed design workspace for agents and engineers. It
combines a design brief, a route DAG, and a map of unknowns, assumptions,
measurements, calculations, and validated knowns. Its CLI is JSON-first so an
agent can act on explicit attention and next actions instead of scraping prose.

## What it provides

- **Map and evidence:** unknowns, assumptions, typed knowns, probes, runs,
  calculations, corroboration, staleness, and retraction.
- **Program control:** briefs, budgeted routes, priorities, phases, and gates.
- **Design of record:** promote validated beliefs into a baseline and detect
  drift in the artifacts that depend on them.
- **Agent-safe CLI:** structured JSON envelopes by default, with human views
  available through `--human`.

## Install

Terra requires Python 3.11 or newer. Until a package-index release is
announced, install from a clone:

```bash
git clone https://github.com/benteigland11/Terra.git
cd Terra
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/terra --version
```

For development, replace the install command with
`.venv/bin/python -m pip install -e .`.

## Quick start

Run this in the project directory whose work you want to survey:

```bash
terra init
terra map status
terra map status --human

terra unknown create mass_gap --type number --quantity mass_kg \
  --claim "What is the assembled mass?" \
  --evidence "Measured assembly mass from a stamped probe run"

terra probe create weigh_assembly --purpose "Measure assembled mass" --kind watch
terra unknown link-probe mass_gap weigh_assembly
terra probe validate weigh_assembly
```

Edit the generated `.terra/map/probes/weigh_assembly/probe.py`, run it with
`terra probe run`, link its run to the unknown, then graduate the unknown into
a known when the evidence is sufficient. `terra map status` returns an agent
envelope containing `data.attention` and `data.next_actions` throughout.

## Core workflow

| Need | Command family |
| --- | --- |
| Create or inspect a project map | `terra init`, `terra map` |
| Name an unanswered question | `terra unknown` |
| Record a provisional value | `terra assumption` |
| Build and run an instrument | `terra probe`, `terra run` |
| Derive a result from map inputs | `terra calculation` |
| Turn evidence into a durable belief | `terra unknown graduate`, `terra known` |
| Check whether work is safe to proceed | `terra gate`, `terra sitrep` |
| Plan and track program work | `terra brief`, `terra route` |
| Maintain a validated design baseline | `terra design` |

Map state lives in `.terra/` within the surveyed project and is intentionally
ignored by Git. Use session maps for experiments and promote only validated
beliefs to the global map.

## Agent I/O

The default response for agent-facing commands is a JSON envelope:

```json
{
  "status": "success",
  "data": { "attention": [], "next_actions": [] }
}
```

Human-oriented output is opt-in (`--human`). See
[agent I/O](docs/agent-io.md) and [map scopes](docs/maps.md) for the contract
and multi-map behavior.

## Documentation

- [Unknowns](docs/unknowns.md), [assumptions](docs/assumptions.md), and
  [known graph](docs/known-graph.md)
- [Probe inputs](docs/probe-inputs.md), [probe validation](docs/probe-level1.md),
  and [calculations](docs/calculations.md)
- [Evidence plans](docs/evidence-plan.md), [corroboration](docs/corroboration.md),
  and [design baselines](docs/design.md)
- [Briefs and routes](docs/brief-route.md)

## Development and release checks

```bash
PYTHONPATH=.:src python -m pytest -q
git diff --check
python -m build --sdist --wheel --outdir dist
```

The CI workflow also rebuilds from the sdist and runs the installed wheel in a
blank virtual environment. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[SECURITY.md](SECURITY.md).

## License

Terra is licensed under the [Apache License 2.0](LICENSE).
