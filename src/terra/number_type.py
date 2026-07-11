"""Map type: number — samples in, substrate-computed stats out.

Probes stay open. Number-typed knowns/unknowns filter to a scalar estimate
with uncertainty. Agents do not author mean/std; Terra recomputes from runs.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

MAP_TYPES = frozenset({"number"})  # closed; more types later
CONFIDENCE_LEVELS = ("low", "med", "high")
CONFIDENCE_SET = frozenset(CONFIDENCE_LEVELS)

# Known status (belief)
KNOWN_STATUSES = frozenset(
    {"provisional", "active", "contested", "refuted", "superseded"}
)


def compute_number_stats(values: list[float]) -> dict[str, Any]:
    """From sample vector → n, mean, std (sample), min, max.

    std is null when n < 2 (n=1 cannot invent uncertainty).
    """
    clean = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    n = len(clean)
    if n == 0:
        return {
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
        "n": n,
        "mean": mean,
        "std": std,
        "min": float(min(clean)),
        "max": float(max(clean)),
        "values": clean,
    }


def derive_confidence(stats: dict[str, Any]) -> str:
    """Opinionated ladder from sample size / std — not agent vibes.

    low:  n >= 1
    med:  n >= 3 or (n >= 2 and std is not None)
    high: n >= 5 and std is not None and (mean==0 or std/|mean| <= 0.5)
    """
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


def confidence_rank(level: str) -> int:
    order = {"low": 0, "med": 1, "high": 2}
    return order.get(level, 0)


def can_claim_confidence(stats: dict[str, Any], want: str) -> tuple[bool, str]:
    """Whether stats support claiming `want` confidence."""
    if want not in CONFIDENCE_SET:
        return False, f"confidence must be one of {sorted(CONFIDENCE_SET)}"
    derived = derive_confidence(stats)
    if confidence_rank(want) <= confidence_rank(derived):
        return True, derived
    return (
        False,
        f"cannot claim confidence={want!r} with n={stats.get('n')}, "
        f"std={stats.get('std')} (derived max is {derived!r}; need more samples)",
    )


def extract_measures_from_run_meta(
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
) -> list[float]:
    """Pull numeric measures from a stamped run.

    Accepts:
      - run_meta["measures"]: [{quantity, value}, ...] or [number, ...]
      - artifacts with role "measures" / name measures.json (path under run dir handled by caller)
    """
    values: list[float] = []
    raw = run_meta.get("measures")
    if isinstance(raw, list):
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


def extract_measures_from_run_dir(
    run_dir: Path,
    run_meta: dict[str, Any],
    *,
    quantity: str | None = None,
) -> list[float]:
    """Meta measures + optional artifacts/measures.json."""
    values = extract_measures_from_run_meta(run_meta, quantity=quantity)
    # artifact file measures.json
    for art in run_meta.get("artifacts") or []:
        if not isinstance(art, dict):
            continue
        rel = art.get("path")
        role = art.get("role")
        if not isinstance(rel, str):
            continue
        if role == "measures" or rel.endswith("measures.json") or rel.endswith("/measures.json"):
            fpath = run_dir / rel if not Path(rel).is_absolute() else Path(rel)
            # also try relative to run dir basename
            if not fpath.is_file():
                fpath = run_dir / Path(rel).name
            if fpath.is_file():
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if isinstance(data, list):
                    values.extend(
                        extract_measures_from_run_meta(
                            {"measures": data}, quantity=quantity
                        )
                    )
                elif isinstance(data, dict) and "measures" in data:
                    values.extend(
                        extract_measures_from_run_meta(data, quantity=quantity)
                    )
                elif isinstance(data, dict) and "value" in data:
                    values.extend(
                        extract_measures_from_run_meta(
                            {"measures": [data]}, quantity=quantity
                        )
                    )
    return values


def empty_stats() -> dict[str, Any]:
    return compute_number_stats([])


def recompute_number_node(
    record: dict[str, Any],
    *,
    project_root: Path,
    run_dir_fn,
) -> dict[str, Any]:
    """Rebuild stats + derived confidence ceiling from linked run_ids."""
    from .probe_run import RUN_META_NAME  # local to avoid cycles at import if any

    quantity = record.get("quantity")
    if not isinstance(quantity, str) or not quantity.strip():
        quantity = None
    else:
        quantity = quantity.strip()

    all_values: list[float] = []
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
        vals = extract_measures_from_run_dir(rdir, meta, quantity=quantity)
        sample_runs.append({"run_id": rid, "n": len(vals), "values": vals})
        all_values.extend(vals)

    stats = compute_number_stats(all_values)
    stats["by_run"] = sample_runs
    record = dict(record)
    record["stats"] = stats
    record["confidence_derived"] = derive_confidence(stats)
    # Cap claimed confidence at derived
    claimed = record.get("confidence") or "low"
    if claimed not in CONFIDENCE_SET:
        claimed = "low"
    if confidence_rank(claimed) > confidence_rank(record["confidence_derived"]):
        record["confidence"] = record["confidence_derived"]
    else:
        record["confidence"] = claimed
    return record
