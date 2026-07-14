"""Read path for knowns — the single place a number lives.

Probes, sheet generators, and models must import values from the map instead
of hardcoding copies:

  from terra.readings import known
  MTOW = known("mtow")["value"]          # loud if missing/unbacked/stale

Reads are loud by default: missing, unbacked (n=0), stale (dep moved), or
below --min-conf all raise. Every read stamps a consumption edge under
``.terra/map/consumers/<known_id>.json`` so the dependency graph knows who
builds on which belief.

Consumer identity resolution (first hit wins):
  explicit arg > probe context (set by ``terra probe run``) >
  ``TERRA_CONSUMER`` env > ``tool:<sys.argv[0]>``
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .number_type import CONFIDENCE_SET
from .paths import (
    consumer_path,
    ensure_consumers_store,
    find_project_root,
    known_path,
)
from .staleness import compute_staleness

_CONF_RANK = {"low": 0, "med": 1, "high": 2}

# Module-level consumer context (single-process CLI; threads read it fine)
_CURRENT_CONSUMER: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


@contextmanager
def consumer_scope(consumer: str):
    """Set the reader identity for the duration (used by ``terra probe run``)."""
    global _CURRENT_CONSUMER
    prev = _CURRENT_CONSUMER
    _CURRENT_CONSUMER = consumer
    try:
        yield
    finally:
        _CURRENT_CONSUMER = prev


def resolve_consumer(explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    if _CURRENT_CONSUMER:
        return _CURRENT_CONSUMER
    env = os.environ.get("TERRA_CONSUMER")
    if env and env.strip():
        return env.strip()
    argv0 = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "unknown"
    if argv0 in ("terra", "terra.exe"):
        # Interactive/agent CLI read — real tools should pass --consumer
        # or set TERRA_CONSUMER so the edge names who actually builds on it
        return "cli"
    return f"tool:{argv0}"


def record_consumption(
    project_root: Path, known_id: str, consumer: str
) -> Path:
    ensure_consumers_store(project_root)
    path = consumer_path(project_root, known_id)
    doc: dict[str, Any] = {"known_id": known_id, "consumers": []}
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    rows = doc.setdefault("consumers", [])
    now = _now()
    for row in rows:
        if row.get("consumer") == consumer:
            row["last_read_at"] = now
            row["reads"] = int(row.get("reads") or 0) + 1
            break
    else:
        rows.append(
            {
                "consumer": consumer,
                "first_read_at": now,
                "last_read_at": now,
                "reads": 1,
            }
        )
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def list_consumers(project_root: Path, known_id: str) -> list[dict[str, Any]]:
    path = consumer_path(project_root, known_id)
    if not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(doc.get("consumers") or [])


def extract_value(rec: dict[str, Any]) -> Any:
    """Canonical scalar for a known: number→mean, boolean→rate, formula→holds."""
    stats = rec.get("stats") or {}
    mtype = rec.get("type")
    if mtype == "number":
        return stats.get("mean")
    if mtype == "boolean":
        return stats.get("rate")
    if mtype == "formula":
        return stats.get("holds")
    return None


def read_known(
    project_root: Path,
    known_id: str,
    *,
    min_conf: str = "low",
    allow_stale: bool = False,
    consumer: str | None = None,
    record: bool = True,
) -> dict[str, Any]:
    """Read a known for consumption. Loud on missing/unbacked/stale/low-conf."""
    if min_conf not in CONFIDENCE_SET:
        raise ValueError(f"min_conf must be one of {sorted(CONFIDENCE_SET)}")

    path = known_path(project_root, known_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"known not found: {known_id} — survey it first "
            f"(terra unknown create … && terra unknown graduate …)"
        )
    rec = json.loads(path.read_text(encoding="utf-8"))

    stats = rec.get("stats") or {}
    n = stats.get("n") or 0
    if not (rec.get("run_ids") or []) or n == 0:
        raise ValueError(
            f"known {known_id} is unbacked (n={n}, no live evidence) — "
            f"refusing to hand out a number nobody measured.\n"
            f"    terra known link-run {known_id} <run_id>"
        )

    conf = str(rec.get("confidence") or "low")
    if _CONF_RANK.get(conf, 0) < _CONF_RANK.get(min_conf, 0):
        raise ValueError(
            f"known {known_id} is confidence={conf}, below required "
            f"min_conf={min_conf}.\n"
            f"    terra known link-run {known_id} <run_id>  # more samples\n"
            f"    terra known promote {known_id} {min_conf}"
        )

    stale_info = compute_staleness(project_root).get(known_id) or {}
    if stale_info.get("stale") and not allow_stale:
        reasons = "; ".join(stale_info.get("reasons") or [])
        raise ValueError(
            f"known {known_id} is STALE ({reasons}) — re-derive before "
            f"consuming.\n"
            f"    terra probe run … && terra known link-run {known_id} <run_id>\n"
            f"    # or, if verified unchanged: terra known reaffirm "
            f"{known_id} --reason '…'"
        )

    who = resolve_consumer(consumer)
    if record:
        record_consumption(project_root, known_id, who)

    return {
        "id": known_id,
        "value": extract_value(rec),
        "unit": rec.get("unit") or "",
        "type": rec.get("type"),
        "confidence": conf,
        "n": n,
        "stats": stats,
        "stale": bool(stale_info.get("stale")),
        "stale_reasons": list(stale_info.get("reasons") or []),
        "consumer": who,
    }


def known(known_id: str, **kwargs: Any) -> dict[str, Any]:
    """Convenience for probes/tools: resolve project root from cwd and read."""
    root = find_project_root()
    if root is None:
        raise FileNotFoundError(
            "no .terra project found from cwd — run inside the project"
        )
    return read_known(root, known_id, **kwargs)
