"""Agent-first I/O via Cartograph blueprint ``bp-agent-tool-cli-python``.

Do not invent a parallel envelope. Composition lives in the blueprint:

  leaves: universal-agent-response-python + infra-agent-cli-python
  feature: bp-agent-tool-cli-python  (AgentToolCLI, tool_success/error, emit)

Terra only re-exports the sealed blueprint API and adds optional
attention / next_actions helpers for map guidance (product layer).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Blueprint + leaves live under project cg/; sandbox and runtime need path.
_TERRA_ROOT = Path(__file__).resolve().parents[2]
_CG = _TERRA_ROOT / "cg"
if _CG.is_dir() and str(_TERRA_ROOT) not in sys.path:
    sys.path.insert(0, str(_TERRA_ROOT))

from cg.bp_agent_tool_cli_python.src.agent_tool_cli import (  # noqa: E402
    AgentToolCLI,
    emit as _emit,
    format_json,
    is_success,
    tool_error,
    tool_success,
    wrap_handler,
)

# Re-export sealed blueprint surface
__all__ = [
    "AgentToolCLI",
    "action",
    "attention_item",
    "emit",
    "error",
    "format_json",
    "is_success",
    "sort_actions",
    "sort_attention",
    "success",
    "tool_error",
    "tool_success",
    "wrap_handler",
]

success = tool_success
error = tool_error


def emit(response: dict[str, Any]) -> int:
    """Print agent-response JSON; return process-style exit code."""
    return _emit(response)


def action(
    op: str,
    argv: list[str],
    *,
    why: str,
    priority: int = 50,
    map_id: str | None = None,
) -> dict[str, Any]:
    """Concrete next step (Terra product guidance; lives in data.next_actions)."""
    row: dict[str, Any] = {
        "op": op,
        "argv": list(argv),
        "why": why,
        "priority": int(priority),
    }
    if map_id:
        row["map_id"] = map_id
    return row


def attention_item(
    kind: str,
    *,
    id: str | None = None,
    severity: str = "info",
    why: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """What needs handling (Terra product guidance; lives in data.attention)."""
    row: dict[str, Any] = {
        "kind": kind,
        "severity": severity,
        "why": why,
    }
    if id is not None:
        row["id"] = id
    if extra:
        row.update(extra)
    return row


def severity_rank(sev: str) -> int:
    order = {"block": 0, "high": 1, "med": 2, "info": 3}
    return order.get(sev, 9)


def sort_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        actions,
        key=lambda a: (int(a.get("priority") or 50), str(a.get("op") or "")),
    )


def sort_attention(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda a: (
            severity_rank(str(a.get("severity") or "info")),
            str(a.get("kind") or ""),
        ),
    )
