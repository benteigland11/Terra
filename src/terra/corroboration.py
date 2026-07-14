"""Corroboration — the second axis of evidence.

Repetition (n-ladder) proves *precision*: the same instrument, run again,
scatters less. It cannot catch systematic error. Corroboration proves
*truth-shaped agreement*: independent methods (distinct probes) arriving at
the same answer within a declared tolerance.

Ladder consequences (hard opinions):
  - ``high`` requires >=2 methods agreeing — repetition alone caps at ``med``
  - methods in *disagreement* are louder than absence: derived confidence
    collapses to ``low``, reads refuse, the gate fails

Computed from per-probe sample groups at recompute time; never stored as
independent truth.
"""

from __future__ import annotations

from typing import Any

TOLERANCE_KEY = "tolerance"


def parse_tolerance(spec: Any) -> tuple[str, float] | None:
    """``"5%"`` → ("rel", 0.05); ``"0.5"``/``0.5`` → ("abs", 0.5); None → None."""
    if spec is None or (isinstance(spec, str) and not spec.strip()):
        return None
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        value = float(spec)
        kind = "abs"
    else:
        s = str(spec).strip()
        if s.endswith("%"):
            kind = "rel"
            body = s[:-1].strip()
        else:
            kind = "abs"
            body = s
        try:
            value = float(body)
        except ValueError:
            raise ValueError(
                f"tolerance must be a number or 'N%', got {spec!r}"
            ) from None
        if kind == "rel":
            value = value / 100.0
    if value < 0:
        raise ValueError(f"tolerance must be >= 0, got {spec!r}")
    return kind, value


def compute_corroboration(
    by_probe: dict[str, dict[str, Any]],
    *,
    map_type: str,
    tolerance: Any = None,
) -> dict[str, Any]:
    """→ {methods, tolerance, spread, spread_rel, agree, verdicts?}.

    agree: True/False when judgeable; None when <2 methods or (numbers)
    no tolerance declared.
    """
    groups = {
        pid: g for pid, g in (by_probe or {}).items() if (g.get("n") or 0) > 0
    }
    methods = len(groups)
    out: dict[str, Any] = {
        "methods": methods,
        "tolerance": tolerance,
        "agree": None,
    }
    if methods < 2:
        return out

    if map_type == "boolean":
        verdicts = {
            pid: bool((g.get("rate") or 0.0) >= 0.5) for pid, g in groups.items()
        }
        out["verdicts"] = verdicts
        out["agree"] = len(set(verdicts.values())) == 1
        return out

    means = {pid: g.get("mean") for pid, g in groups.items()}
    vals = [m for m in means.values() if m is not None]
    if len(vals) < 2:
        return out
    spread = max(vals) - min(vals)
    center = sum(abs(v) for v in vals) / len(vals)
    out["spread"] = spread
    out["spread_rel"] = (spread / center) if center else None

    tol = parse_tolerance(tolerance)
    if tol is None:
        # >=2 methods but nothing declared — surface the spread, don't judge
        return out
    kind, limit = tol
    if kind == "rel":
        rel = out["spread_rel"]
        out["agree"] = bool(rel is not None and rel <= limit) if center else (
            spread <= 0
        )
    else:
        out["agree"] = spread <= limit
    return out


def corroboration_gate_high(stats: dict[str, Any]) -> tuple[bool, str]:
    """Can these stats support ``high``? (statistical bar checked elsewhere)"""
    corr = stats.get("corroboration") or {}
    methods = int(corr.get("methods") or 0)
    agree = corr.get("agree")
    if agree is False:
        return False, "methods disagree — resolve before any promotion"
    if methods < 2:
        return (
            False,
            "high needs a second independent probe (repetition proves "
            "precision, not truth) — link runs from another method",
        )
    if agree is None:
        return (
            False,
            "2+ methods but agreement not judgeable — declare "
            "`terra known tolerance <id> --within 5%`",
        )
    return True, ""


def methods_disagree(stats: dict[str, Any]) -> bool:
    return (stats.get("corroboration") or {}).get("agree") is False
