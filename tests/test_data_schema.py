"""Validation hard bar for map data captures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from terra.data_schema import SCHEMA_VERSION, sha256_file, validate_capture_dir, validate_store


def _write_capture(
    root: Path,
    capture_id: str,
    *,
    meta: dict | None = None,
    files: dict[str, str] | None = None,
) -> Path:
    cdir = root / capture_id
    cdir.mkdir(parents=True)
    files = files or {"stdout.txt": "hello\n"}
    for name, content in files.items():
        (cdir / name).write_text(content, encoding="utf-8")
    if meta is None:
        art_path = next(iter(files))
        fpath = cdir / art_path
        meta = {
            "schema_version": SCHEMA_VERSION,
            "kind": "data",
            "id": capture_id,
            "title": "t",
            "captured_at": "2026-07-10T12:00:00Z",
            "source": {"type": "manual"},
            "env": {"fingerprint": {"cwd": "/tmp"}},
            "artifacts": [
                {
                    "path": art_path,
                    "role": "stdout",
                    "bytes": fpath.stat().st_size,
                    "sha256": sha256_file(fpath),
                }
            ],
            "links": {
                "supports": [],
                "refutes": [],
                "unknowns": [],
                "anchors": [],
            },
            "notes": "",
        }
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return cdir


def test_valid_capture_passes(tmp_path: Path):
    cdir = _write_capture(tmp_path, "cap-ok")
    result = validate_capture_dir(cdir)
    assert result["ok"] is True
    assert result["blocks"] == []


def test_missing_meta_blocks(tmp_path: Path):
    cdir = tmp_path / "x"
    cdir.mkdir()
    (cdir / "stdout.txt").write_text("a", encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("meta.json" in b for b in result["blocks"])


def test_id_must_match_dirname(tmp_path: Path):
    cdir = _write_capture(tmp_path, "dir-a")
    meta = json.loads((cdir / "meta.json").read_text())
    meta["id"] = "dir-b"
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("does not match" in b for b in result["blocks"])


def test_empty_artifact_blocks_without_flag(tmp_path: Path):
    cdir = _write_capture(
        tmp_path,
        "empty-art",
        files={"stdout.txt": ""},
    )
    # rewrite meta with empty file hash
    fpath = cdir / "stdout.txt"
    meta = {
        "schema_version": SCHEMA_VERSION,
        "kind": "data",
        "id": "empty-art",
        "captured_at": "2026-07-10T12:00:00Z",
        "source": {"type": "manual"},
        "env": {"fingerprint": {"cwd": "/tmp"}},
        "artifacts": [
            {
                "path": "stdout.txt",
                "role": "stdout",
                "bytes": 0,
                "sha256": sha256_file(fpath),
            }
        ],
        "links": {
            "supports": [],
            "refutes": [],
            "unknowns": [],
            "anchors": [],
        },
    }
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("empty" in b for b in result["blocks"])


def test_empty_artifact_ok_with_flag(tmp_path: Path):
    cdir = tmp_path / "empty-ok"
    cdir.mkdir()
    (cdir / "stdout.txt").write_text("", encoding="utf-8")
    fpath = cdir / "stdout.txt"
    meta = {
        "schema_version": SCHEMA_VERSION,
        "kind": "data",
        "id": "empty-ok",
        "captured_at": "2026-07-10T12:00:00Z",
        "source": {"type": "manual"},
        "env": {"fingerprint": {"cwd": "/tmp"}},
        "artifacts": [
            {
                "path": "stdout.txt",
                "role": "stdout",
                "bytes": 0,
                "sha256": sha256_file(fpath),
                "allow_empty": True,
            }
        ],
        "links": {
            "supports": [],
            "refutes": [],
            "unknowns": [],
            "anchors": [],
        },
    }
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is True


def test_sha256_mismatch_blocks(tmp_path: Path):
    cdir = _write_capture(tmp_path, "bad-hash")
    meta = json.loads((cdir / "meta.json").read_text())
    meta["artifacts"][0]["sha256"] = "0" * 64
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("sha256" in b for b in result["blocks"])


def test_command_source_requires_command(tmp_path: Path):
    cdir = _write_capture(tmp_path, "cmd")
    meta = json.loads((cdir / "meta.json").read_text())
    meta["source"] = {"type": "command"}
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("source.command" in b for b in result["blocks"])


def test_empty_fingerprint_blocks(tmp_path: Path):
    cdir = _write_capture(tmp_path, "nofp")
    meta = json.loads((cdir / "meta.json").read_text())
    meta["env"] = {"fingerprint": {}}
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    result = validate_capture_dir(cdir)
    assert result["ok"] is False
    assert any("fingerprint" in b for b in result["blocks"])


def test_validate_store_empty(tmp_path: Path):
    store = tmp_path / "data"
    store.mkdir()
    result = validate_store(store)
    assert result["ok"] is False
    assert any("no captures" in b for b in result["blocks"])


def test_validate_store_with_good_capture(tmp_path: Path):
    _write_capture(tmp_path, "one")
    result = validate_store(tmp_path)
    assert result["ok"] is True
