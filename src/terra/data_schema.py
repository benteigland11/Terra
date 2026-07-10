"""Map data capture schema (v1) and pure validation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SOURCE_TYPES = frozenset({"command", "file", "probe", "manual"})

# Accept common ISO-8601 forms (with or without fractional seconds / Z)
_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})?$"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_iso8601(value: str) -> bool:
    if not isinstance(value, str) or not _ISO_RE.match(value):
        return False
    # Normalize Z for fromisoformat
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_capture_dir(capture_path: Path) -> dict[str, Any]:
    """Validate one capture directory.

    Returns:
        {
          "ok": bool,
          "id": str | None,
          "blocks": [str, ...],
          "warnings": [str, ...],
          "meta": dict | None,
        }
    """
    blocks: list[str] = []
    warnings: list[str] = []
    meta: dict[str, Any] | None = None
    capture_path = capture_path.resolve()
    dir_name = capture_path.name

    if not capture_path.is_dir():
        return {
            "ok": False,
            "id": dir_name,
            "blocks": [f"not a directory: {capture_path}"],
            "warnings": [],
            "meta": None,
        }

    meta_path = capture_path / "meta.json"
    if not meta_path.is_file():
        blocks.append("missing meta.json")
        return {
            "ok": False,
            "id": dir_name,
            "blocks": blocks,
            "warnings": warnings,
            "meta": None,
        }

    try:
        raw = meta_path.read_text(encoding="utf-8")
        loaded = json.loads(raw)
    except json.JSONDecodeError as e:
        blocks.append(f"meta.json is not valid JSON: {e}")
        return {
            "ok": False,
            "id": dir_name,
            "blocks": blocks,
            "warnings": warnings,
            "meta": None,
        }

    if not isinstance(loaded, dict):
        blocks.append("meta.json must be a JSON object")
        return {
            "ok": False,
            "id": dir_name,
            "blocks": blocks,
            "warnings": warnings,
            "meta": None,
        }
    meta = loaded

    # schema_version
    ver = meta.get("schema_version")
    if ver != SCHEMA_VERSION:
        blocks.append(
            f"schema_version must be {SCHEMA_VERSION}, got {ver!r}"
        )

    # id
    cid = meta.get("id")
    if not isinstance(cid, str) or not cid.strip():
        blocks.append("id must be a non-empty string")
    elif cid != dir_name:
        blocks.append(
            f"id {cid!r} does not match directory name {dir_name!r}"
        )

    # kind
    kind = meta.get("kind", "data")
    if kind != "data":
        blocks.append(f"kind must be 'data', got {kind!r}")

    # captured_at
    captured_at = meta.get("captured_at")
    if not isinstance(captured_at, str) or not is_iso8601(captured_at):
        blocks.append("captured_at must be a valid ISO-8601 timestamp")

    # source
    source = meta.get("source")
    if not isinstance(source, dict):
        blocks.append("source must be an object")
    else:
        st = source.get("type")
        if st not in SOURCE_TYPES:
            blocks.append(
                f"source.type must be one of {sorted(SOURCE_TYPES)}, got {st!r}"
            )
        elif st == "command":
            if not isinstance(source.get("command"), str) or not source["command"].strip():
                blocks.append("source.command required for type=command")
        elif st == "file":
            if not isinstance(source.get("path"), str) or not source["path"].strip():
                blocks.append("source.path required for type=file")
        elif st == "probe":
            if not isinstance(source.get("probe_id"), str) or not source["probe_id"].strip():
                blocks.append("source.probe_id required for type=probe")
        # manual: no extra required fields

    # env.fingerprint
    env = meta.get("env")
    if not isinstance(env, dict):
        blocks.append("env must be an object")
    else:
        fp = env.get("fingerprint")
        if not isinstance(fp, dict) or len(fp) < 1:
            blocks.append("env.fingerprint must be a non-empty object")

    # artifacts
    artifacts = meta.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) < 1:
        blocks.append("artifacts must be a non-empty list")
    else:
        for i, art in enumerate(artifacts):
            prefix = f"artifacts[{i}]"
            if not isinstance(art, dict):
                blocks.append(f"{prefix} must be an object")
                continue
            rel = art.get("path")
            if not isinstance(rel, str) or not rel.strip():
                blocks.append(f"{prefix}.path must be a non-empty string")
                continue
            if Path(rel).is_absolute() or ".." in Path(rel).parts:
                blocks.append(
                    f"{prefix}.path must be a relative path without '..': {rel!r}"
                )
                continue
            fpath = capture_path / rel
            if not fpath.is_file():
                blocks.append(f"{prefix}: missing file {rel!r}")
                continue
            size = fpath.stat().st_size
            allow_empty = bool(art.get("allow_empty", False))
            if size == 0 and not allow_empty:
                blocks.append(
                    f"{prefix}: file {rel!r} is empty "
                    f"(set allow_empty true if intentional)"
                )
            declared = art.get("bytes")
            if declared is not None and declared != size:
                blocks.append(
                    f"{prefix}: bytes {declared} != actual size {size}"
                )
            digest = art.get("sha256")
            if digest is not None:
                actual = sha256_file(fpath)
                if not isinstance(digest, str) or digest.lower() != actual:
                    blocks.append(
                        f"{prefix}: sha256 mismatch for {rel!r}"
                    )

    # links (empty lists ok)
    links = meta.get("links")
    if links is None:
        warnings.append("links missing; treating as empty (prefer explicit lists)")
    elif not isinstance(links, dict):
        blocks.append("links must be an object")
    else:
        for key in ("supports", "refutes", "unknowns", "anchors"):
            val = links.get(key, [])
            if not isinstance(val, list):
                blocks.append(f"links.{key} must be a list")

    return {
        "ok": len(blocks) == 0,
        "id": cid if isinstance(cid, str) else dir_name,
        "blocks": blocks,
        "warnings": warnings,
        "meta": meta,
    }


def validate_store(data_root: Path) -> dict[str, Any]:
    """Validate all captures under data_root."""
    data_root = data_root.resolve()
    if not data_root.is_dir():
        return {
            "ok": False,
            "blocks": [f"data store missing: {data_root}"],
            "captures": [],
        }

    captures = []
    any_block = False
    for child in sorted(p for p in data_root.iterdir() if p.is_dir()):
        if child.name.startswith("."):
            continue
        result = validate_capture_dir(child)
        captures.append(result)
        if not result["ok"]:
            any_block = True

    store_blocks: list[str] = []
    if not captures:
        store_blocks.append("no captures in store (empty map data)")

    return {
        "ok": (not any_block) and len(store_blocks) == 0,
        "blocks": store_blocks,
        "captures": captures,
    }
