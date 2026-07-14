"""Route — task DAG for the main agent (Gantt source of truth).

Walks the **brief**. Does not store world truth (that's the map).
Does not store multi-leg belief recipes (that's evidence plans).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ensure_map_store, route_path, terra_root

ROUTE_SCHEMA_VERSION = 1
TASK_STATUSES = frozenset(
    {"ready", "in_progress", "blocked", "done", "cancelled"}
)
SKILLS = frozenset(
    {
        "terra-map",
        "terra-probe",
        "cg-plan",
        "cg-create",
        "cg-blueprint",
        "deliverable",  # produce brief.deliverables
        "tooling",  # build brief.enablers (harnesses, print pipelines)
        "any",
    }
)
# Optional task.role for clarity (enabler work vs customer deliverable)
TASK_ROLES = frozenset({"survey", "enabler", "deliverable", "orchestration", "any"})
# Effort buckets: how open the search space is (points fixed)
TASK_BUCKETS = frozenset({"low", "medium", "high"})
BUCKET_POINTS: dict[str, int] = {"low": 3, "medium": 8, "high": 21}
POINTS_BUCKET: dict[int, str] = {v: k for k, v in BUCKET_POINTS.items()}
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def points_for_bucket(bucket: str) -> int:
    if bucket not in TASK_BUCKETS:
        raise ValueError(
            f"bucket must be one of {sorted(TASK_BUCKETS)} "
            f"(points: low=3 medium=8 high=21)"
        )
    return BUCKET_POINTS[bucket]


def resolve_bucket_points(
    *,
    bucket: str | None = None,
    points: int | None = None,
) -> tuple[str | None, int | None]:
    """Return (bucket, points). Either, both, or neither may be set."""
    if bucket is None and points is None:
        return None, None
    if bucket is not None and points is not None:
        expected = points_for_bucket(bucket)
        if int(points) != expected:
            raise ValueError(
                f"bucket {bucket!r} is {expected} points, got points={points}"
            )
        return bucket, expected
    if bucket is not None:
        return bucket, points_for_bucket(bucket)
    # points only
    p = int(points)  # type: ignore[arg-type]
    if p not in POINTS_BUCKET:
        raise ValueError(
            f"points must be one of {sorted(POINTS_BUCKET)} "
            f"(low=3 medium=8 high=21), got {p}"
        )
    return POINTS_BUCKET[p], p


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def default_route(*, brief_version: int | None = None) -> dict[str, Any]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "id": "route",
        "brief_version": brief_version,
        "plan_locked": False,
        "plan_locked_at": None,
        # Reserved effort pools to explode into tasks later (provisions)
        "sectors": [],
        "tasks": [],
        "created_at": _now(),
        "updated_at": _now(),
    }


def validate_route(data: Any) -> list[str]:
    blocks: list[str] = []
    if not isinstance(data, dict):
        return ["route must be a JSON object"]
    if data.get("schema_version") != ROUTE_SCHEMA_VERSION:
        blocks.append(
            f"schema_version must be {ROUTE_SCHEMA_VERSION}, "
            f"got {data.get('schema_version')!r}"
        )
    if "plan_locked" in data and data["plan_locked"] is not None:
        if not isinstance(data["plan_locked"], bool):
            blocks.append("plan_locked must be a bool")
    sector_ids: set[str] = set()
    if "sectors" in data and data["sectors"] is not None:
        if not isinstance(data["sectors"], list):
            blocks.append("sectors must be a list")
        else:
            for i, s in enumerate(data["sectors"]):
                if not isinstance(s, dict):
                    blocks.append(f"sectors[{i}] must be an object")
                    continue
                sid = s.get("id")
                if not isinstance(sid, str) or not _SLUG_RE.match(sid):
                    blocks.append(f"sectors[{i}].id must be a slug")
                elif sid in sector_ids:
                    blocks.append(f"duplicate sector id {sid!r}")
                else:
                    sector_ids.add(sid)
                rp = s.get("reserved_points")
                if not isinstance(rp, int) or isinstance(rp, bool) or rp < 0:
                    blocks.append(
                        f"sectors[{i}].reserved_points must be int >= 0"
                    )
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        blocks.append("tasks must be a list")
        return blocks
    ids: set[str] = set()
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            blocks.append(f"tasks[{i}] must be an object")
            continue
        tid = t.get("id")
        if not isinstance(tid, str) or not _SLUG_RE.match(tid):
            blocks.append(f"tasks[{i}].id must be a slug")
        elif tid in ids:
            blocks.append(f"duplicate task id {tid!r}")
        else:
            ids.add(tid)
        if t.get("status") not in TASK_STATUSES:
            blocks.append(
                f"tasks[{i}].status must be one of {sorted(TASK_STATUSES)}"
            )
        deps = t.get("deps") or []
        if not isinstance(deps, list):
            blocks.append(f"tasks[{i}].deps must be a list")
        bkt = t.get("bucket")
        pts = t.get("points")
        if bkt is not None and bkt not in TASK_BUCKETS:
            blocks.append(
                f"tasks[{i}].bucket must be one of {sorted(TASK_BUCKETS)} or null"
            )
        if pts is not None and (
            not isinstance(pts, int)
            or isinstance(pts, bool)
            or pts not in POINTS_BUCKET
        ):
            blocks.append(
                f"tasks[{i}].points must be one of {sorted(POINTS_BUCKET)} or null"
            )
        if bkt in TASK_BUCKETS and isinstance(pts, int) and not isinstance(pts, bool):
            if pts != BUCKET_POINTS[bkt]:
                blocks.append(
                    f"tasks[{i}]: bucket {bkt!r} expects points={BUCKET_POINTS[bkt]}, "
                    f"got {pts}"
                )
        pb = t.get("plan_bucket")
        pp = t.get("plan_points")
        if pb is not None and pb not in TASK_BUCKETS:
            blocks.append(
                f"tasks[{i}].plan_bucket must be one of {sorted(TASK_BUCKETS)} or null"
            )
        if pp is not None and (
            not isinstance(pp, int)
            or isinstance(pp, bool)
            or pp not in POINTS_BUCKET
        ):
            blocks.append(
                f"tasks[{i}].plan_points must be one of {sorted(POINTS_BUCKET)} or null"
            )
        if pb in TASK_BUCKETS and isinstance(pp, int) and not isinstance(pp, bool):
            if pp != BUCKET_POINTS[pb]:
                blocks.append(
                    f"tasks[{i}]: plan_bucket {pb!r} expects plan_points="
                    f"{BUCKET_POINTS[pb]}, got {pp}"
                )
        sec = t.get("sector_id")
        if sec is not None:
            if not isinstance(sec, str) or not _SLUG_RE.match(sec):
                blocks.append(f"tasks[{i}].sector_id must be a slug or null")
            elif "sectors" in data and sec not in sector_ids:
                blocks.append(
                    f"tasks[{i}].sector_id {sec!r} not in route.sectors"
                )
    # dep existence
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for d in t.get("deps") or []:
            if d not in ids:
                blocks.append(f"task {t.get('id')}: unknown dep {d!r}")
    # dep acyclicity — a cycle silently makes tasks never-pickable
    dep_map = {
        t.get("id"): [d for d in (t.get("deps") or []) if d in ids]
        for t in tasks
        if isinstance(t, dict) and t.get("id") in ids
    }
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in dep_map}
    cycles: list[str] = []

    def visit(tid: str, path: list[str]) -> None:
        color[tid] = GRAY
        for d in dep_map.get(tid) or []:
            if color.get(d) == GRAY:
                cyc = path[path.index(d):] + [d] if d in path else [tid, d]
                cycles.append(" -> ".join(cyc + [cyc[0]] if cyc[-1] != cyc[0] else cyc))
            elif color.get(d) == WHITE:
                visit(d, path + [d])
        color[tid] = BLACK

    for tid in dep_map:
        if color[tid] == WHITE:
            visit(tid, [tid])
    for cyc in sorted(set(cycles)):
        blocks.append(f"dependency cycle: {cyc}")
    return blocks


def load_route(project_root: Path) -> dict[str, Any]:
    path = route_path(project_root)
    if not path.is_file():
        raise FileNotFoundError(
            "no route — terra route init  (after terra brief init)"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if "plan_locked" not in data:
        data["plan_locked"] = False
    if "plan_locked_at" not in data:
        data["plan_locked_at"] = None
    if "sectors" not in data or data["sectors"] is None:
        data["sectors"] = []
    for t in data.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        # legacy: copy working → plan if plan missing
        if "plan_points" not in t and t.get("points") is not None:
            t["plan_points"] = t.get("points")
        if "plan_bucket" not in t and t.get("bucket") is not None:
            t["plan_bucket"] = t.get("bucket")
    blocks = validate_route(data)
    if blocks:
        raise ValueError("invalid route:\n  - " + "\n  - ".join(blocks))
    return data


def save_route(project_root: Path, record: dict[str, Any]) -> Path:
    record = dict(record)
    record["updated_at"] = _now()
    # refresh ready flags from deps
    record["tasks"] = _recompute_ready(list(record.get("tasks") or []))
    blocks = validate_route(record)
    if blocks:
        raise ValueError("invalid route:\n  - " + "\n  - ".join(blocks))
    terra_root(project_root).mkdir(parents=True, exist_ok=True)
    path = route_path(project_root)
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _recompute_ready(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate pickable/waiting_on; leave terminal statuses alone."""
    by_id = {t["id"]: dict(t) for t in tasks if isinstance(t, dict) and t.get("id")}
    result: list[dict[str, Any]] = []
    for _tid, t in by_id.items():
        st = t.get("status")
        if st in ("done", "cancelled", "blocked", "in_progress"):
            t.pop("waiting_on", None)
            t["pickable"] = False
            result.append(t)
            continue
        deps = list(t.get("deps") or [])
        waiting = [
            d
            for d in deps
            if d not in by_id or by_id[d].get("status") != "done"
        ]
        t["status"] = "ready"
        if waiting:
            t["waiting_on"] = waiting
            t["pickable"] = False
        else:
            t.pop("waiting_on", None)
            t["pickable"] = True
        result.append(t)
    order = [t["id"] for t in tasks if isinstance(t, dict) and t.get("id")]
    by_new = {t["id"]: t for t in result}
    return [by_new[i] for i in order if i in by_new]


def init_route(project_root: Path, *, force: bool = False) -> Path:
    ensure_map_store(project_root)
    path = route_path(project_root)
    if path.is_file() and not force:
        raise FileExistsError(f"route already exists: {path}")
    brief_version = None
    try:
        from .brief import load_brief

        brief_version = load_brief(project_root).get("version")
    except (FileNotFoundError, ValueError, OSError):
        pass
    rec = default_route(brief_version=brief_version)
    return save_route(project_root, rec)


def add_task(
    project_root: Path,
    task_id: str,
    *,
    title: str,
    phase: str = "",
    deps: list[str] | None = None,
    skill: str = "any",
    role: str = "any",
    enabler_id: str | None = None,
    acceptance: list[str] | None = None,
    map_id: str | None = None,
    bucket: str | None = None,
    points: int | None = None,
    sector_id: str | None = None,
) -> dict[str, Any]:
    if not _SLUG_RE.match(task_id):
        raise ValueError(f"task id must match {_SLUG_RE.pattern}")
    if skill not in SKILLS:
        raise ValueError(f"skill must be one of {sorted(SKILLS)}")
    if role not in TASK_ROLES:
        raise ValueError(f"role must be one of {sorted(TASK_ROLES)}")
    if not title or not str(title).strip():
        raise ValueError("title required")
    bkt, pts = resolve_bucket_points(bucket=bucket, points=points)
    budget = brief_budget_points(project_root)
    if budget is not None and bkt is None and pts is None:
        raise ValueError(
            "brief has budget_points set — assign effort with "
            "--bucket low|medium|high (3/8/21) or --points 3|8|21"
        )
    # Default role from skill when not set
    if role == "any" and skill == "tooling":
        role = "enabler"
    if role == "any" and skill == "deliverable":
        role = "deliverable"
    rec = load_route(project_root)
    sectors = list(rec.get("sectors") or [])
    sector_ids = {s.get("id") for s in sectors if isinstance(s, dict)}
    if sector_id is not None:
        if not _SLUG_RE.match(sector_id):
            raise ValueError(f"sector_id must match {_SLUG_RE.pattern}")
        if sector_id not in sector_ids:
            raise ValueError(
                f"unknown sector {sector_id!r} — "
                f"terra route sector add {sector_id} --title \"…\" --points N"
            )
    if rec.get("plan_locked"):
        # Locked: only explode provisions into finer tasks inside a sector
        if not sector_id:
            raise ValueError(
                "route plan is locked — cannot add unsectored tasks to the baseline. "
                "Either: terra route add … --sector <id> --bucket …  "
                "(draw from a sector provision), or unlock: "
                "terra route unlock-plan then terra route unlock-plan --confirm"
            )
    tasks = list(rec.get("tasks") or [])
    if any(t.get("id") == task_id for t in tasks):
        raise FileExistsError(f"task already exists: {task_id}")
    tasks.append(
        {
            "id": task_id,
            "title": title.strip(),
            "phase": (phase or "").strip(),
            "deps": list(deps or []),
            "status": "ready",
            "skill": skill,
            "role": role,
            "enabler_id": enabler_id,
            "acceptance": list(acceptance or []),
            "map_id": map_id,
            "sector_id": sector_id,
            "bucket": bkt,
            "points": pts,
            "plan_bucket": bkt,
            "plan_points": pts,
            "blocked_reason": None,
            "evidence": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    assert_planned_within_budget(
        project_root,
        tasks,
        context=f"route add {task_id}",
        sectors=sectors,
    )
    rec["tasks"] = tasks
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


def add_sector(
    project_root: Path,
    sector_id: str,
    *,
    title: str,
    reserved_points: int,
    notes: str = "",
) -> dict[str, Any]:
    """Reserve a point provision to explode into tasks later."""
    if not _SLUG_RE.match(sector_id):
        raise ValueError(f"sector id must match {_SLUG_RE.pattern}")
    if not title or not str(title).strip():
        raise ValueError("title required")
    if not isinstance(reserved_points, int) or isinstance(reserved_points, bool):
        raise ValueError("reserved_points must be an int >= 0")
    if reserved_points < 0:
        raise ValueError("reserved_points must be an int >= 0")
    rec = load_route(project_root)
    if rec.get("plan_locked"):
        raise ValueError(
            "route plan is locked — cannot add sector reserves. "
            "Unlock: terra route unlock-plan --confirm"
        )
    sectors = list(rec.get("sectors") or [])
    if any(s.get("id") == sector_id for s in sectors):
        raise FileExistsError(f"sector already exists: {sector_id}")
    sectors.append(
        {
            "id": sector_id,
            "title": title.strip(),
            "reserved_points": reserved_points,
            "notes": (notes or "").strip(),
            "created_at": _now(),
        }
    )
    assert_planned_within_budget(
        project_root,
        list(rec.get("tasks") or []),
        context=f"sector add {sector_id}",
        sectors=sectors,
    )
    rec["sectors"] = sectors
    save_route(project_root, rec)
    return next(s for s in load_route(project_root)["sectors"] if s["id"] == sector_id)


def set_sector_reserve(
    project_root: Path,
    sector_id: str,
    *,
    reserved_points: int | None = None,
    title: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Adjust sector reserve (plan unlocked only for reserve changes)."""
    rec = load_route(project_root)
    if rec.get("plan_locked") and reserved_points is not None:
        raise ValueError(
            "route plan is locked — cannot change sector reserves. "
            "Unlock: terra route unlock-plan --confirm"
        )
    found = None
    for s in rec.get("sectors") or []:
        if s.get("id") == sector_id:
            found = s
            if reserved_points is not None:
                if reserved_points < 0:
                    raise ValueError("reserved_points must be >= 0")
                s["reserved_points"] = int(reserved_points)
            if title is not None:
                s["title"] = title.strip()
            if notes is not None:
                s["notes"] = notes.strip()
            break
    if not found:
        raise FileNotFoundError(f"sector not found: {sector_id}")
    assert_planned_within_budget(
        project_root,
        list(rec.get("tasks") or []),
        context=f"sector set {sector_id}",
        sectors=list(rec.get("sectors") or []),
    )
    save_route(project_root, rec)
    return next(s for s in load_route(project_root)["sectors"] if s["id"] == sector_id)


def _get_task(rec: dict[str, Any], task_id: str) -> dict[str, Any]:
    for t in rec.get("tasks") or []:
        if t.get("id") == task_id:
            return t
    raise FileNotFoundError(f"task not found: {task_id}")


def start_task(project_root: Path, task_id: str) -> dict[str, Any]:
    rec = load_route(project_root)
    t = _get_task(rec, task_id)
    if t.get("pickable") is False or t.get("waiting_on"):
        raise ValueError(
            f"task {task_id} waiting on {t.get('waiting_on')}"
        )
    if t.get("status") in ("done", "cancelled"):
        raise ValueError(f"task {task_id} is {t.get('status')}")
    if t.get("status") == "blocked":
        raise ValueError(f"task {task_id} is blocked: {t.get('blocked_reason')}")
    for task in rec["tasks"]:
        if task.get("id") == task_id:
            task["status"] = "in_progress"
            task["updated_at"] = _now()
            task.pop("waiting_on", None)
            task["pickable"] = False
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


# Claim-shaped skills: completing these must cite map evidence, not prose
SURVEY_SKILLS = frozenset({"terra-map", "terra-probe"})


def _all_map_ids(project_root: Path) -> list[str]:
    from .paths import list_maps

    return [m["id"] for m in list_maps(project_root)] or ["global"]


def _find_run(project_root: Path, run_id: str) -> dict[str, Any] | None:
    """Search every map for a run id (run ids are globally unique)."""
    from .paths import run_dir, scoped_map
    from .probe_run import RUN_META_NAME

    for mid in _all_map_ids(project_root):
        with scoped_map(mid):
            meta_path = run_dir(project_root, run_id) / RUN_META_NAME
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                meta["_map_id"] = mid
                return meta
    return None


def _find_known(project_root: Path, known_id: str) -> dict[str, Any] | None:
    """Search active map first, then the rest."""
    from .paths import get_active_map_id, known_path, scoped_map

    active = get_active_map_id(project_root)
    order = [active] + [m for m in _all_map_ids(project_root) if m != active]
    for mid in order:
        with scoped_map(mid):
            path = known_path(project_root, known_id)
            if path.is_file():
                try:
                    rec = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                rec["_map_id"] = mid
                return rec
    return None


def validate_evidence_refs(
    project_root: Path,
    *,
    run_ids: list[str] | None = None,
    known_ids: list[str] | None = None,
) -> list[str]:
    """Hard checks: cited evidence must exist and be trustworthy."""
    problems: list[str] = []
    for rid in run_ids or []:
        meta = _find_run(project_root, rid)
        if meta is None:
            problems.append(f"run not found on any map: {rid}")
        elif meta.get("voided"):
            problems.append(
                f"run {rid} is voided ({meta.get('void_reason')!r}) — "
                f"voided evidence cannot complete a task"
            )
    for kid in known_ids or []:
        rec = _find_known(project_root, kid)
        if rec is None:
            problems.append(f"known not found on any map: {kid}")
            continue
        stats = rec.get("stats") or {}
        if not (rec.get("run_ids") or []) or not (stats.get("n") or 0):
            problems.append(f"known {kid} is unbacked (n=0) — not evidence")
        if (stats.get("corroboration") or {}).get("agree") is False:
            problems.append(
                f"known {kid}: methods disagree — resolve before citing it"
            )
    return problems


def complete_task(
    project_root: Path,
    task_id: str,
    *,
    evidence: str | None = None,
    run_ids: list[str] | None = None,
    known_ids: list[str] | None = None,
    freehand: str | None = None,
) -> dict[str, Any]:
    rec = load_route(project_root)
    task = _get_task(rec, task_id)

    problems = validate_evidence_refs(
        project_root, run_ids=run_ids, known_ids=known_ids
    )
    if problems:
        raise ValueError(
            "evidence refs rejected:\n  - " + "\n  - ".join(problems)
        )

    claim_shaped = (
        task.get("skill") in SURVEY_SKILLS or task.get("role") == "survey"
    )
    if claim_shaped and not run_ids and not known_ids:
        if not freehand:
            raise ValueError(
                f"task {task_id} is claim-shaped (skill="
                f"{task.get('skill')!r}, role={task.get('role')!r}) — "
                "completing it needs map evidence, not prose:\n"
                "    terra route complete "
                f"{task_id} --run <run_id> | --known <known_id>\n"
                "  or record why none applies:\n"
                f"    terra route complete {task_id} --freehand '<reason>'"
            )

    for t in rec["tasks"]:
        if t.get("id") == task_id:
            t["status"] = "done"
            t["updated_at"] = _now()
            t["blocked_reason"] = None
            t.pop("waiting_on", None)
            entry: dict[str, Any] = {"at": _now()}
            if evidence:
                entry["note"] = evidence.strip()
            if run_ids:
                entry["runs"] = list(run_ids)
            if known_ids:
                entry["knowns"] = list(known_ids)
            if freehand:
                entry["freehand"] = freehand.strip()
            if len(entry) > 1:
                ev = list(t.get("evidence") or [])
                ev.append(entry)
                t["evidence"] = ev
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


def block_task(
    project_root: Path,
    task_id: str,
    *,
    reason: str,
) -> dict[str, Any]:
    if not reason or not str(reason).strip():
        raise ValueError("reason required")
    rec = load_route(project_root)
    _get_task(rec, task_id)
    for task in rec["tasks"]:
        if task.get("id") == task_id:
            task["status"] = "blocked"
            task["blocked_reason"] = reason.strip()
            task["updated_at"] = _now()
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


def unblock_task(project_root: Path, task_id: str) -> dict[str, Any]:
    rec = load_route(project_root)
    _get_task(rec, task_id)
    for task in rec["tasks"]:
        if task.get("id") == task_id:
            task["status"] = "ready"
            task["blocked_reason"] = None
            task["updated_at"] = _now()
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


def next_tasks(project_root: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    rec = load_route(project_root)
    rec["tasks"] = _recompute_ready(list(rec.get("tasks") or []))
    pickable = [
        t
        for t in rec["tasks"]
        if t.get("status") == "ready" and t.get("pickable") is True
    ]
    in_prog = [t for t in rec["tasks"] if t.get("status") == "in_progress"]
    out = in_prog + pickable
    return out[: max(1, limit)]


def _task_points(t: dict[str, Any]) -> int:
    pts = t.get("points")
    if isinstance(pts, int) and not isinstance(pts, bool) and pts in POINTS_BUCKET:
        return pts
    bkt = t.get("bucket")
    if bkt in BUCKET_POINTS:
        return BUCKET_POINTS[bkt]
    return 0


def planned_points(tasks: list[dict[str, Any]]) -> int:
    return sum(
        _task_points(t)
        for t in tasks
        if t.get("status") != "cancelled"
    )


def brief_budget_points(project_root: Path) -> int | None:
    try:
        from .brief import load_brief

        bp = load_brief(project_root).get("budget_points")
        if isinstance(bp, int) and not isinstance(bp, bool) and bp >= 0:
            return bp
    except (FileNotFoundError, ValueError, OSError):
        pass
    return None


def assert_planned_within_budget(
    project_root: Path,
    tasks: list[dict[str, Any]],
    *,
    context: str = "route",
    budget_points: int | None = None,
    sectors: list[dict[str, Any]] | None = None,
) -> None:
    """Hard fail when plan allocation exceeds budget or sector reserves.

    Uses **plan_points** (baseline) when set, else working points.
    ``budget_points`` / ``sectors`` override disk when not saved yet.
    """
    budget = budget_points if budget_points is not None else brief_budget_points(
        project_root
    )
    if sectors is None:
        try:
            sectors = list(load_route(project_root).get("sectors") or [])
        except (FileNotFoundError, ValueError, OSError):
            sectors = []

    reserved = 0
    by_sec_reserve: dict[str, int] = {}
    for s in sectors:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        rp = s.get("reserved_points")
        if isinstance(sid, str) and isinstance(rp, int) and not isinstance(rp, bool):
            by_sec_reserve[sid] = rp
            reserved += rp

    if budget is not None and reserved > budget:
        raise ValueError(
            f"{context}: sum of sector reserves {reserved} exceeds "
            f"budget_points {budget}"
        )

    plan_by_sector: dict[str, int] = {sid: 0 for sid in by_sec_reserve}
    unsectored = 0
    total_plan = 0
    for t in tasks:
        if t.get("status") == "cancelled":
            continue
        p = _plan_task_points(t) or _task_points(t)
        total_plan += p
        sid = t.get("sector_id")
        if sid:
            if sid not in by_sec_reserve:
                raise ValueError(
                    f"{context}: task {t.get('id')!r} sector_id {sid!r} "
                    f"has no matching route sector"
                )
            plan_by_sector[sid] = plan_by_sector.get(sid, 0) + p
        else:
            unsectored += p

    for sid, used in plan_by_sector.items():
        cap = by_sec_reserve.get(sid, 0)
        if used > cap:
            raise ValueError(
                f"{context}: sector {sid!r} plan allocation {used} exceeds "
                f"reserved_points {cap}. Add less, raise sector reserve, or "
                f"use a different sector."
            )

    if budget is not None:
        free = budget - reserved
        if unsectored > free:
            raise ValueError(
                f"{context}: unsectored plan points {unsectored} exceed free "
                f"pool {free} (budget {budget} − sector reserves {reserved}). "
                f"Put work in a sector, lower buckets, or raise budget."
            )
        if total_plan > budget:
            raise ValueError(
                f"{context}: plan points {total_plan} exceed budget_points {budget} "
                f"(unallocated would be {budget - total_plan}). "
                f"Lower task buckets, cancel tasks, or raise "
                f"`terra brief set --budget-points …`."
            )


def set_task_effort(
    project_root: Path,
    task_id: str,
    *,
    bucket: str | None = None,
    points: int | None = None,
) -> dict[str, Any]:
    """Re-bucket a task (e.g. low→medium when work got harder).

    If plan is **locked**: only working ``bucket``/``points`` change (plan_* frozen).
    Working may exceed budget_points.

    If plan is **unlocked**: updates both plan and working; still enforces
    planned (working) ≤ budget like initial setting.
    """
    if bucket is None and points is None:
        raise ValueError("provide --bucket and/or --points")
    bkt, pts = resolve_bucket_points(bucket=bucket, points=points)
    rec = load_route(project_root)
    t = _get_task(rec, task_id)
    if t.get("status") == "cancelled":
        raise ValueError(f"task {task_id} is cancelled")
    locked = bool(rec.get("plan_locked"))
    for task in rec["tasks"]:
        if task.get("id") == task_id:
            task["bucket"] = bkt
            task["points"] = pts
            if not locked:
                task["plan_bucket"] = bkt
                task["plan_points"] = pts
            task["updated_at"] = _now()
            break
    if not locked:
        assert_planned_within_budget(
            project_root,
            list(rec.get("tasks") or []),
            context=f"set-effort {task_id} (plan unlocked — treated as replan)",
        )
    save_route(project_root, rec)
    return _get_task(load_route(project_root), task_id)


def lock_plan(project_root: Path) -> dict[str, Any]:
    """Freeze plan_* ledger from current working points; stop baseline drift."""
    rec = load_route(project_root)
    if rec.get("plan_locked"):
        return {
            "plan_locked": True,
            "plan_locked_at": rec.get("plan_locked_at"),
            "message": "plan already locked",
            "budget": budget_rollup(project_root, list(rec.get("tasks") or [])),
        }
    # Ensure every weighted task has plan_* = working before lock
    for task in rec.get("tasks") or []:
        if task.get("status") == "cancelled":
            continue
        if task.get("points") is not None or task.get("bucket") is not None:
            task["plan_bucket"] = task.get("bucket")
            task["plan_points"] = task.get("points")
            if task.get("plan_points") is None and task.get("bucket") in BUCKET_POINTS:
                task["plan_points"] = BUCKET_POINTS[task["bucket"]]
                task["plan_bucket"] = task["bucket"]
    assert_planned_within_budget(
        project_root,
        list(rec.get("tasks") or []),
        context="lock-plan",
    )
    rec["plan_locked"] = True
    rec["plan_locked_at"] = _now()
    save_route(project_root, rec)
    rec2 = load_route(project_root)
    return {
        "plan_locked": True,
        "plan_locked_at": rec2.get("plan_locked_at"),
        "message": "plan locked — set-effort only changes working points; "
        "route add only with --sector <provision> (explode reserves); "
        "full replan: unlock-plan --confirm",
        "budget": budget_rollup(project_root, list(rec2.get("tasks") or [])),
    }


def unlock_plan(project_root: Path, *, confirm: bool = False) -> dict[str, Any]:
    """Unlock plan ledger. Requires confirm=True (--confirm on CLI)."""
    rec = load_route(project_root)
    if not rec.get("plan_locked"):
        return {
            "plan_locked": False,
            "plan_locked_at": rec.get("plan_locked_at"),
            "message": "plan already unlocked",
            "budget": budget_rollup(project_root, list(rec.get("tasks") or [])),
        }
    if not confirm:
        raise ValueError(
            "WARNING: unlocking the plan allows rewriting plan_bucket/plan_points "
            "(baseline commitment) and adding tasks to the plan again. "
            "Working effort history is not deleted, but the locked baseline can drift. "
            "If you intend this, re-run: terra route unlock-plan --confirm"
        )
    rec["plan_locked"] = False
    # keep plan_locked_at as last lock time for audit
    save_route(project_root, rec)
    rec2 = load_route(project_root)
    return {
        "plan_locked": False,
        "plan_locked_at": rec2.get("plan_locked_at"),
        "message": "plan unlocked — set-effort updates plan+working; route add allowed",
        "budget": budget_rollup(project_root, list(rec2.get("tasks") or [])),
    }


def _plan_task_points(t: dict[str, Any]) -> int:
    pp = t.get("plan_points")
    if isinstance(pp, int) and not isinstance(pp, bool) and pp in POINTS_BUCKET:
        return pp
    pb = t.get("plan_bucket")
    if pb in BUCKET_POINTS:
        return BUCKET_POINTS[pb]
    return 0


def budget_rollup(project_root: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Project budget vs plan/actual task points (3/8/21 buckets)."""
    budget = None
    notes = ""
    plan_locked = False
    plan_locked_at = None
    try:
        from .brief import load_brief

        br = load_brief(project_root)
        budget = br.get("budget_points")
        notes = br.get("budget_notes") or ""
    except (FileNotFoundError, ValueError, OSError):
        pass
    try:
        rt = load_route(project_root)
        plan_locked = bool(rt.get("plan_locked"))
        plan_locked_at = rt.get("plan_locked_at")
    except (FileNotFoundError, ValueError, OSError):
        pass

    actual = 0
    plan = 0
    done = 0
    in_flight = 0
    by_bucket: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    by_plan_bucket: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    unset_tasks = 0
    for t in tasks:
        if t.get("status") == "cancelled":
            continue
        p = _task_points(t)
        pp = _plan_task_points(t)
        bkt = t.get("bucket") if t.get("bucket") in TASK_BUCKETS else None
        pb = t.get("plan_bucket") if t.get("plan_bucket") in TASK_BUCKETS else None
        if bkt:
            by_bucket[bkt] += p
        elif p == 0:
            unset_tasks += 1
        if pb:
            by_plan_bucket[pb] += pp
        actual += p
        plan += pp
        st = t.get("status")
        if st == "done":
            done += p
        elif st in ("in_progress", "ready", "blocked"):
            in_flight += p

    # Sector provisions
    sectors_out: list[dict[str, Any]] = []
    reserved_total = 0
    try:
        for s in load_route(project_root).get("sectors") or []:
            if not isinstance(s, dict) or not s.get("id"):
                continue
            sid = s["id"]
            reserved = int(s.get("reserved_points") or 0)
            reserved_total += reserved
            plan_used = sum(
                _plan_task_points(t) or _task_points(t)
                for t in tasks
                if t.get("status") != "cancelled" and t.get("sector_id") == sid
            )
            actual_used = sum(
                _task_points(t)
                for t in tasks
                if t.get("status") != "cancelled" and t.get("sector_id") == sid
            )
            sectors_out.append(
                {
                    "id": sid,
                    "title": s.get("title"),
                    "reserved_points": reserved,
                    "points_plan": plan_used,
                    "points_actual": actual_used,
                    "remaining_reserve_plan": reserved - plan_used,
                    "over_reserve": actual_used > reserved,
                    "notes": s.get("notes") or "",
                }
            )
    except (FileNotFoundError, ValueError, OSError):
        pass

    remaining = None
    unallocated_plan = None
    unallocated_actual = None
    free_pool = None
    over_budget = False
    over_plan = False
    if isinstance(budget, int) and not isinstance(budget, bool):
        remaining = budget - done
        unallocated_plan = budget - plan
        unallocated_actual = budget - actual
        free_pool = budget - reserved_total
        over_budget = actual > budget
        over_plan = actual > plan

    return {
        "budget_points": budget,
        "budget_notes": notes,
        "plan_locked": plan_locked,
        "plan_locked_at": plan_locked_at,
        "bucket_scale": dict(BUCKET_POINTS),
        "sectors": sectors_out,
        "sector_reserved_total": reserved_total,
        "free_pool": free_pool,  # budget − sector reserves (for unsectored tasks)
        # baseline commitment
        "points_plan": plan,
        "points_by_bucket_plan": by_plan_bucket,
        # working effort (may diverge after lock + set-effort)
        "points_actual": actual,
        "points_planned": actual,  # alias for older clients
        "points_done": done,
        "points_remaining_work": in_flight,
        "points_remaining_budget": remaining,
        "points_unallocated_plan": unallocated_plan,
        "points_unallocated_actual": unallocated_actual,
        "points_unallocated": unallocated_actual,  # alias
        "over_budget": over_budget,
        "over_plan": over_plan,
        "variance_actual_minus_plan": actual - plan,
        "points_by_bucket_actual": by_bucket,
        "points_by_bucket_planned": by_bucket,  # alias
        "tasks_without_points": unset_tasks,
    }


STALL_DAYS = 7


def route_attention(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aging debt on the route: stalled in-progress work, standing blocks."""
    from datetime import datetime, timezone

    items: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for t in tasks:
        st = t.get("status")
        if st == "blocked":
            items.append(
                {
                    "kind": "task_blocked",
                    "id": t.get("id"),
                    "severity": "med",
                    "why": f"blocked: {t.get('blocked_reason') or '(no reason)'}",
                }
            )
        elif st == "in_progress":
            raw = t.get("updated_at")
            try:
                touched = datetime.fromisoformat(
                    str(raw).replace("Z", "+00:00")
                )
                age_days = (now - touched).days
            except (ValueError, TypeError):
                continue
            if age_days >= STALL_DAYS:
                items.append(
                    {
                        "kind": "task_stalled",
                        "id": t.get("id"),
                        "severity": "high",
                        "why": (
                            f"in_progress untouched for {age_days}d — "
                            f"complete/block it or split the work"
                        ),
                    }
                )
    return items


def route_status(project_root: Path) -> dict[str, Any]:
    rec = load_route(project_root)
    rec["tasks"] = _recompute_ready(list(rec.get("tasks") or []))
    tasks = rec["tasks"]
    by_status: dict[str, int] = {}
    for t in tasks:
        st = str(t.get("status") or "?")
        by_status[st] = by_status.get(st, 0) + 1
    pickable = [t for t in tasks if t.get("pickable") is True]
    blocked = [t for t in tasks if t.get("status") == "blocked"]
    return {
        "command": "route.status",
        "brief_version": rec.get("brief_version"),
        "plan_locked": bool(rec.get("plan_locked")),
        "plan_locked_at": rec.get("plan_locked_at"),
        "counts": {
            "tasks": len(tasks),
            "by_status": by_status,
            "pickable": len(pickable),
            "blocked": len(blocked),
            "in_progress": by_status.get("in_progress", 0),
            "done": by_status.get("done", 0),
        },
        "budget": budget_rollup(project_root, tasks),
        "next": next_tasks(project_root, limit=5),
        "blocked": blocked,
        "attention": route_attention(tasks),
        "tasks": tasks,
    }
