"""Project / store path resolution for Terra map."""

from __future__ import annotations

from pathlib import Path

TERRA_DIRNAME = ".terra"
MAP_DIRNAME = "map"
PROBES_DIRNAME = "probes"
UNKNOWNS_DIRNAME = "unknowns"
RUNS_DIRNAME = "runs"
LIB_DIRNAME = "lib"
SUITES_DIRNAME = "suites"
KNOWNS_DIRNAME = "knowns"
# Legacy experimental capture store — not the product path (probes + unknowns + runs are)
DATA_DIRNAME = "data"


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk parents for a directory containing `.terra/`. None if missing."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / TERRA_DIRNAME).is_dir():
            return candidate
    return None


def terra_root(project_root: Path) -> Path:
    return project_root / TERRA_DIRNAME


def map_root(project_root: Path) -> Path:
    return terra_root(project_root) / MAP_DIRNAME


def probes_root(project_root: Path) -> Path:
    return map_root(project_root) / PROBES_DIRNAME


def probe_dir(project_root: Path, probe_id: str) -> Path:
    return probes_root(project_root) / probe_id


def unknowns_root(project_root: Path) -> Path:
    return map_root(project_root) / UNKNOWNS_DIRNAME


def unknown_path(project_root: Path, unknown_id: str) -> Path:
    return unknowns_root(project_root) / f"{unknown_id}.json"


def ensure_probes_store(project_root: Path) -> Path:
    """Create `.terra/map/probes` if needed; return probes root."""
    root = probes_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map probes\n\n"
            "Python instruments that survey the world.\n"
            "Create with `terra probe create <id> --purpose \"…\"`.\n"
            "Validate with `terra probe validate`.\n",
            encoding="utf-8",
        )
    return root


def ensure_unknowns_store(project_root: Path) -> Path:
    """Create `.terra/map/unknowns` if needed."""
    root = unknowns_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map unknowns\n\n"
            "Named gaps in understanding. Stuck → open an unknown (never silent).\n"
            "Create with `terra unknown create <id> --claim \"…\"`.\n",
            encoding="utf-8",
        )
    return root


def runs_root(project_root: Path) -> Path:
    return map_root(project_root) / RUNS_DIRNAME


def run_dir(project_root: Path, run_id: str) -> Path:
    return runs_root(project_root) / run_id


def map_lib_root(project_root: Path) -> Path:
    """Shared helpers for probes: `.terra/map/lib` (on sys.path during validate/run)."""
    return map_root(project_root) / LIB_DIRNAME


def ensure_runs_store(project_root: Path) -> Path:
    root = runs_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map runs\n\n"
            "Stamped readings from `terra probe run`.\n"
            "Each run has meta.json (time/from/to/status/artifacts) + artifacts/.\n",
            encoding="utf-8",
        )
    return root


def ensure_map_lib(project_root: Path) -> Path:
    root = map_lib_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    init = root / "__init__.py"
    if not init.exists():
        init.write_text(
            '"""Shared helpers importable by probes (on sys.path during validate/run)."""\n',
            encoding="utf-8",
        )
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map probe library\n\n"
            "Put shared Python modules here. Terra adds this directory to "
            "`sys.path` when validating or running probes.\n"
            "Import as top-level modules, e.g. `import rcon_client`.\n",
            encoding="utf-8",
        )
    return root


def suites_root(project_root: Path) -> Path:
    return map_root(project_root) / SUITES_DIRNAME


def suite_path(project_root: Path, suite_id: str) -> Path:
    return suites_root(project_root) / f"{suite_id}.json"


def ensure_suites_store(project_root: Path) -> Path:
    root = suites_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map suites\n\n"
            "Ordered probe recipes (composition, not domain plugins).\n"
            "Create with `terra suite create <id> --probes a,b,c`.\n"
            "Run with `terra suite run <id> --to '{…}'`.\n",
            encoding="utf-8",
        )
    return root


def knowns_root(project_root: Path) -> Path:
    return map_root(project_root) / KNOWNS_DIRNAME


def known_path(project_root: Path, known_id: str) -> Path:
    return knowns_root(project_root) / f"{known_id}.json"


def ensure_knowns_store(project_root: Path) -> Path:
    root = knowns_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map knowns (typed anchors)\n\n"
            "Beliefs with structure. First type: **number** (mean ± std from samples).\n"
            "Create with `terra known create <id> --type number --claim \"…\" --quantity q`.\n",
            encoding="utf-8",
        )
    return root


def ensure_map_store(project_root: Path) -> Path:
    """Create full map store."""
    ensure_probes_store(project_root)
    ensure_unknowns_store(project_root)
    ensure_knowns_store(project_root)
    ensure_runs_store(project_root)
    ensure_map_lib(project_root)
    ensure_suites_store(project_root)
    return map_root(project_root)


def require_project_root(start: Path | None = None) -> Path:
    root = find_project_root(start)
    if root is None:
        raise FileNotFoundError(
            "No .terra/ project found. "
            "`terra probe create` / `terra unknown create` auto-init, "
            "or run `terra init`."
        )
    return root


def ensure_project_root(start: Path | None = None) -> tuple[Path, bool]:
    """Return (project_root, created). Creates `.terra/map` in cwd if missing."""
    root = find_project_root(start)
    if root is not None:
        ensure_map_store(root)
        return root, False
    root = (start or Path.cwd()).resolve()
    ensure_map_store(root)
    return root, True


# --- legacy data paths (kept so old tests/import paths do not hard-crash) ---

def data_root(project_root: Path) -> Path:
    return map_root(project_root) / DATA_DIRNAME


def capture_dir(project_root: Path, capture_id: str) -> Path:
    return data_root(project_root) / capture_id


def ensure_data_store(project_root: Path) -> Path:
    root = data_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    return root
