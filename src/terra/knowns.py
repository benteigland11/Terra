"""Knowns — typed anchors. Types: number, boolean (scalar filters only).

Multi/sequence evidence lives one layer up: ``terra.plans`` / ``terra plan``.
"""

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
    CONFIDENCE_SET,
    KNOWN_STATUSES,
    MAP_TYPES,
    SCALAR_TYPES,
    can_claim_confidence,
    empty_stats,
    recompute_typed_node,
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
            f"type must be one of {sorted(MAP_TYPES)}, got {mtype!r}"
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

    if mtype in SCALAR_TYPES:
        q = data.get("quantity")
        if not isinstance(q, str) or not q.strip():
            blocks.append(
                f"type={mtype} requires quantity (stable measure name, "
                f"e.g. hostile_count or rcon_reachable)"
            )
        stats = data.get("stats")
        if stats is not None and not isinstance(stats, dict):
            blocks.append("stats must be an object when present")
        elif isinstance(stats, dict) and conf in CONFIDENCE_SET:
            ok, msg = can_claim_confidence(stats, conf, map_type=mtype)
            if not ok:
                blocks.append(msg)
    elif mtype == "formula":
        blocks.extend(
            validate_formula_fields(data.get("expression"), data.get("vars"))
        )
        stats = data.get("stats")
        if stats is not None and not isinstance(stats, dict):
            blocks.append("stats must be an object when present")
        elif isinstance(stats, dict) and conf in CONFIDENCE_SET:
            ok, msg = can_claim_confidence(stats, conf, map_type="formula")
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
    quantity: str | None = None,
    map_type: str = "number",
    unit: str = "",
    confidence: str = "low",
    status: str = "provisional",
    run_id: str | None = None,
    notes: str = "",
    force: bool = False,
    expression: str | None = None,
    vars: dict[str, Any] | list[str] | str | None = None,
) -> Path:
    if not _SLUG_RE.match(known_id):
        raise ValueError(f"known id {known_id!r} must match {_SLUG_RE.pattern}")
    if not claim or not str(claim).strip():
        raise ValueError("claim is required")
    if map_type not in MAP_TYPES:
        raise ValueError(
            f"type must be one of {sorted(MAP_TYPES)} "
            f"(use `terra plan` for multi/sequence evidence)"
        )
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"confidence must be one of {sorted(CONFIDENCE_SET)}")
    if status not in KNOWN_STATUSES:
        raise ValueError(f"status must be one of {sorted(KNOWN_STATUSES)}")

    ensure_knowns_store(project_root)
    path = known_path(project_root, known_id)
    if path.exists() and not force:
        raise FileExistsError(f"known already exists: {path}")

    now = _now()
    if map_type == "formula":
        vars_spec = parse_vars_arg(vars)
        expr = (expression or "").strip()
        ferr = validate_formula_fields(expr, vars_spec)
        if ferr:
            raise ValueError("invalid formula:\n  - " + "\n  - ".join(ferr))
        record: dict[str, Any] = {
            "schema_version": KNOWN_SCHEMA_VERSION,
            "id": known_id,
            "type": "formula",
            "role": "known",
            "claim": claim.strip(),
            "expression": expr,
            "vars": vars_spec,
            "status": status,
            "confidence": "low",
            "run_ids": [run_id] if run_id else [],
            "probe_ids": [],
            "primary_run_id": run_id,
            "stats": empty_formula_stats(),
            "confidence_derived": "low",
            "notes": notes or "",
            "created_at": now,
            "updated_at": now,
        }
    else:
        if not quantity or not str(quantity).strip():
            raise ValueError(f"quantity is required for type={map_type}")
        record = {
            "schema_version": KNOWN_SCHEMA_VERSION,
            "id": known_id,
            "type": map_type,
            "role": "known",
            "claim": claim.strip(),
            "quantity": quantity.strip(),
            "unit": (unit or "").strip(),
            "status": status,
            "confidence": "low",
            "run_ids": [run_id] if run_id else [],
            "probe_ids": [],
            "primary_run_id": run_id,
            "stats": empty_stats(map_type),
            "confidence_derived": "low",
            "notes": notes or "",
            "created_at": now,
            "updated_at": now,
        }
    if run_id:
        if not (run_dir(project_root, run_id) / RUN_META_NAME).is_file():
            raise FileNotFoundError(f"run not found: {run_id}")
        record = recompute_typed_node(
            record, project_root=project_root, run_dir_fn=run_dir
        )
        ok, _ = can_claim_confidence(
            record["stats"], confidence, map_type=map_type
        )
        if ok:
            record["confidence"] = confidence

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
    if record.get("type") in MAP_TYPES:
        record = recompute_typed_node(
            record, project_root=project_root, run_dir_fn=run_dir
        )
    # validate after recompute (confidence demotion already applied)
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
    try:
        meta = json.loads(
            (run_dir(project_root, run_id) / RUN_META_NAME).read_text(encoding="utf-8")
        )
        if meta.get("voided"):
            raise ValueError(
                f"run {run_id} is voided — cannot link "
                f"(terra run unvoid, or use another run)"
            )
        pid = meta.get("probe_id")
        if isinstance(pid, str) and pid.strip():
            pids = list(rec.get("probe_ids") or [])
            if pid not in pids:
                pids.append(pid)
            rec["probe_ids"] = pids
    except ValueError:
        raise
    except (json.JSONDecodeError, OSError):
        pass
    rids = list(rec.get("run_ids") or [])
    if run_id not in rids:
        rids.append(run_id)
    rec["run_ids"] = rids
    if primary or rec.get("primary_run_id") is None:
        rec["primary_run_id"] = run_id
    save_known(project_root, rec)
    return load_known(project_root, known_id)


def unlink_run_known(
    project_root: Path,
    known_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Detach a sample; stats + confidence recompute (over-claimed conf demotes)."""
    rec = load_known(project_root, known_id)
    rids = [x for x in (rec.get("run_ids") or []) if x != run_id]
    rec["run_ids"] = rids
    if rec.get("primary_run_id") == run_id:
        rec["primary_run_id"] = rids[-1] if rids else None
    save_known(project_root, rec)
    return load_known(project_root, known_id)


def delete_known(project_root: Path, known_id: str) -> Path:
    path = known_path(project_root, known_id)
    if not path.is_file():
        raise FileNotFoundError(f"known not found: {known_id}")
    path.unlink()
    return path


def promote_known(
    project_root: Path,
    known_id: str,
    confidence: str,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"confidence must be one of {sorted(CONFIDENCE_SET)}")
    rec = load_known(project_root, known_id)
    rec = recompute_typed_node(rec, project_root=project_root, run_dir_fn=run_dir)
    ok, msg = can_claim_confidence(
        rec["stats"], confidence, map_type=rec.get("type")
    )
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


# Freehand --value is the agent footgun that used to look like a silent no-op
# when agents invented `terra known set` (subcommand missing) + 2>/dev/null.
_FREEHAND_VALUE_MSG = (
    "freehand --value is not supported (would skip probe evidence and stats).\n"
    "  Sample-backed path:\n"
    "    terra known set <id> --claim \"…\" --quantity <q> --from-run <run_id>\n"
    "    # or: terra known create … && terra known link-run …\n"
    "  Metadata only (existing known):\n"
    "    terra known set <id> --claim \"…\" --notes \"…\"\n"
    "  Provisional anchor without a run yet:\n"
    "    terra known set <id> --claim \"…\" --quantity <q> --notes \"asserted=…\""
)


def set_known(
    project_root: Path,
    known_id: str,
    *,
    claim: str | None = None,
    notes: str | None = None,
    map_type: str | None = None,
    quantity: str | None = None,
    unit: str | None = None,
    confidence: str | None = None,
    status: str | None = None,
    run_id: str | None = None,
    expression: str | None = None,
    vars: dict[str, Any] | list[str] | str | None = None,
    value: Any = None,
) -> tuple[dict[str, Any], str]:
    """Create-or-update a known (agent-facing ``terra known set``).

    Returns ``(record, action)`` where action is ``\"created\"`` or ``\"updated\"``.
    Always writes on success. Freehand ``value`` without a run is rejected.
    """
    if value is not None:
        raise ValueError(_FREEHAND_VALUE_MSG)

    path = known_path(project_root, known_id)
    exists = path.is_file()

    if not exists:
        if not claim or not str(claim).strip():
            raise ValueError(
                "known does not exist; --claim is required to create "
                f"(id={known_id!r}). There is no silent set."
            )
        mtype = map_type or "number"
        create_known(
            project_root,
            known_id,
            claim=claim,
            quantity=quantity,
            map_type=mtype,
            unit=unit or "",
            confidence=confidence or "low",
            status=status or "provisional",
            run_id=run_id,
            notes=notes or "",
            force=False,
            expression=expression,
            vars=vars,
        )
        return load_known(project_root, known_id), "created"

    rec = load_known(project_root, known_id)
    changed = False

    if claim is not None:
        if not str(claim).strip():
            raise ValueError("claim must be non-empty when provided")
        rec["claim"] = claim.strip()
        changed = True
    if notes is not None:
        rec["notes"] = notes
        changed = True
    if unit is not None:
        rec["unit"] = unit.strip()
        changed = True
    if status is not None:
        if status not in KNOWN_STATUSES:
            raise ValueError(f"status must be one of {sorted(KNOWN_STATUSES)}")
        rec["status"] = status
        changed = True
    if quantity is not None:
        if rec.get("type") not in SCALAR_TYPES:
            raise ValueError(
                f"cannot set --quantity on type={rec.get('type')!r} "
                f"(only {sorted(SCALAR_TYPES)})"
            )
        if not str(quantity).strip():
            raise ValueError("quantity must be non-empty when provided")
        rec["quantity"] = quantity.strip()
        changed = True
    if expression is not None:
        if rec.get("type") != "formula":
            raise ValueError("cannot set --expression on non-formula known")
        rec["expression"] = expression.strip()
        changed = True
    if vars is not None:
        if rec.get("type") != "formula":
            raise ValueError("cannot set --var on non-formula known")
        rec["vars"] = parse_vars_arg(vars)
        changed = True
    if map_type is not None and map_type != rec.get("type"):
        raise ValueError(
            f"cannot change type {rec.get('type')!r} → {map_type!r} "
            "(delete + recreate, or create a new id)"
        )

    if confidence is not None:
        if confidence not in CONFIDENCE_SET:
            raise ValueError(f"confidence must be one of {sorted(CONFIDENCE_SET)}")
        rec = recompute_typed_node(
            rec, project_root=project_root, run_dir_fn=run_dir
        )
        ok, msg = can_claim_confidence(
            rec.get("stats") or {}, confidence, map_type=rec.get("type")
        )
        if not ok:
            raise ValueError(msg)
        rec["confidence"] = confidence
        changed = True

    if run_id is not None:
        save_known(project_root, rec) if changed else None
        # link always writes
        link_run_known(project_root, known_id, run_id)
        return load_known(project_root, known_id), "updated"

    if not changed:
        raise ValueError(
            "nothing to set — pass at least one of: "
            "--claim --notes --quantity --unit --status --confidence "
            "--from-run --expression --var\n"
            "(freehand --value is rejected; see terra known set --help)"
        )

    save_known(project_root, rec)
    return load_known(project_root, known_id), "updated"


def list_knowns(project_root: Path) -> list[dict[str, Any]]:
    root = knowns_root(project_root)
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("type") in MAP_TYPES:
                data = recompute_typed_node(
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
    if data.get("type") in MAP_TYPES:
        data = recompute_typed_node(
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
    if rec.get("type") in MAP_TYPES:
        rec = recompute_typed_node(
            rec, project_root=project_root, run_dir_fn=run_dir
        )
    return {"record": rec}
