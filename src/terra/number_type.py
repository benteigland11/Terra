"""Map types: number + boolean — samples in, substrate-computed stats out.

Probes stay open. Typed knowns/unknowns filter the world.
Agents do not author stats; Terra recomputes from runs.measures.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

MAP_TYPES = frozenset({"number", "boolean"})
CONFIDENCE_LEVELS = ("low", "med", "high")
CONFIDENCE_SET = frozenset(CONFIDENCE_LEVELS)

KNOWN_STATUSES = frozenset(
    {"provisional", "active", "contested", "refuted", "superseded"}
)


# ---------------------------------------------------------------------------
# Number
# ---------------------------------------------------------------------------


def compute_number_stats(values: list[float]) -> dict[str, Any]:
    """From sample vector → n, mean, std (sample), min, max.

    std is null when n < 2 (n=1 cannot invent uncertainty).
    """
    clean = [
        float(v)
        for v in values
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    n = len(clean)
    if n == 0:
        return {
            "kind": "number",
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "values": [],
        }
    mean = float(statistics.fmean(clean))
    std: float | None
    if n < 2:
        std = None
    else:
        std = float(statistics.stdev(clean))
    return {
        "kind": "number",
        "n": n,
        "mean": mean,
        "std": std,
        "min": float(min(clean)),
        "max": float(max(clean)),
        "values": clean,
    }


def derive_confidence_number(stats: dict[str, Any]) -> str:
    """low: n>=1; med: n>=3 or (n>=2 and std); high: n>=5 and tight std/mean."""
    n = int(stats.get("n") or 0)
    if n < 1:
        return "low"
    std = stats.get("std")
    mean = stats.get("mean")
    if n >= 5 and std is not None and mean is not None:
        if mean == 0:
            if std == 0:
                return "high"
        elif abs(float(std) / abs(float(mean))) <= 0.5:
            return "high"
    if n >= 3 or (n >= 2 and std is not None):
        return "med"
    return "low"


# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------


def coerce_bool(v: Any) -> bool | None:
    """Accept true/false, 1/0, 'true'/'false' (case-insensitive)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and not isinstance(v, bool) and v in (0, 1):
        return bool(v)
    if isinstance(v, float) and v in (0.0, 1.0):
        return bool(int(v))
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0"):
            return False
    return None


def compute_boolean_stats(values: list[bool]) -> dict[str, Any]:
    """From trial vector → n, k_true, k_false, rate."""
    clean = [v for v in values if isinstance(v, bool)]
    n = len(clean)
    if n == 0:
        return {
            "kind": "boolean",
            "n": 0,
            "k_true": 0,
            "k_false": 0,
            "rate": None,
            "values": [],
        }
    k_true = sum(1 for v in clean if v)
    k_false = n - k_true
    return {
        "kind": "boolean",
        "n": n,
        "k_true": k_true,
        "k_false": k_false,
        "rate": float(k_true) / float(n),
        "values": clean,
    }


def derive_confidence_boolean(stats: dict[str, Any]) -> str:
    """low: n>=1; med: n>=3; high: n>=5 and unanimous (rate 0 or 1)."""
    n = int(stats.get("n") or 0)
    if n < 1:
        return "low"
    rate = stats.get("rate")
    if n >= 5 and rate is not None and (rate == 0.0 or rate == 1.0):
        return "high"
    if n >= 3:
        return "med"
    return "low"


# ---------------------------------------------------------------------------
# Shared confidence API
# ---------------------------------------------------------------------------


def derive_confidence(stats: dict[str, Any], map_type: str | None = None) -> str:
    kind = map_type or stats.get("kind") or "number"
    if kind == "boolean":
        return derive_confidence_boolean(stats)
    return derive_confidence_number(stats)


def confidence_rank(level: str) -> int:
    order = {"low": 0, "med": 1, "high": 2}
    return order.get(level, 0)


def can_claim_confidence(
    stats: dict[str, Any],
    want: str,
    *,
    map_type: str | None = None,
) -> tuple[bool, str]:
    if want not in CONFIDENCE_SET:
        return False, f"confidence must be one of {sorted(CONFIDENCE_SET)}"
    derived = derive_confidence(stats, map_type=map_type)
    if confidence_rank(want) <= confidence_rank(derived):
        return True, derived
    kind = map_type or stats.get("kind") or "number"
    if kind == "boolean":
        return (
            False,
            f"cannot claim confidence={want!r} with n={stats.get('n')}, "
            f"rate={stats.get('rate')} (derived max is {derived!r}; need more trials)",
        )
    return (
        False,
        f"cannot claim confidence={want!r} with n={stats.get('n')}, "
        f"std={stats.get('std')} (derived max is {derived!r}; need more samples)",
    )


# ---------------------------------------------------------------------------
# Measure extraction
# ---------------------------------------------------------------------------


def extract_number_measures_from_run_meta(
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
) -> list[float]:
    values: list[float] = []
    raw = run_meta.get("measures")
    if not isinstance(raw, list):
        return values
    for item in raw:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            if quantity is None:
                values.append(float(item))
        elif isinstance(item, dict):
            q = item.get("quantity")
            v = item.get("value")
            if quantity is not None and q is not None and q != quantity:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                values.append(float(v))
    return values


def extract_boolean_measures_from_run_meta(
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
) -> list[bool]:
    values: list[bool] = []
    raw = run_meta.get("measures")
    if not isinstance(raw, list):
        return values
    for item in raw:
        if isinstance(item, bool):
            if quantity is None:
                values.append(item)
            continue
        if isinstance(item, dict):
            q = item.get("quantity")
            v = item.get("value")
            if quantity is not None and q is not None and q != quantity:
                continue
            b = coerce_bool(v)
            if b is not None:
                values.append(b)
        else:
            b = coerce_bool(item)
            if b is not None and quantity is None:
                values.append(b)
    return values


def _load_measures_json(fpath: Path) -> Any:
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _artifact_measure_blobs(
    run_dir: Path, run_meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """Extra measure lists from artifacts/measures.json style files."""
    blobs: list[dict[str, Any]] = []
    for art in run_meta.get("artifacts") or []:
        if not isinstance(art, dict):
            continue
        rel = art.get("path")
        role = art.get("role")
        if not isinstance(rel, str):
            continue
        if not (
            role == "measures"
            or rel.endswith("measures.json")
            or rel.endswith("/measures.json")
        ):
            continue
        fpath = run_dir / rel if not Path(rel).is_absolute() else Path(rel)
        if not fpath.is_file():
            fpath = run_dir / Path(rel).name
        if not fpath.is_file():
            continue
        data = _load_measures_json(fpath)
        if isinstance(data, list):
            blobs.append({"measures": data})
        elif isinstance(data, dict) and "measures" in data:
            blobs.append(data)
        elif isinstance(data, dict) and "value" in data:
            blobs.append({"measures": [data]})
    return blobs


def extract_measures_from_run_dir(
    run_dir: Path,
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
    map_type: str = "number",
) -> list[Any]:
    """Meta measures + optional measures.json artifacts."""
    if map_type == "boolean":
        values: list[Any] = extract_boolean_measures_from_run_meta(
            run_meta, quantity=quantity
        )
        for blob in _artifact_measure_blobs(run_dir, run_meta):
            values.extend(
                extract_boolean_measures_from_run_meta(blob, quantity=quantity)
            )
        return values

    values = extract_number_measures_from_run_meta(run_meta, quantity=quantity)
    for blob in _artifact_measure_blobs(run_dir, run_meta):
        values.extend(
            extract_number_measures_from_run_meta(blob, quantity=quantity)
        )
    return values


# Back-compat alias used by older imports
def extract_measures_from_run_meta(
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
) -> list[float]:
    return extract_number_measures_from_run_meta(run_meta, quantity=quantity)


def empty_stats(map_type: str = "number") -> dict[str, Any]:
    if map_type == "boolean":
        return compute_boolean_stats([])
    return compute_number_stats([])


def recompute_typed_node(
    record: dict[str, Any],
    *,
    project_root: Path,
    run_dir_fn,
) -> dict[str, Any]:
    """Rebuild stats + derived confidence from linked run_ids."""
    from .probe_run import RUN_META_NAME

    map_type = record.get("type") or "number"
    quantity = record.get("quantity")
    if not isinstance(quantity, str) or not quantity.strip():
        quantity = None
    else:
        quantity = quantity.strip()

    all_values: list[Any] = []
    sample_runs: list[dict[str, Any]] = []
    for rid in record.get("run_ids") or []:
        if not isinstance(rid, str):
            continue
        rdir = run_dir_fn(project_root, rid)
        meta_path = rdir / RUN_META_NAME
        if not meta_path.is_file():
            sample_runs.append({"run_id": rid, "n": 0, "missing": True})
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            sample_runs.append({"run_id": rid, "n": 0, "missing": True})
            continue
        vals = extract_measures_from_run_dir(
            rdir, meta, quantity=quantity, map_type=map_type
        )
        sample_runs.append({"run_id": rid, "n": len(vals), "values": vals})
        all_values.extend(vals)

    if map_type == "boolean":
        stats = compute_boolean_stats([v for v in all_values if isinstance(v, bool)])
    else:
        stats = compute_number_stats(
            [
                float(v)
                for v in all_values
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
        )
    stats["by_run"] = sample_runs
    record = dict(record)
    record["stats"] = stats
    record["confidence_derived"] = derive_confidence(stats, map_type=map_type)
    claimed = record.get("confidence") or "low"
    if claimed not in CONFIDENCE_SET:
        claimed = "low"
    if confidence_rank(claimed) > confidence_rank(record["confidence_derived"]):
        record["confidence"] = record["confidence_derived"]
    else:
        record["confidence"] = claimed
    return record


# Back-compat name
def recompute_number_node(
    record: dict[str, Any],
    *,
    project_root: Path,
    run_dir_fn,
) -> dict[str, Any]:
    return recompute_typed_node(
        record, project_root=project_root, run_dir_fn=run_dir_fn
    )
