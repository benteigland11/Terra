"""Create / update / list / validate map unknowns."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .formula_type import (
    empty_formula_stats,
    parse_vars_arg,
    validate_formula_fields,
)
from .number_type import (
    MAP_TYPES,
    SCALAR_TYPES,
    empty_stats,
    recompute_typed_node,
)
from .paths import (
    ensure_unknowns_store,
    run_dir,
    unknown_path,
    unknowns_root,
)
from .probe_run import RUN_META_NAME
from .unknown_contract import (
    ACTIVE_STATUSES,
    UNKNOWN_SCHEMA_VERSION,
    UNKNOWN_STATUSES,
    validate_unknown_record,
)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def create_unknown(
    project_root: Path,
    unknown_id: str,
    *,
    claim: str,
    evidence_needed: str = "",
    blocks_build: bool = True,
    probe_id: str | None = None,
    notes: str = "",
    force: bool = False,
    map_type: str | None = None,
    quantity: str | None = None,
    unit: str = "",
    expression: str | None = None,
    vars: dict[str, Any] | list[str] | str | None = None,
    tolerance: Any = None,
) -> Path:
    if not _SLUG_RE.match(unknown_id):
        raise ValueError(
            f"unknown id {unknown_id!r} must match {_SLUG_RE.pattern}"
        )
    if not claim or not str(claim).strip():
        raise ValueError("claim is required (what we do not know)")

    ensure_unknowns_store(project_root)
    path = unknown_path(project_root, unknown_id)
    if path.exists() and not force:
        raise FileExistsError(f"unknown already exists: {path}")

    if map_type is not None and map_type not in MAP_TYPES:
        raise ValueError(
            f"type must be one of {sorted(MAP_TYPES)} or omitted, got {map_type!r}"
        )
    if map_type in SCALAR_TYPES and (
        not quantity or not str(quantity).strip()
    ):
        raise ValueError(f"type={map_type} requires --quantity")
    if map_type == "formula":
        vars_spec = parse_vars_arg(vars)
        expr = (expression or "").strip()
        ferr = validate_formula_fields(expr, vars_spec)
        if ferr:
            raise ValueError("invalid formula:\n  - " + "\n  - ".join(ferr))
    else:
        vars_spec = {}
        expr = ""

    now = _now()
    # create with --probe behaves like link-probe (probing, not open)
    status = "probing" if probe_id else "open"
    record: dict[str, Any] = {
        "schema_version": UNKNOWN_SCHEMA_VERSION,
        "id": unknown_id,
        "claim": claim.strip(),
        "status": status,
        "blocks_build": bool(blocks_build),
        "evidence_needed": (evidence_needed or "").strip()
        or "a validated probe reading that answers the claim",
        "probe_id": probe_id,
        "probe_ids": [probe_id] if probe_id else [],
        "run_ids": [],
        "primary_run_id": None,
        "resolved_by": None,
        "notes": notes or "",
        "created_at": now,
        "updated_at": now,
    }
    if map_type in SCALAR_TYPES:
        record["type"] = map_type
        record["quantity"] = quantity.strip()
        record["unit"] = (unit or "").strip()
        record["stats"] = empty_stats(map_type)
        record["confidence_derived"] = "low"
        if tolerance is not None:
            from .corroboration import parse_tolerance

            parse_tolerance(tolerance)  # loud on junk
            record["tolerance"] = tolerance
    elif map_type == "formula":
        record["type"] = "formula"
        record["expression"] = expr
        record["vars"] = vars_spec
        record["stats"] = empty_formula_stats()
        record["confidence_derived"] = "low"
    blocks = validate_unknown_record(record, expected_id=unknown_id)
    if blocks:
        raise ValueError("invalid unknown:\n  - " + "\n  - ".join(blocks))

    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_unknown(project_root: Path, unknown_id: str) -> dict[str, Any]:
    path = unknown_path(project_root, unknown_id)
    if not path.is_file():
        raise FileNotFoundError(f"unknown not found: {unknown_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_unknown(project_root: Path, record: dict[str, Any]) -> Path:
    uid = record["id"]
    record = dict(record)
    record["updated_at"] = _now()
    if record.get("type") in MAP_TYPES:
        record = recompute_typed_node(
            record, project_root=project_root, run_dir_fn=run_dir
        )
    blocks = validate_unknown_record(record, expected_id=uid)
    if blocks:
        raise ValueError("invalid unknown:\n  - " + "\n  - ".join(blocks))
    ensure_unknowns_store(project_root)
    path = unknown_path(project_root, uid)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def set_status(
    project_root: Path,
    unknown_id: str,
    status: str,
    *,
    resolved_by: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status not in UNKNOWN_STATUSES:
        raise ValueError(
            f"status must be one of {sorted(UNKNOWN_STATUSES)}, got {status!r}"
        )
    rec = load_unknown(project_root, unknown_id)
    rec["status"] = status
    if resolved_by is not None:
        rec["resolved_by"] = resolved_by
    if notes is not None:
        rec["notes"] = notes
    save_unknown(project_root, rec)
    return rec


def link_probe(
    project_root: Path, unknown_id: str, probe_id: str
) -> dict[str, Any]:
    """Attach a probe. Supports multiple probes via probe_ids; probe_id = primary."""
    rec = load_unknown(project_root, unknown_id)
    ids = list(rec.get("probe_ids") or [])
    # Seed from legacy primary so re-link does not drop the original probe
    legacy = rec.get("probe_id")
    if isinstance(legacy, str) and legacy.strip() and legacy not in ids:
        ids.append(legacy)
    if probe_id not in ids:
        ids.append(probe_id)
    rec["probe_ids"] = ids
    rec["probe_id"] = probe_id  # primary = most recently linked
    if rec.get("status") == "open":
        rec["status"] = "probing"
    save_unknown(project_root, rec)
    return rec


def _run_meta_path(project_root: Path, run_id: str) -> Path:
    return run_dir(project_root, run_id) / RUN_META_NAME


def link_run(
    project_root: Path,
    unknown_id: str,
    run_id: str,
    *,
    primary: bool = False,
) -> dict[str, Any]:
    """Attach a stamped run as structured evidence. Idempotent on run_id."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a non-empty string")
    run_id = run_id.strip()
    meta_path = _run_meta_path(project_root, run_id)
    if not meta_path.is_file():
        raise FileNotFoundError(
            f"run not found: {run_id} (expected {meta_path})"
        )
    try:
        _meta_chk = json.loads(meta_path.read_text(encoding="utf-8"))
        if _meta_chk.get("voided"):
            raise ValueError(
                f"run {run_id} is voided — cannot link "
                f"(terra run unvoid, or use another run)"
            )
    except ValueError:
        raise
    except (json.JSONDecodeError, OSError):
        pass

    rec = load_unknown(project_root, unknown_id)
    rids = list(rec.get("run_ids") or [])
    if run_id not in rids:
        rids.append(run_id)
    rec["run_ids"] = rids
    if primary or rec.get("primary_run_id") is None:
        rec["primary_run_id"] = run_id
    if rec.get("status") == "open":
        rec["status"] = "probing"
    # Best-effort: attach probe from run meta if present
    try:
        run_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pid = run_meta.get("probe_id")
        if isinstance(pid, str) and pid.strip():
            pids = list(rec.get("probe_ids") or [])
            if pid not in pids:
                pids.append(pid)
            rec["probe_ids"] = pids
            if not rec.get("probe_id"):
                rec["probe_id"] = pid
    except (json.JSONDecodeError, OSError):
        pass
    if rec.get("type") in MAP_TYPES:
        rec = recompute_typed_node(
            rec, project_root=project_root, run_dir_fn=run_dir
        )
    save_unknown(project_root, rec)
    return rec


def unlink_run(
    project_root: Path, unknown_id: str, run_id: str
) -> dict[str, Any]:
    """Detach a run; typed stats recompute on save (bad sample drops out)."""
    rec = load_unknown(project_root, unknown_id)
    rids = [x for x in (rec.get("run_ids") or []) if x != run_id]
    rec["run_ids"] = rids
    if rec.get("primary_run_id") == run_id:
        rec["primary_run_id"] = rids[-1] if rids else None
    save_unknown(project_root, rec)
    return load_unknown(project_root, unknown_id)


def delete_unknown(project_root: Path, unknown_id: str) -> Path:
    """Remove unknown record from the active map (irreversible)."""
    path = unknown_path(project_root, unknown_id)
    if not path.is_file():
        raise FileNotFoundError(f"unknown not found: {unknown_id}")
    path.unlink()
    return path


def describe_unknown(project_root: Path, unknown_id: str) -> dict[str, Any]:
    """Record plus expanded linked runs (for show)."""
    rec = load_unknown(project_root, unknown_id)
    if rec.get("type") in MAP_TYPES:
        rec = recompute_typed_node(
            rec, project_root=project_root, run_dir_fn=run_dir
        )
    runs_out: list[dict[str, Any]] = []
    for rid in rec.get("run_ids") or []:
        meta_path = _run_meta_path(project_root, rid)
        entry: dict[str, Any] = {
            "id": rid,
            "primary": rid == rec.get("primary_run_id"),
            "exists": meta_path.is_file(),
            "status": None,
            "probe_id": None,
            "captured_at": None,
            "path": str(meta_path) if meta_path.is_file() else None,
        }
        if meta_path.is_file():
            try:
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                entry["status"] = m.get("status")
                entry["probe_id"] = m.get("probe_id")
                time = m.get("time") or {}
                entry["captured_at"] = (
                    time.get("captured_at")
                    or time.get("finished_at")
                    or time.get("started_at")
                )
            except (json.JSONDecodeError, OSError):
                entry["exists"] = False
        runs_out.append(entry)
    return {"record": rec, "linked_runs": runs_out}


def list_unknowns(project_root: Path) -> list[dict[str, Any]]:
    root = unknowns_root(project_root)
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            out.append(
                {
                    "id": path.stem,
                    "ok": False,
                    "blocks": [f"unreadable: {e}"],
                    "record": None,
                }
            )
            continue
        blocks = validate_unknown_record(data, expected_id=path.stem)
        out.append(
            {
                "id": path.stem,
                "ok": len(blocks) == 0,
                "blocks": blocks,
                "record": data,
            }
        )
    return out


def validate_unknown_file(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        return {
            "ok": False,
            "id": path.stem,
            "path": str(path),
            "blocks": [f"not a file: {path}"],
            "record": None,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "id": path.stem,
            "path": str(path),
            "blocks": [f"invalid JSON: {e}"],
            "record": None,
        }
    blocks = validate_unknown_record(data, expected_id=path.stem)
    return {
        "ok": len(blocks) == 0,
        "id": path.stem,
        "path": str(path),
        "blocks": blocks,
        "record": data,
    }


def validate_all_unknowns(project_root: Path) -> dict[str, Any]:
    rows = list_unknowns(project_root)
    store_blocks: list[str] = []
    if not rows:
        # empty is ok — no unknowns yet is not a failure of the store
        pass
    any_fail = any(not r["ok"] for r in rows)
    active = [
        r
        for r in rows
        if r.get("record")
        and r["record"].get("status") in ACTIVE_STATUSES
    ]
    blocking = [
        r
        for r in active
        if r.get("record") and r["record"].get("blocks_build") is True
    ]
    return {
        "ok": not any_fail,
        "blocks": store_blocks,
        "unknowns": rows,
        "active_count": len(active),
        "blocking_count": len(blocking),
    }
