"""Execute a probe for real and stamp a run (substrate: time + from)."""

from __future__ import annotations

import hashlib
import json
import platform
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .paths import ensure_runs_store, probe_dir, run_dir, runs_root
from .probe_contract import (
    PROBE_ENTRY_DEFAULT,
    PROBE_META_NAME,
    PROBE_SCRIPT_NAME,
    is_nonempty_to,
    validate_probe_input_level1,
    validate_probe_output_level1,
)
from .probe_load import load_probe_module, probe_sys_path
from .status_vocab import warn_status_vocab
from .to_schema import warn_to_shape
from .watch_ctx import build_watch_ctx, effective_run_timeout


def _parse_entry(entry: str) -> tuple[str, str] | None:
    if not isinstance(entry, str) or ":" not in entry:
        return None
    script, _, attr = entry.partition(":")
    script, attr = script.strip(), attr.strip()
    if not script or not attr or not attr.isidentifier():
        return None
    return script, attr

DEFAULT_RUN_TIMEOUT_S = 120.0
RUN_META_NAME = "meta.json"
RUN_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _load_probe_meta(pdir: Path) -> dict[str, Any]:
    meta_path = pdir / PROBE_META_NAME
    if not meta_path.is_file():
        raise FileNotFoundError(f"missing {PROBE_META_NAME} in {pdir}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _artifact_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_artifacts(
    raw_artifacts: list[Any],
    *,
    project_root: Path,
    run_path: Path,
) -> list[dict[str, Any]]:
    """Normalize probe artifacts into stamped list with optional integrity."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw_artifacts):
        if isinstance(item, str):
            entry: dict[str, Any] = {"path": item, "role": "reading"}
        elif isinstance(item, dict):
            entry = dict(item)
            if "path" not in entry and "role" not in entry:
                entry.setdefault("role", "reading")
        else:
            entry = {"path": str(item), "role": "opaque", "index": i}

        path_str = entry.get("path")
        if isinstance(path_str, str) and path_str.strip():
            p = Path(path_str)
            if not p.is_absolute():
                cand = (project_root / p).resolve()
                if cand.exists():
                    p = cand
                else:
                    p = (run_path / p).resolve()
            else:
                p = p.resolve()
            try:
                rel = str(p.relative_to(project_root.resolve()))
            except ValueError:
                rel = str(p)
            entry["path"] = rel
            if p.is_file():
                entry.setdefault("bytes", p.stat().st_size)
                digest = _artifact_sha256(p)
                if digest:
                    entry.setdefault("sha256", digest)
                entry.setdefault("exists", True)
            else:
                entry.setdefault("exists", p.exists())
        out.append(entry)
    return out


def _build_from(
    *,
    probe_id: str,
    entry: str,
    project_root: Path,
    kind: str | None,
) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "entry": entry,
        "kind": kind,
        "runner": "python",
        "cwd": str(project_root.resolve()),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "terra_version": __version__,
    }


def _call_with_timeout(
    fn: Callable[..., Any], ctx: dict[str, Any], timeout_s: float
) -> Any:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn, ctx)
        return fut.result(timeout=timeout_s)


def parse_to_arg(raw: str | None) -> Any:
    """Parse --to CLI value: JSON object/string, or key=value pairs."""
    if raw is None or not str(raw).strip():
        return {"kind": "default"}
    text = str(raw).strip()
    if text.startswith("{") or text.startswith("[") or text.startswith('"'):
        return json.loads(text)
    if "=" in text and not text.startswith("/"):
        parts = [p for chunk in text.replace(",", " ").split() for p in [chunk] if p]
        obj: dict[str, Any] = {}
        for part in parts:
            if "=" not in part:
                raise ValueError(
                    f"invalid --to fragment {part!r} (want key=value or JSON)"
                )
            k, _, v = part.partition("=")
            try:
                obj[k] = json.loads(v)
            except json.JSONDecodeError:
                obj[k] = v
        if not obj:
            raise ValueError("--to key=value produced empty target")
        return obj
    return {"kind": "literal", "value": text}


def run_probe(
    project_root: Path,
    probe_id: str,
    *,
    to: Any | None = None,
    timeout_s: float = DEFAULT_RUN_TIMEOUT_S,
    dry_run: bool = False,
    extra_ctx: dict[str, Any] | None = None,
    strict_to: bool = False,
    strict_status: bool = False,
) -> dict[str, Any]:
    """Load probe, execute run(ctx), stamp a run directory. Returns stamp dict.

    strict_to / strict_status: promote composition warns to hard failures (CI).
    Default remains warn-only.
    """
    project_root = project_root.resolve()
    pdir = probe_dir(project_root, probe_id)
    if not pdir.is_dir():
        raise FileNotFoundError(f"unknown probe {probe_id!r} (no {pdir})")

    meta = _load_probe_meta(pdir)
    entry = meta.get("entry") or PROBE_ENTRY_DEFAULT
    parsed = _parse_entry(entry if isinstance(entry, str) else PROBE_ENTRY_DEFAULT)
    if parsed is None:
        raise ValueError(f"invalid probe entry {entry!r}")
    script_name, attr = parsed
    script_path = pdir / script_name
    if not script_path.is_file():
        script_path = pdir / PROBE_SCRIPT_NAME
        attr = "run"
        if not script_path.is_file():
            raise FileNotFoundError(f"probe script missing under {pdir}")

    mod_name = f"terra_probe_run_{probe_id}_{uuid.uuid4().hex[:8]}"
    mod, import_err = load_probe_module(
        project_root, script_path, module_name=mod_name
    )
    if import_err:
        raise RuntimeError(import_err)
    assert mod is not None
    fn = getattr(mod, attr, None)
    if not callable(fn):
        raise RuntimeError(f"entry {attr!r} is not callable on {script_path}")

    target = to if to is not None else {"kind": "default", "probe": probe_id}
    ctx: dict[str, Any] = {"to": target}
    if dry_run:
        ctx["dry_run"] = True
    # Watch: probe owns the window; substrate only injects deadline/duration
    for k, v in build_watch_ctx(meta, dry_run=bool(dry_run)).items():
        ctx.setdefault(k, v)
    if extra_ctx:
        for k, v in extra_ctx.items():
            if k not in ctx:
                ctx[k] = v

    input_blocks = validate_probe_input_level1(ctx)
    if input_blocks:
        raise ValueError("invalid run input:\n  - " + "\n  - ".join(input_blocks))

    timeout_eff = effective_run_timeout(meta, float(timeout_s))

    started = _now()
    started_mono = datetime.now(timezone.utc)
    # Keep map lib on sys.path for the whole execute (imports inside run())
    try:
        with probe_sys_path(project_root, pdir):
            raw = _call_with_timeout(fn, ctx, timeout_eff)
    except FuturesTimeout as e:
        raise TimeoutError(
            f"probe {probe_id!r} exceeded timeout {timeout_eff}s "
            f"(watch window needs duration_s+slack if kind=watch)"
        ) from e
    finished = _now()
    finished_mono = datetime.now(timezone.utc)

    output_blocks = validate_probe_output_level1(raw)
    if output_blocks:
        raise ValueError(
            "probe output failed level-1 contract:\n  - "
            + "\n  - ".join(output_blocks)
        )
    assert isinstance(raw, dict)

    ensure_runs_store(project_root)
    stamp = started_mono.strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}_{probe_id}_{uuid.uuid4().hex[:6]}"
    rdir = run_dir(project_root, run_id)
    rdir.mkdir(parents=True, exist_ok=False)

    artifacts = _normalize_artifacts(
        list(raw.get("artifacts") or []),
        project_root=project_root,
        run_path=rdir,
    )

    duration_s = max(0.0, (finished_mono - started_mono).total_seconds())
    stamp_doc: dict[str, Any] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "id": run_id,
        "probe_id": probe_id,
        "time": {
            "started_at": started,
            "finished_at": finished,
            "captured_at": finished,
            "duration_s": duration_s,
        },
        "from": _build_from(
            probe_id=probe_id,
            entry=f"{script_path.name}:{attr}",
            project_root=project_root,
            kind=meta.get("kind"),
        ),
        "to": raw.get("to"),
        "status": raw.get("status"),
        "artifacts": artifacts,
        "measures": raw.get("measures") if isinstance(raw.get("measures"), list) else [],
        "dry_run": bool(dry_run),
        "timeout_s": float(timeout_eff),
        "probe_purpose": meta.get("purpose"),
        "probe_kind": meta.get("kind"),
        "watch_mode": ctx.get("watch_mode"),
        "duration_s": ctx.get("duration_s"),
    }

    warnings: list[str] = []
    to_warns: list[str] = []
    status_warns: list[str] = []
    # Recommended composition — default warn-only; --strict-* promotes to blocks
    if not dry_run:
        to_warns.extend(warn_to_shape(target, live=True, which="input"))
        to_warns.extend(warn_to_shape(stamp_doc.get("to"), live=True, which="output"))
        status_warns.extend(warn_status_vocab(stamp_doc.get("status"), live=True))
        warnings.extend(to_warns)
        warnings.extend(status_warns)
    if not artifacts and not dry_run:
        warnings.append(
            "run produced zero artifacts — evidence may be thin "
            "(status alone is not a map reading)"
        )
    if not is_nonempty_to(stamp_doc["to"]):
        warnings.append("to is empty after run (should not pass level-1)")

    # Soft guard: watch window ignored if wall time << duration_s
    if (
        not dry_run
        and ctx.get("watch_mode") == "window"
        and isinstance(ctx.get("duration_s"), (int, float))
        and float(ctx["duration_s"]) > 0
    ):
        elapsed = max(0.0, (finished_mono - started_mono).total_seconds())
        need = float(ctx["duration_s"])
        # finished in under 10% of window (and under 1s floor for small N)
        if elapsed < min(1.0, need * 0.1):
            warnings.append(
                f"watch window was duration_s={need:g}s but run finished in "
                f"{elapsed:.3f}s — probe should poll/listen until "
                "ctx['deadline'] / ctx['deadline_unix'] (probe owns the window; "
                "see docs/watch-duration.md)"
            )

    strict_blocks: list[str] = []
    if strict_to:
        strict_blocks.extend(f"strict-to: {w}" for w in to_warns)
    if strict_status:
        strict_blocks.extend(f"strict-status: {w}" for w in status_warns)

    stamp_doc["warnings"] = warnings
    if strict_blocks:
        stamp_doc["strict_blocks"] = strict_blocks

    meta_path = rdir / RUN_META_NAME
    meta_path.write_text(
        json.dumps(stamp_doc, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    latest = runs_root(project_root) / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "probe_id": probe_id,
                "path": str(meta_path.relative_to(project_root)),
                "status": stamp_doc["status"],
                "captured_at": finished,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    stamp_doc["_path"] = str(meta_path)
    stamp_doc["_run_dir"] = str(rdir)

    if strict_blocks:
        raise ValueError(
            "strict validation failed (run stamped, exit failed for CI):\n  - "
            + "\n  - ".join(strict_blocks)
        )

    return stamp_doc


def list_runs(
    project_root: Path,
    *,
    probe_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    root = runs_root(project_root)
    if not root.is_dir():
        return []
    status_filter = status.strip().lower() if isinstance(status, str) and status.strip() else None
    rows: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), reverse=True):
        if not child.is_dir() or child.name.startswith("."):
            continue
        meta_path = child / RUN_META_NAME
        if not meta_path.is_file():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            rows.append(
                {
                    "id": child.name,
                    "ok": False,
                    "blocks": [f"unreadable: {e}"],
                    "record": None,
                    "path": str(meta_path),
                }
            )
            continue
        if probe_id and data.get("probe_id") != probe_id:
            continue
        if status_filter is not None:
            st = data.get("status")
            if not isinstance(st, str) or st.strip().lower() != status_filter:
                continue
        from .run_validate import validate_run_record

        blocks = validate_run_record(data, expected_id=child.name)
        rows.append(
            {
                "id": child.name,
                "ok": len(blocks) == 0,
                "blocks": blocks,
                "record": data,
                "path": str(meta_path),
            }
        )
    return rows


def load_run(project_root: Path, run_id: str) -> dict[str, Any]:
    path = run_dir(project_root, run_id) / RUN_META_NAME
    if not path.is_file():
        raise FileNotFoundError(f"run not found: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))
