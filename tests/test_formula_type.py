"""Formula type: observation as checkable expression + vars."""

from __future__ import annotations

from pathlib import Path

import pytest

from terra.formula_type import evaluate_expression, parse_vars_arg
from terra.knowns import create_known, link_run_known, load_known, promote_known
from terra.probe_init import init_probe
from terra.probe_run import run_probe


def _write_measure_probe(root: Path, probe_id: str, *, quantity: str, value) -> None:
    pdir = root / ".terra" / "map" / "probes" / probe_id
    (pdir / "probe.py").write_text(
        "KIND = 'watch'\n"
        "DURATION_S = 0\n"
        "REQUIRED_EXPORTS = ['to', 'status', 'artifacts']\n"
        "from pathlib import Path\n"
        f"Q = {quantity!r}\n"
        f"V = {value!r}\n"
        "def run(ctx=None):\n"
        "    ctx = ctx or {}\n"
        "    to = ctx.get('to') or {'kind': 'default'}\n"
        "    if ctx.get('dry_run'):\n"
        "        return {'to': to, 'status': 'ok', 'artifacts': []}\n"
        "    p = Path(__file__).parent / 'm.txt'\n"
        "    p.write_text(str(V))\n"
        "    return {\n"
        "        'to': to,\n"
        "        'status': 'ok',\n"
        "        'artifacts': [{'path': str(p), 'role': 'out'}],\n"
        "        'measures': [{'quantity': Q, 'value': V}],\n"
        "    }\n",
        encoding="utf-8",
    )


def test_eval_mean_le():
    val, binds = evaluate_expression("mean(h) <= 10", {"h": [3.0, 5.0, 7.0]})
    assert val is True
    assert binds["mean(h)"] == 5.0


def test_eval_disallows_call():
    with pytest.raises(ValueError, match="simple function|unknown function|disallowed"):
        evaluate_expression("__import__('os').system('x')", {})


def test_parse_vars():
    v = parse_vars_arg(["h=hostile_count", "b=rcon_up:boolean"])
    assert v["h"]["quantity"] == "hostile_count"
    assert v["b"]["kind"] == "boolean"


def test_known_formula_holds_and_promote(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_probe(tmp_path, "p", purpose="p")
    _write_measure_probe(tmp_path, "p", quantity="hostile_count", value=4)
    r1 = run_probe(tmp_path, "p", to={"kind": "region", "id": "a"}).get("id")
    _write_measure_probe(tmp_path, "p", quantity="hostile_count", value=6)
    r2 = run_probe(tmp_path, "p", to={"kind": "region", "id": "b"}).get("id")
    _write_measure_probe(tmp_path, "p", quantity="hostile_count", value=5)
    r3 = run_probe(tmp_path, "p", to={"kind": "region", "id": "c"}).get("id")

    create_known(
        tmp_path,
        "sparse",
        claim="Hostiles stay sparse",
        map_type="formula",
        expression="mean(h) <= 10 and n(h) >= 3",
        vars=["h=hostile_count"],
        run_id=r1,
    )
    link_run_known(tmp_path, "sparse", r2)
    rec = link_run_known(tmp_path, "sparse", r3)
    assert rec["stats"]["holds"] is True
    assert rec["stats"]["n"] == 3
    assert rec["confidence_derived"] == "med"
    rec2 = promote_known(tmp_path, "sparse", "med")
    assert rec2["confidence"] == "med"


def test_known_formula_fails_blocks_promote(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_probe(tmp_path, "p", purpose="p")
    _write_measure_probe(tmp_path, "p", quantity="hostile_count", value=50)
    rid = run_probe(tmp_path, "p", to={"kind": "region"}).get("id")
    create_known(
        tmp_path,
        "sparse",
        claim="under 10",
        map_type="formula",
        expression="mean(h) <= 10",
        vars=["h=hostile_count"],
        run_id=rid,
    )
    rec = load_known(tmp_path, "sparse")
    assert rec["stats"]["holds"] is False
    with pytest.raises(ValueError, match="confidence|hold"):
        promote_known(tmp_path, "sparse", "med")
