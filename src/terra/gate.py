"""Mechanical release gate — debts fail the gate, no judgment calls.

``terra gate`` exits 0 only when every map is clean:
  - no active unknowns flagged blocks_build
  - no unbacked knowns (evidence voided/unlinked away)
  - no stale knowns (dependency moved without re-derivation)
  - no unsatisfied evidence plans

Route integration: completing a ``deliverable`` task requires the gate to
pass (or an explicit recorded override).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import (
    GLOBAL_MAP_ID,
    get_active_map_id,
    list_maps,
    scoped_map,
)


def _collect_map_violations(
    project_root: Path, map_id: str
) -> list[dict[str, Any]]:
    from .knowns import list_knowns
    from .plans import list_plans
    from .staleness import compute_staleness
    from .unknowns import list_unknowns

    violations: list[dict[str, Any]] = []
    with scoped_map(map_id):
        unknowns = list_unknowns(project_root)
        knowns = list_knowns(project_root)
        plans = list_plans(project_root)
        stale = compute_staleness(project_root)

    for u in unknowns:
        rec = u.get("record") or {}
        if rec.get("status") in ("open", "probing", "blocked") and rec.get(
            "blocks_build"
        ):
            violations.append(
                {
                    "kind": "unknown_blocking",
                    "id": rec.get("id") or u.get("id"),
                    "map_id": map_id,
                    "why": (
                        f"blocks_build unknown still {rec.get('status')}: "
                        f"{(rec.get('claim') or '')[:80]}"
                    ),
                }
            )

    for k in knowns:
        rec = k.get("record") or {}
        kid = rec.get("id") or k.get("id")
        n = (rec.get("stats") or {}).get("n") or 0
        if not (rec.get("run_ids") or []) or n == 0:
            violations.append(
                {
                    "kind": "known_unbacked",
                    "id": kid,
                    "map_id": map_id,
                    "why": f"known {kid} has no live evidence (n={n})",
                }
            )
        info = stale.get(str(kid)) or {}
        if info.get("stale"):
            violations.append(
                {
                    "kind": "known_stale",
                    "id": kid,
                    "map_id": map_id,
                    "why": (
                        f"known {kid} is stale: "
                        + "; ".join(info.get("reasons") or [])
                    ),
                }
            )

    for p in plans:
        rec = p.get("record") or {}
        pl = rec.get("plan") or {}
        if not pl.get("all_satisfied"):
            violations.append(
                {
                    "kind": "plan_incomplete",
                    "id": rec.get("id") or p.get("id"),
                    "map_id": map_id,
                    "why": (
                        f"plan {rec.get('id')}: "
                        f"{pl.get('satisfied_count')}/{pl.get('leg_count')} "
                        f"legs satisfied"
                    ),
                }
            )

    return violations


def check_gate(
    project_root: Path,
    *,
    map_id: str | None = None,
) -> dict[str, Any]:
    """Gate verdict. Default scans ALL maps — session debt cannot hide."""
    if map_id:
        map_ids = [map_id]
    else:
        map_ids = [m["id"] for m in list_maps(project_root)] or [GLOBAL_MAP_ID]
    violations: list[dict[str, Any]] = []
    for mid in map_ids:
        violations.extend(_collect_map_violations(project_root, mid))
    return {
        "ok": not violations,
        "maps_checked": map_ids,
        "active_map": get_active_map_id(project_root),
        "violations": violations,
        "counts": {
            kind: sum(1 for v in violations if v["kind"] == kind)
            for kind in sorted({v["kind"] for v in violations})
        },
    }
