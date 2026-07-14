"""The design layer — graduated knowns become the stable design baseline.

Project-wide (like brief/route), sourced exclusively from the GLOBAL map:
session experiments never become design. Two halves:

  params     knowns admitted into the design (live links, value never copied)
  artifacts  deliverable files stamped against the params they were built from

Admission bar: known on global map, confidence >= med, backed, methods not
disagreeing, not stale. Params stay live: if the underlying known moves,
degrades, or goes stale, the param goes red (attention + gate), never
silently updated. Artifacts go red when a used param moved after their
stamp, when the file changed without re-attach, or when the file is gone.

Health is computed at check time, never stored as truth.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .number_type import confidence_rank
from .paths import scoped_map, terra_root
from .staleness import file_sha256

DESIGN_FILENAME = "design.json"
DESIGN_SCHEMA_VERSION = 1
ADMISSION_MIN_CONF = "med"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def design_path(project_root: Path) -> Path:
    return terra_root(project_root) / DESIGN_FILENAME


def load_design(project_root: Path) -> dict[str, Any]:
    path = design_path(project_root)
    if not path.is_file():
        return {
            "schema_version": DESIGN_SCHEMA_VERSION,
            "params": [],
            "artifacts": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_design(project_root: Path, rec: dict[str, Any]) -> Path:
    rec = dict(rec)
    rec["updated_at"] = _now()
    terra_root(project_root).mkdir(parents=True, exist_ok=True)
    path = design_path(project_root)
    path.write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _load_global_known(project_root: Path, known_id: str) -> dict[str, Any] | None:
    from .paths import known_path

    with scoped_map("global"):
        path = known_path(project_root, known_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


def _known_admission_problems(
    project_root: Path, known_id: str, rec: dict[str, Any] | None
) -> list[str]:
    from .staleness import compute_staleness

    if rec is None:
        return [
            f"known {known_id!r} not found on the GLOBAL map — session "
            "experiments do not become design (promote the belief to global "
            "first)"
        ]
    problems: list[str] = []
    stats = rec.get("stats") or {}
    if not (rec.get("run_ids") or []) or not (stats.get("n") or 0):
        problems.append(f"known {known_id} is unbacked (n=0)")
    conf = str(rec.get("confidence") or "low")
    if confidence_rank(conf) < confidence_rank(ADMISSION_MIN_CONF):
        problems.append(
            f"known {known_id} is confidence={conf}, design admission needs "
            f">= {ADMISSION_MIN_CONF} (link more runs + promote)"
        )
    if (stats.get("corroboration") or {}).get("agree") is False:
        problems.append(f"known {known_id}: methods disagree — resolve first")
    with scoped_map("global"):
        info = compute_staleness(project_root).get(known_id) or {}
    if info.get("stale"):
        problems.append(
            f"known {known_id} is stale: "
            + "; ".join(info.get("reasons") or [])
        )
    return problems


def add_param(
    project_root: Path,
    known_id: str,
    *,
    name: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Admit a global-map known into the design (live link, pinned stamp)."""
    from .readings import extract_value

    pname = name or known_id
    rec = _load_global_known(project_root, known_id)
    problems = _known_admission_problems(project_root, known_id, rec)
    if problems:
        raise ValueError(
            "design admission refused:\n  - " + "\n  - ".join(problems)
        )
    assert rec is not None

    design = load_design(project_root)
    params = design.setdefault("params", [])
    existing = next((p for p in params if p.get("name") == pname), None)
    if existing is not None and not force:
        raise FileExistsError(
            f"design param {pname!r} exists (known {existing.get('known_id')}) "
            f"— terra design refresh {pname}, or --force to replace"
        )
    entry = {
        "name": pname,
        "known_id": known_id,
        "admitted_at": _now(),
        "known_updated_at": rec.get("updated_at"),
        "value_at_admission": extract_value(rec),
        "unit": rec.get("unit") or "",
        "confidence_at_admission": rec.get("confidence"),
    }
    if existing is not None:
        params[params.index(existing)] = entry
    else:
        params.append(entry)
    save_design(project_root, design)
    return entry


def refresh_param(project_root: Path, name: str) -> dict[str, Any]:
    """Re-pin a param after its known legitimately moved (bar re-checked)."""
    design = load_design(project_root)
    entry = next(
        (p for p in design.get("params") or [] if p.get("name") == name), None
    )
    if entry is None:
        raise FileNotFoundError(f"design param not found: {name}")
    return add_param(
        project_root, entry["known_id"], name=name, force=True
    )


def remove_param(project_root: Path, name: str) -> None:
    design = load_design(project_root)
    params = design.get("params") or []
    entry = next((p for p in params if p.get("name") == name), None)
    if entry is None:
        raise FileNotFoundError(f"design param not found: {name}")
    used_by = [
        a.get("path")
        for a in design.get("artifacts") or []
        if name in (a.get("uses") or [])
    ]
    if used_by:
        raise ValueError(
            f"design param {name!r} is used by artifacts: {used_by} — "
            "detach them first"
        )
    params.remove(entry)
    save_design(project_root, design)


def attach_artifact(
    project_root: Path, path: str, *, uses: list[str]
) -> dict[str, Any]:
    """Stamp a deliverable file against the design params it was built from."""
    if not uses:
        raise ValueError("--uses is required: which design params built this file?")
    fpath = project_root / path
    if not fpath.is_file():
        raise FileNotFoundError(f"artifact file not found: {path}")
    design = load_design(project_root)
    by_name = {p.get("name"): p for p in design.get("params") or []}
    missing = [u for u in uses if u not in by_name]
    if missing:
        raise ValueError(
            f"not design params: {missing} — terra design add <known> first "
            f"(have: {sorted(by_name)})"
        )
    entry = {
        "path": path,
        "uses": list(uses),
        "sha256": file_sha256(fpath),
        "stamped_at": _now(),
        "params_at": {
            u: by_name[u].get("known_updated_at") for u in uses
        },
    }
    artifacts = design.setdefault("artifacts", [])
    existing = next((a for a in artifacts if a.get("path") == path), None)
    if existing is not None:
        artifacts[artifacts.index(existing)] = entry
    else:
        artifacts.append(entry)
    save_design(project_root, design)
    return entry


def detach_artifact(project_root: Path, path: str) -> None:
    design = load_design(project_root)
    artifacts = design.get("artifacts") or []
    entry = next((a for a in artifacts if a.get("path") == path), None)
    if entry is None:
        raise FileNotFoundError(f"artifact not attached: {path}")
    artifacts.remove(entry)
    save_design(project_root, design)


def check_design(project_root: Path) -> dict[str, Any]:
    """Health of every param and artifact — computed now, never stored."""
    design = load_design(project_root)
    violations: list[dict[str, Any]] = []
    params_out: list[dict[str, Any]] = []

    for p in design.get("params") or []:
        name = p.get("name")
        kid = p.get("known_id")
        rec = _load_global_known(project_root, kid)
        reasons = _known_admission_problems(project_root, kid, rec)
        moved = bool(
            rec is not None
            and str(rec.get("updated_at") or "")
            > str(p.get("known_updated_at") or "")
        )
        if moved:
            reasons.append(
                f"known {kid} moved since admission — review and "
                f"`terra design refresh {name}`"
            )
        row = {
            **p,
            "ok": not reasons,
            "reasons": reasons,
            "current_value": None,
            "current_confidence": None,
        }
        if rec is not None:
            from .readings import extract_value

            row["current_value"] = extract_value(rec)
            row["current_confidence"] = rec.get("confidence")
        params_out.append(row)
        for r in reasons:
            violations.append(
                {"kind": "design_param", "id": name, "why": r}
            )

    params_at_now = {
        p.get("name"): p.get("known_updated_at")
        for p in design.get("params") or []
    }
    artifacts_out: list[dict[str, Any]] = []
    for a in design.get("artifacts") or []:
        path = a.get("path")
        reasons = []
        fpath = project_root / str(path)
        current = file_sha256(fpath)
        if current is None:
            reasons.append("file missing")
        elif current != a.get("sha256"):
            reasons.append(
                "file changed since stamp — re-attach after regeneration"
            )
        for u in a.get("uses") or []:
            now_at = params_at_now.get(u)
            then_at = (a.get("params_at") or {}).get(u)
            if now_at is None:
                reasons.append(f"uses removed design param: {u}")
            elif str(now_at) > str(then_at or ""):
                reasons.append(
                    f"param {u} moved after stamp — REGENERATE this file"
                )
        artifacts_out.append({**a, "ok": not reasons, "reasons": reasons})
        for r in reasons:
            violations.append(
                {"kind": "design_artifact", "id": path, "why": r}
            )

    return {
        "command": "design.check",
        "ok": not violations,
        "params": params_out,
        "artifacts": artifacts_out,
        "violations": violations,
        "counts": {
            "params": len(params_out),
            "params_red": sum(1 for p in params_out if not p["ok"]),
            "artifacts": len(artifacts_out),
            "artifacts_red": sum(1 for a in artifacts_out if not a["ok"]),
        },
    }


def get_param(
    project_root: Path, name: str, *, consumer: str | None = None
) -> dict[str, Any]:
    """Read path for generators: live known value, admission bar enforced."""
    from .readings import read_known

    design = load_design(project_root)
    entry = next(
        (p for p in design.get("params") or [] if p.get("name") == name), None
    )
    if entry is None:
        raise FileNotFoundError(
            f"design param not found: {name} — terra design add <known_id>"
        )
    with scoped_map("global"):
        reading = read_known(
            project_root,
            entry["known_id"],
            min_conf=ADMISSION_MIN_CONF,
            consumer=consumer,
        )
    reading["param"] = name
    return reading
