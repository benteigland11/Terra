"""known supersede: soft tombstone — keep as history, refuse as current.

Between `known set` (metadata only, can't touch a bug-derived value) and
`known delete` (destructive, dangling refs). A retired belief is refused by
the read path unless --allow-superseded, and surfaces as info in map status.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from terra.knowns import load_known, supersede_known
from terra.probe_init import init_probe
from terra.probe_run import run_probe
from terra.readings import read_known
from terra.unknowns import create_unknown, link_run
from terra.knowns import graduate_unknown


def _write_measure_probe(root: Path, probe_id: str, *, quantity: str, value: float):
    pdir = root / ".terra" / "map" / "probes" / probe_id
    (pdir / "probe.py").write_text(
        "KIND = 'watch'\nDURATION_S = 0\n"
        "REQUIRED_EXPORTS = ['to', 'status', 'artifacts']\n"
        f"Q = {quantity!r}\nV = {value!r}\n"
        "def run(ctx=None):\n"
        "    ctx = ctx or {}\n"
        "    to = ctx.get('to') or {'kind': 'default'}\n"
        "    if ctx.get('dry_run'):\n"
        "        return {'to': to, 'status': 'ok', 'artifacts': []}\n"
        "    return {'to': to, 'status': 'ok', 'artifacts': [],\n"
        "            'measures': [{'quantity': Q, 'value': V}]}\n",
        encoding="utf-8",
    )


def _mk_known(tmp_path: Path, kid: str, *, quantity="q", value=4.0) -> str:
    pid = f"p_{kid}"
    init_probe(tmp_path, pid, purpose="p")
    _write_measure_probe(tmp_path, pid, quantity=quantity, value=value)
    rid = run_probe(tmp_path, pid, to={"kind": "region"}).get("id")
    create_unknown(
        tmp_path, f"u_{kid}", claim=f"{kid}?", evidence_needed="e",
        map_type="number", quantity=quantity,
    )
    link_run(tmp_path, f"u_{kid}", rid)
    graduate_unknown(tmp_path, f"u_{kid}", known_id=kid)
    return rid


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_supersede_stamps_tombstone(proj):
    _mk_known(proj, "sm", value=-5.27)
    rec = supersede_known(proj, "sm", reason="bug-derived sign error")
    assert rec["status"] == "superseded"
    assert rec["superseded"]["reason"] == "bug-derived sign error"
    assert rec["superseded"]["refuted"] is False


def test_refuted_flag_sets_refuted_status(proj):
    _mk_known(proj, "ballast", value=99)
    rec = supersede_known(proj, "ballast", reason="never real", refuted=True)
    assert rec["status"] == "refuted"
    assert rec["superseded"]["refuted"] is True


def test_supersede_requires_reason(proj):
    _mk_known(proj, "sm", value=1)
    with pytest.raises(ValueError, match="requires --reason"):
        supersede_known(proj, "sm", reason="  ")


def test_read_refuses_superseded_by_default(proj):
    _mk_known(proj, "sm", value=-5.27)
    supersede_known(proj, "sm", reason="wrong")
    with pytest.raises(ValueError, match="SUPERSEDED"):
        read_known(proj, "sm")


def test_read_allows_superseded_with_flag_but_flags_it(proj):
    _mk_known(proj, "sm", value=-5.27)
    supersede_known(proj, "sm", reason="wrong")
    r = read_known(proj, "sm", allow_superseded=True)
    assert r["value"] == -5.27  # historical value still readable
    assert r["superseded"] is True
    assert r["superseded_info"]["reason"] == "wrong"


def test_refuted_also_refused(proj):
    _mk_known(proj, "ballast", value=99)
    supersede_known(proj, "ballast", reason="bug", refuted=True)
    with pytest.raises(ValueError, match="REFUTED"):
        read_known(proj, "ballast")


def test_by_must_exist_and_not_self(proj):
    _mk_known(proj, "sm", value=1)
    with pytest.raises(FileNotFoundError):
        supersede_known(proj, "sm", reason="x", superseded_by="ghost")
    with pytest.raises(ValueError, match="cannot supersede itself"):
        supersede_known(proj, "sm", reason="x", superseded_by="sm")


def test_by_points_at_replacement(proj):
    _mk_known(proj, "sm_old", value=-5.27)
    _mk_known(proj, "sm_new", value=5.27)
    rec = supersede_known(
        proj, "sm_old", reason="sign fixed", superseded_by="sm_new"
    )
    assert rec["superseded"]["by"] == "sm_new"
    # the refusal message should point at the replacement
    with pytest.raises(ValueError, match="sm_new"):
        read_known(proj, "sm_old")


def test_supersede_is_not_delete(proj):
    _mk_known(proj, "sm", value=1)
    supersede_known(proj, "sm", reason="wrong")
    # record still on disk (history preserved), just refused as current
    assert load_known(proj, "sm")["status"] == "superseded"


def test_map_status_flags_retired_as_info_not_debt(proj):
    from terra.map_status import agent_status_response, collect_status_board

    _mk_known(proj, "sm", value=1)
    supersede_known(proj, "sm", reason="wrong")
    board = agent_status_response(collect_status_board(proj, all_maps=True))["data"]
    retired = [
        a for a in board.get("attention") or []
        if a.get("kind") == "known_retired" and a.get("id") == "sm"
    ]
    assert len(retired) == 1
    assert retired[0]["severity"] == "info"
    # a retired known must NOT also fire high-severity unbacked/stale noise
    noisy = [
        a for a in board.get("attention") or []
        if a.get("id") == "sm" and a.get("kind") != "known_retired"
    ]
    assert not noisy


def test_gate_excludes_retired_knowns_from_debt(tmp_path: Path, monkeypatch):
    """Retiring a mis-wired gate must CLEAR its violation.

    Otherwise the only way to green the gate is `known delete`, which destroys
    the audit trail — the gate would reward erasing a mistake over recording
    it. Real case 2026-07-27: a tautologically-false flutter formula was
    correctly superseded with a full reason and `terra gate` kept counting it.
    """
    monkeypatch.chdir(tmp_path)
    from terra.gate import check_gate
    from terra.knowns import create_known, link_run_known
    from terra.probe_run import run_probe
    from test_formula_type import _write_measure_probe

    init_probe(tmp_path, "p", purpose="p")
    _write_measure_probe(tmp_path, "p", quantity="hostile_count", value=50)
    run_ids = [
        run_probe(tmp_path, "p", to={"kind": "region", "id": str(i)}).get("id")
        for i in range(5)
    ]
    create_known(
        tmp_path,
        "sparse",
        claim="under 10",
        map_type="formula",
        expression="mean(h) <= 10",
        vars=["h=hostile_count"],
        run_id=run_ids[0],
    )
    for rid in run_ids[1:]:
        link_run_known(tmp_path, "sparse", rid)

    before = check_gate(tmp_path)
    assert any(
        v["kind"] == "known_formula_failed" and v["id"] == "sparse"
        for v in before["violations"]
    ), "precondition: the failing formula must be a violation"

    supersede_known(tmp_path, "sparse", reason="mis-wired gate, tautological")

    after = check_gate(tmp_path)
    assert not any(
        v["id"] == "sparse" for v in after["violations"]
    ), "a retired belief must not remain gate debt"
    assert any(
        n["kind"] == "known_retired" and n["id"] == "sparse"
        for n in after["notices"]
    ), "it must still be VISIBLE as a notice — retired, not vanished"
