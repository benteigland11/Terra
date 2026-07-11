"""Knowns — typed anchors. First type: number (samples → n/mean/std)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .number_type import (
    CONFIDENCE_SET,
    KNOWN_STATUSES,
    MAP_TYPES,
    can_claim_confidence,
    derive_confidence,
    empty_stats,
    recompute_number_node,
)
from .paths import ensure_knowns_store, known_path, knowns_root, run_dir
from .probe_run import RUN_META_NAME

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
KNOWN_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def validate_known_record(data: Any, *, expected_id: str | None = None) -> list[str]:
    blocks: list[str] = []
    if not isinstance(data, dict):
        return ["known must be a JSON object"]
    if data.get("schema_version") != KNOWN_SCHEMA_VERSION:
        blocks.append(
            f"schema_version must be {KNOWN_SCHEMA_VERSION}, "
            f"got {data.get('schema_version')!r}"
        )
    kid = data.get("id")
    if not isinstance(kid, str) or not kid.strip():
        blocks.append("id must be a non-empty string")
    elif expected_id is not None and kid != expected_id:
        blocks.append(f"id {kid!r} does not match filename {expected_id!r}")

    claim = data.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        blocks.append("claim must be a non-empty string")

    mtype = data.get("type")
    if mtype not in MAP_TYPES:
        blocks.append(
            f"type must be one of {sorted(MAP_TYPES)} (v0: number only), got {mtype!r}"
        )

    status = data.get("status")
    if status not in KNOWN_STATUSES:
        blocks.append(
            f"status must be one of {sorted(KNOWN_STATUSES)}, got {status!r}"
        )

    conf = data.get("confidence")
    if conf not in CONFIDENCE_SET:
        blocks.append(
            f"confidence must be one of {sorted(CONFIDENCE_SET)}, got {conf!r}"
        )

    if mtype == "number":
        q = data.get("quantity")
        if not isinstance(q, str) or not q.strip():
            blocks.append(
                "type=number requires quantity (stable name for the scalar, "
                "e.g. hostile_count)"
            )
        stats = data.get("stats")
        if stats is not None and not isinstance(stats, dict):
            blocks.append("stats must be an object when present")
        elif isinstance(stats, dict) and conf in CONFIDENCE_SET:
            ok, msg = can_claim_confidence(stats, conf)
            if not ok:
                blocks.append(msg)

    for key in ("run_ids", "probe_ids"):
        if key in data and data[key] is not None:
            if not isinstance(data[key], list):
                blocks.append(f"{key} must be a list")
            else:
                for i, item in enumerate(data[key]):
                    if not isinstance(item, str) or not item.strip():
                        blocks.append(f"{key}[{i}] must be a non-empty string")

    return blocks


def create_known(
    project_root: Path,
    known_id: str,
    *,
    claim: str,
    quantity: str,
    unit: str = "",
    confidence: str = "low",
    status: str = "provisional",
    run_id: str | None = None,
    notes: str = "",
    force: bool = False,
) -> Path:
    if not _SLUG_RE.match(known_id):
        raise ValueError(f"known id {known_id!r} must match {_SLUG_RE.pattern}")
    if not claim or not str(claim).strip():
        raise ValueError("claim is required")
    if not quantity or not str(quantity).strip():
        raise ValueError("quantity is required for type=number")
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"confidence must be one of {sorted(CONFIDENCE_SET)}")
    if status not in KNOWN_STATUSES:
        raise ValueError(f"status must be one of {sorted(KNOWN_STATUSES)}")

    ensure_knowns_store(project_root)
    path = known_path(project_root, known_id)
    if path.exists() and not force:
        raise FileExistsError(f"known already exists: {path}")

    now = _now()
    record: dict[str, Any] = {
        "schema_version": KNOWN_SCHEMA_VERSION,
        "id": known_id,
        "type": "number",
        "role": "known",
        "claim": claim.strip(),
        "quantity": quantity.strip(),
        "unit": (unit or "").strip(),
        "status": status,
        "confidence": "low",  # always start low; promote after samples
        "run_ids": [run_id] if run_id else [],
        "probe_ids": [],
        "primary_run_id": run_id,
        "stats": empty_stats(),
        "confidence_derived": "low",
        "notes": notes or "",
        "created_at": now,
        "updated_at": now,
    }
    if run_id:
        if not (run_dir(project_root, run_id) / RUN_META_NAME).is_file():
            raise FileNotFoundError(f"run not found: {run_id}")
        record = recompute_number_node(
            record, project_root=project_root, run_dir_fn=run_dir
        )
        ok, _ = can_claim_confidence(record["stats"], confidence)
        if ok:
            record["confidence"] = confidence
        # else stay at capped value from recompute

    blocks = validate_known_record(record, expected_id=known_id)
    if blocks:
        raise ValueError("invalid known:\n  - " + "\n  - ".join(blocks))

    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_known(project_root: Path, known_id: str) -> dict[str, Any]:
    path = known_path(project_root, known_id)
    if not path.is_file():
        raise FileNotFoundError(f"known not found: {known_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_known(project_root: Path, record: dict[str, Any]) -> Path:
    kid = record["id"]
    record = dict(record)
    record["updated_at"] = _now()
    if record.get("type") == "number":
        record = recompute_number_node(
            record, project_root=project_root, run_dir_fn=run_dir
        )
    blocks = validate_known_record(record, expected_id=kid)
    if blocks:
        raise ValueError("invalid known:\n  - " + "\n  - ".join(blocks))
    ensure_knowns_store(project_root)
    path = known_path(project_root, kid)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def link_run_known(
    project_root: Path,
    known_id: str,
    run_id: str,
    *,
    primary: bool = False,
) -> dict[str, Any]:
    if not (run_dir(project_root, run_id) / RUN_META_NAME).is_file():
        raise FileNotFoundError(f"run not found: {run_id}")
    rec = load_known(project_root, known_id)
    rids = list(rec.get("run_ids") or [])
    if run_id not in rids:
        rids.append(run_id)
    rec["run_ids"] = rids
    if primary or rec.get("primary_run_id") is None:
        rec["primary_run_id"] = run_id
    # seed probe from run
    try:
        meta = json.loads(
            (run_dir(project_root, run_id) / RUN_META_NAME).read_text(encoding="utf-8")
        )
        pid = meta.get("probe_id")
        if isinstance(pid, str) and pid.strip():
            pids = list(rec.get("probe_ids") or [])
            if pid not in pids:
                pids.append(pid)
            rec["probe_ids"] = pids
    except (json.JSONDecodeError, OSError):
        pass
    if rec.get("status") == "provisional" and rec.get("stats", {}).get("n", 0) >= 1:
        pass  # stays provisional until promote
    save_known(project_root, rec)
    return load_known(project_root, known_id)


def promote_known(
    project_root: Path,
    known_id: str,
    confidence: str,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    """Raise claimed confidence only if sample ladder allows."""
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"confidence must be one of {sorted(CONFIDENCE_SET)}")
    rec = load_known(project_root, known_id)
    rec = recompute_number_node(rec, project_root=project_root, run_dir_fn=run_dir)
    ok, msg = can_claim_confidence(rec["stats"], confidence)
    if not ok:
        raise ValueError(msg)
    rec["confidence"] = confidence
    if status is not None:
        if status not in KNOWN_STATUSES:
            raise ValueError(f"status must be one of {sorted(KNOWN_STATUSES)}")
        rec["status"] = status
    elif confidence in ("med", "high") and rec.get("status") == "provisional":
        rec["status"] = "active"
    save_known(project_root, rec)
    return load_known(project_root, known_id)


def set_known_status(
    project_root: Path,
    known_id: str,
    status: str,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    if status not in KNOWN_STATUSES:
        raise ValueError(f"status must be one of {sorted(KNOWN_STATUSES)}")
    rec = load_known(project_root, known_id)
    rec["status"] = status
    if notes is not None:
        rec["notes"] = notes
    save_known(project_root, rec)
    return load_known(project_root, known_id)


def list_knowns(project_root: Path) -> list[dict[str, Any]]:
    root = knowns_root(project_root)
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("type") == "number":
                data = recompute_number_node(
                    data, project_root=project_root, run_dir_fn=run_dir
                )
        except (json.JSONDecodeError, OSError) as e:
            out.append({"id": path.stem, "ok": False, "blocks": [str(e)], "record": None})
            continue
        blocks = validate_known_record(data, expected_id=path.stem)
        out.append(
            {
                "id": path.stem,
                "ok": len(blocks) == 0,
                "blocks": blocks,
                "record": data,
            }
        )
    return out


def validate_known_file(project_root: Path, known_id: str) -> dict[str, Any]:
    path = known_path(project_root, known_id)
    if not path.is_file():
        return {
            "ok": False,
            "id": known_id,
            "blocks": [f"not found: {known_id}"],
            "record": None,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") == "number":
        data = recompute_number_node(
            data, project_root=project_root, run_dir_fn=run_dir
        )
    blocks = validate_known_record(data, expected_id=known_id)
    return {
        "ok": len(blocks) == 0,
        "id": known_id,
        "blocks": blocks,
        "record": data,
        "path": str(path),
    }


def describe_known(project_root: Path, known_id: str) -> dict[str, Any]:
    rec = load_known(project_root, known_id)
    if rec.get("type") == "number":
        rec = recompute_number_node(
            rec, project_root=project_root, run_dir_fn=run_dir
        )
    return {"record": rec}
