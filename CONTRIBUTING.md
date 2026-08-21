# Contributing to Terra

Thanks for helping improve Terra.

## Development

Use Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
PYTHONPATH=.:src .venv/bin/python -m pytest -q
```

Keep agent-facing command output JSON-first, preserve the shared Cartograph
agent-CLI blueprint, and add focused regression coverage for behavior changes.

## Pull requests

- Keep one coherent purpose per change.
- Run the full test suite and `git diff --check`.
- Update the relevant user documentation when CLI behavior changes.
- Do not commit local `.terra/` map data, credentials, or build artifacts.

## Release checks

The release-readiness workflow builds both sdist and wheel, rebuilds from the
sdist, and runs the installed `terra` command in a blank virtual environment.
