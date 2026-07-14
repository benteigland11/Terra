"""Project / store path resolution for Terra.

Program layer (project-wide, not map-scoped):
  - **brief** `.terra/brief.json` — SSOT design request
  - **route** `.terra/route.json` — task DAG for the main agent

Map layer:
  - **global** map: `.terra/map/` — durable beliefs + shared probes/lib
  - **session** maps: `.terra/map/sessions/<id>/` — experiment-scoped beliefs

Probes/lib always global. Beliefs use the **active** map.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERRA_DIRNAME = ".terra"
MAP_DIRNAME = "map"
SESSIONS_DIRNAME = "sessions"
PROBES_DIRNAME = "probes"
UNKNOWNS_DIRNAME = "unknowns"
RUNS_DIRNAME = "runs"
LIB_DIRNAME = "lib"
SUITES_DIRNAME = "suites"
KNOWNS_DIRNAME = "knowns"
PLANS_DIRNAME = "plans"
DATA_DIRNAME = "data"
ACTIVE_MAP_FILENAME = "active_map"
MAP_META_NAME = "map.json"
GLOBAL_MAP_ID = "global"
BRIEF_FILENAME = "brief.json"
ROUTE_FILENAME = "route.json"

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Per-invocation override (CLI --map); falls back to file / env / global
_active_map_id: ContextVar[str | None] = ContextVar("terra_active_map_id", default=None)


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk parents for a directory containing `.terra/`. None if missing."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / TERRA_DIRNAME).is_dir():
            return candidate
    return None


def terra_root(project_root: Path) -> Path:
    return project_root / TERRA_DIRNAME


def brief_path(project_root: Path) -> Path:
    """SSOT design request (project-wide)."""
    return terra_root(project_root) / BRIEF_FILENAME


def route_path(project_root: Path) -> Path:
    """Task DAG / Gantt source for the main agent (project-wide)."""
    return terra_root(project_root) / ROUTE_FILENAME


def set_active_map_id(map_id: str | None) -> None:
    """Set active map for this context (CLI --map). None clears override."""
    _active_map_id.set(map_id)


@contextmanager
def scoped_map(map_id: str):
    """Pin the active map for a with-block (multi-map scans)."""
    token = _active_map_id.set(_normalize_map_id(map_id))
    try:
        yield
    finally:
        _active_map_id.reset(token)


def get_active_map_id(project_root: Path | None = None) -> str:
    """Resolve active map: CLI context → TERRA_MAP env → .terra/active_map → global."""
    override = _active_map_id.get()
    if override:
        return _normalize_map_id(override)
    env = os.environ.get("TERRA_MAP", "").strip()
    if env:
        return _normalize_map_id(env)
    if project_root is not None:
        active_file = terra_root(project_root) / ACTIVE_MAP_FILENAME
        if active_file.is_file():
            try:
                text = active_file.read_text(encoding="utf-8").strip()
                if text:
                    return _normalize_map_id(text.splitlines()[0].strip())
            except OSError:
                pass
    return GLOBAL_MAP_ID


def _normalize_map_id(map_id: str) -> str:
    mid = map_id.strip()
    if not mid or mid == GLOBAL_MAP_ID:
        return GLOBAL_MAP_ID
    if not _SLUG_RE.match(mid):
        raise ValueError(
            f"map id {map_id!r} must be 'global' or a slug (a-z, then a-z0-9_)"
        )
    return mid


def global_map_root(project_root: Path) -> Path:
    """Always `.terra/map` — shared instruments live here."""
    return terra_root(project_root) / MAP_DIRNAME


def sessions_root(project_root: Path) -> Path:
    return global_map_root(project_root) / SESSIONS_DIRNAME


def map_root(project_root: Path, map_id: str | None = None) -> Path:
    """Belief/evidence root for the active (or given) map."""
    mid = _normalize_map_id(map_id) if map_id else get_active_map_id(project_root)
    if mid == GLOBAL_MAP_ID:
        return global_map_root(project_root)
    return sessions_root(project_root) / mid


def probes_root(project_root: Path) -> Path:
    """Probes are always global (shared instruments)."""
    return global_map_root(project_root) / PROBES_DIRNAME


def probe_dir(project_root: Path, probe_id: str) -> Path:
    return probes_root(project_root) / probe_id


def map_lib_root(project_root: Path) -> Path:
    """Shared helpers always global."""
    return global_map_root(project_root) / LIB_DIRNAME


def unknowns_root(project_root: Path) -> Path:
    return map_root(project_root) / UNKNOWNS_DIRNAME


def unknown_path(project_root: Path, unknown_id: str) -> Path:
    return unknowns_root(project_root) / f"{unknown_id}.json"


def knowns_root(project_root: Path) -> Path:
    return map_root(project_root) / KNOWNS_DIRNAME


def known_path(project_root: Path, known_id: str) -> Path:
    return knowns_root(project_root) / f"{known_id}.json"


def consumers_root(project_root: Path) -> Path:
    """Consumption edges: who read which known (map-scoped, like knowns)."""
    return map_root(project_root) / "consumers"


def consumer_path(project_root: Path, known_id: str) -> Path:
    return consumers_root(project_root) / f"{known_id}.json"


def ensure_consumers_store(project_root: Path) -> Path:
    root = consumers_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def runs_root(project_root: Path) -> Path:
    return map_root(project_root) / RUNS_DIRNAME


def run_dir(project_root: Path, run_id: str) -> Path:
    return runs_root(project_root) / run_id


def suites_root(project_root: Path) -> Path:
    return map_root(project_root) / SUITES_DIRNAME


def suite_path(project_root: Path, suite_id: str) -> Path:
    return suites_root(project_root) / f"{suite_id}.json"


def plans_root(project_root: Path) -> Path:
    """Evidence plans sit *above* typed knowns (multi/sequence dossiers)."""
    return map_root(project_root) / PLANS_DIRNAME


def plan_path(project_root: Path, plan_id: str) -> Path:
    return plans_root(project_root) / f"{plan_id}.json"


def ensure_probes_store(project_root: Path) -> Path:
    root = probes_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map probes (global)\n\n"
            "Shared instruments for the whole project.\n"
            "`terra probe create <id> --purpose \"…\"`\n",
            encoding="utf-8",
        )
    return root


def ensure_map_lib(project_root: Path) -> Path:
    root = map_lib_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    init = root / "__init__.py"
    if not init.exists():
        init.write_text(
            '"""Shared helpers importable by probes (global map lib)."""\n',
            encoding="utf-8",
        )
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map probe library (global)\n\n"
            "Shared across all maps/sessions.\n",
            encoding="utf-8",
        )
    return root


def ensure_unknowns_store(project_root: Path) -> Path:
    root = unknowns_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map unknowns (this map scope)\n\n"
            "Named gaps. Scoped to global or a session map.\n",
            encoding="utf-8",
        )
    return root


def ensure_knowns_store(project_root: Path) -> Path:
    root = knowns_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map knowns (this map scope)\n\n"
            "Typed anchors. Scoped to global or a session map.\n",
            encoding="utf-8",
        )
    return root


def ensure_runs_store(project_root: Path) -> Path:
    root = runs_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map runs (this map scope)\n\n"
            "Stamped readings. Session maps keep experiment runs out of global.\n",
            encoding="utf-8",
        )
    return root


def ensure_suites_store(project_root: Path) -> Path:
    root = suites_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map suites (this map scope)\n\n"
            "Ordered probe recipes for this map.\n",
            encoding="utf-8",
        )
    return root


def ensure_plans_store(project_root: Path) -> Path:
    root = plans_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Map evidence plans (this map scope)\n\n"
            "Above typed knowns: multi-evidence (all) and sequential (prove A then B).\n"
            "Legs use scalar types (number|boolean); the plan is the dossier.\n",
            encoding="utf-8",
        )
    return root


def ensure_belief_store(project_root: Path) -> Path:
    """Unknowns/knowns/runs/suites/plans for the **active** map."""
    ensure_unknowns_store(project_root)
    ensure_knowns_store(project_root)
    ensure_runs_store(project_root)
    ensure_suites_store(project_root)
    ensure_plans_store(project_root)
    return map_root(project_root)


def ensure_map_store(project_root: Path) -> Path:
    """Ensure global instruments + active map belief store."""
    ensure_probes_store(project_root)
    ensure_map_lib(project_root)
    # global belief dirs always exist
    prev = _active_map_id.get()
    try:
        set_active_map_id(GLOBAL_MAP_ID)
        ensure_belief_store(project_root)
        meta = map_root(project_root) / MAP_META_NAME
        if not meta.is_file():
            _write_map_meta(
                project_root,
                GLOBAL_MAP_ID,
                purpose="Global project map (durable beliefs + default evidence)",
            )
    finally:
        _active_map_id.set(prev)
    # active map (may be a session)
    ensure_belief_store(project_root)
    return map_root(project_root)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _write_map_meta(
    project_root: Path, map_id: str, *, purpose: str
) -> Path:
    root = map_root(project_root, map_id)
    root.mkdir(parents=True, exist_ok=True)
    path = root / MAP_META_NAME
    data = {
        "schema_version": 1,
        "id": map_id,
        "kind": "global" if map_id == GLOBAL_MAP_ID else "session",
        "purpose": purpose,
        "created_at": _now(),
    }
    if map_id != GLOBAL_MAP_ID:
        data["parent"] = GLOBAL_MAP_ID
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def create_session_map(
    project_root: Path,
    map_id: str,
    *,
    purpose: str = "",
    use: bool = False,
    force: bool = False,
) -> Path:
    """Create an experiment-scoped map under sessions/<id>/."""
    mid = _normalize_map_id(map_id)
    if mid == GLOBAL_MAP_ID:
        raise ValueError("cannot create map id 'global' — it always exists")
    ensure_probes_store(project_root)
    ensure_map_lib(project_root)
    root = sessions_root(project_root) / mid
    meta = root / MAP_META_NAME
    if meta.is_file() and not force:
        raise FileExistsError(f"map already exists: {mid} ({root})")
    prev = _active_map_id.get()
    try:
        set_active_map_id(mid)
        ensure_belief_store(project_root)
        _write_map_meta(
            project_root,
            mid,
            purpose=(purpose or f"Experiment map {mid}").strip(),
        )
    finally:
        _active_map_id.set(prev)
    if use:
        write_active_map(project_root, mid)
    return root


def write_active_map(project_root: Path, map_id: str) -> Path:
    """Persist active map and sync process ContextVar (so use=True / map use work in-process)."""
    mid = _normalize_map_id(map_id)
    if mid != GLOBAL_MAP_ID:
        root = sessions_root(project_root) / mid
        if not (root / MAP_META_NAME).is_file() and not root.is_dir():
            raise FileNotFoundError(
                f"map {mid!r} not found — terra map create {mid}"
            )
    path = terra_root(project_root) / ACTIVE_MAP_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(mid + "\n", encoding="utf-8")
    # Match durable selection in this process; otherwise a prior set_active_map_id
    # (e.g. global) would keep shadowing the active_map file.
    set_active_map_id(mid)
    return path


def list_maps(project_root: Path) -> list[dict[str, Any]]:
    active = get_active_map_id(project_root)
    rows: list[dict[str, Any]] = []
    # global
    gmeta = global_map_root(project_root) / MAP_META_NAME
    purpose = "global"
    if gmeta.is_file():
        try:
            purpose = json.loads(gmeta.read_text(encoding="utf-8")).get(
                "purpose", purpose
            )
        except (json.JSONDecodeError, OSError):
            pass
    rows.append(
        {
            "id": GLOBAL_MAP_ID,
            "kind": "global",
            "active": active == GLOBAL_MAP_ID,
            "purpose": purpose,
            "path": str(global_map_root(project_root)),
        }
    )
    sroot = sessions_root(project_root)
    if sroot.is_dir():
        for child in sorted(p for p in sroot.iterdir() if p.is_dir()):
            if child.name.startswith("."):
                continue
            purpose = ""
            meta = child / MAP_META_NAME
            if meta.is_file():
                try:
                    purpose = json.loads(meta.read_text(encoding="utf-8")).get(
                        "purpose", ""
                    )
                except (json.JSONDecodeError, OSError):
                    pass
            rows.append(
                {
                    "id": child.name,
                    "kind": "session",
                    "active": active == child.name,
                    "purpose": purpose,
                    "path": str(child),
                }
            )
    return rows


def require_project_root(start: Path | None = None) -> Path:
    root = find_project_root(start)
    if root is None:
        raise FileNotFoundError(
            "No .terra/ project found. "
            "`terra probe create` / `terra map create` auto-init, "
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


# --- legacy data paths ---

def data_root(project_root: Path) -> Path:
    return map_root(project_root) / DATA_DIRNAME


def capture_dir(project_root: Path, capture_id: str) -> Path:
    return data_root(project_root) / capture_id


def ensure_data_store(project_root: Path) -> Path:
    root = data_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    return root
