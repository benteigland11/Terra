"""Capture path: command + file → valid store entries."""

from __future__ import annotations

from pathlib import Path

from terra.data_capture import capture_command, capture_file, list_captures
from terra.data_schema import validate_store
from terra.paths import data_root


def test_capture_command(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = capture_command(
        ["python", "-c", "print('hello-map')"],
        title="hello",
        init=True,
    )
    assert result["ok"] is True
    assert (tmp_path / ".terra" / "map" / "data" / result["id"]).is_dir()
    store = validate_store(data_root(tmp_path))
    assert store["ok"] is True


def test_capture_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "reading.txt"
    src.write_text("env dump\n", encoding="utf-8")
    result = capture_file(src, title="reading", init=True)
    assert result["ok"] is True
    rows = list_captures(tmp_path)
    assert len(rows) == 1
    assert rows[0]["ok"] is True
