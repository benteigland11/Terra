"""Create validated map data captures."""

from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .data_schema import SCHEMA_VERSION, sha256_file, validate_capture_dir
from .env_fingerprint import collect_fingerprint
from .paths import capture_dir, ensure_data_store, find_project_root


def _new_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(3)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _artifact_entry(capture_path: Path, rel: str, role: str, *, allow_empty: bool = False) -> dict[str, Any]:
    fpath = capture_path / rel
    size = fpath.stat().st_size
    entry: dict[str, Any] = {
        "path": rel,
        "role": role,
        "bytes": size,
        "sha256": sha256_file(fpath),
    }
    if allow_empty:
        entry["allow_empty"] = True
    return entry


def _write_meta(capture_path: Path, meta: dict[str, Any]) -> None:
    path = capture_path / "meta.json"
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finalize(
    project_root: Path,
    capture_id: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    cdir = capture_dir(project_root, capture_id)
    _write_meta(cdir, meta)
    result = validate_capture_dir(cdir)
    if not result["ok"]:
        # Leave dir for inspection; surface blocks
        raise RuntimeError(
            "capture failed validation:\n  - " + "\n  - ".join(result["blocks"])
        )
    return result


def init_project(project_root: Path | None = None) -> Path:
    root = (project_root or Path.cwd()).resolve()
    ensure_data_store(root)
    return root


def capture_command(
    command: Sequence[str],
    *,
    title: str | None = None,
    notes: str = "",
    project_root: Path | None = None,
    init: bool = False,
    extra_env: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run a command, store stdout/stderr/exit as a data capture."""
    if not command:
        raise ValueError("command must be non-empty")

    if project_root is not None:
        root = project_root.resolve()
    elif init:
        root = init_project()
    else:
        found = find_project_root()
        if found is None:
            raise FileNotFoundError(
                "No .terra/ found. Pass --init to create one in cwd."
            )
        root = found

    ensure_data_store(root)
    capture_id = _new_id()
    cdir = capture_dir(root, capture_id)
    cdir.mkdir(parents=False)

    cwd = Path.cwd()
    try:
        proc = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = (e.stderr or "") + f"\n[terra] command timed out after {timeout}s\n"
        exit_code = -1
        timed_out = True
    except FileNotFoundError:
        shutil.rmtree(cdir, ignore_errors=True)
        raise
    else:
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode
        timed_out = False

    (cdir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (cdir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (cdir / "exit_code.txt").write_text(str(exit_code) + "\n", encoding="utf-8")

    artifacts = [
        _artifact_entry(cdir, "stdout.txt", "stdout", allow_empty=True),
        _artifact_entry(cdir, "stderr.txt", "stderr", allow_empty=True),
        _artifact_entry(cdir, "exit_code.txt", "exit_code"),
    ]

    meta: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "data",
        "id": capture_id,
        "title": title or " ".join(command)[:120],
        "captured_at": _now_iso(),
        "source": {
            "type": "command",
            "command": " ".join(command),
            "argv": list(command),
            "cwd": str(cwd.resolve()),
            "exit_code": exit_code,
            "timed_out": timed_out,
        },
        "env": {"fingerprint": collect_fingerprint(cwd=cwd, extra=extra_env)},
        "artifacts": artifacts,
        "links": {
            "supports": [],
            "refutes": [],
            "unknowns": [],
            "anchors": [],
        },
        "notes": notes,
    }
    return _finalize(root, capture_id, meta)


def capture_file(
    file_path: Path,
    *,
    title: str | None = None,
    notes: str = "",
    project_root: Path | None = None,
    init: bool = False,
    extra_env: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Copy a file into the store as a data capture."""
    src = file_path.resolve()
    if not src.is_file():
        raise FileNotFoundError(f"not a file: {src}")

    if project_root is not None:
        root = project_root.resolve()
    elif init:
        root = init_project()
    else:
        found = find_project_root()
        if found is None:
            raise FileNotFoundError(
                "No .terra/ found. Pass --init to create one in cwd."
            )
        root = found

    ensure_data_store(root)
    capture_id = _new_id()
    cdir = capture_dir(root, capture_id)
    cdir.mkdir(parents=False)

    dest_name = "artifact" + (src.suffix if src.suffix else ".bin")
    dest = cdir / dest_name
    shutil.copy2(src, dest)

    meta: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "data",
        "id": capture_id,
        "title": title or src.name,
        "captured_at": _now_iso(),
        "source": {
            "type": "file",
            "path": str(src),
        },
        "env": {
            "fingerprint": collect_fingerprint(cwd=Path.cwd(), extra=extra_env)
        },
        "artifacts": [
            _artifact_entry(cdir, dest_name, "file", allow_empty=src.stat().st_size == 0),
        ],
        "links": {
            "supports": [],
            "refutes": [],
            "unknowns": [],
            "anchors": [],
        },
        "notes": notes,
    }
    # empty source file: allow_empty already set if size 0
    if src.stat().st_size == 0:
        meta["artifacts"][0]["allow_empty"] = True

    return _finalize(root, capture_id, meta)


def list_captures(project_root: Path) -> list[dict[str, Any]]:
    from .paths import data_root

    root = data_root(project_root)
    if not root.is_dir():
        return []
    out = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name.startswith("."):
            continue
        result = validate_capture_dir(child)
        title = None
        if result["meta"]:
            title = result["meta"].get("title")
        out.append(
            {
                "id": child.name,
                "ok": result["ok"],
                "title": title,
                "blocks": result["blocks"],
            }
        )
    return out
