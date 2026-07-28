"""Agent-DX fixes from the 2026-07-27 lead handbacks.

Each test encodes a failure an agent actually hit in production, not a
hypothetical. The common thread is that all of them let an agent believe
something false: a failure that reads as success, a run whose inputs are
undisclosed, a reclaim that reports the wrong reason.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from terra.brief import init_brief
from terra.paths import ensure_map_store, set_active_map_id
from terra.probe_init import init_probe
from terra.probe_run import run_probe
from terra.route import (
    HEARTBEAT_STALE_HOURS,
    add_task,
    complete_task,
    heartbeat_task,
    init_route,
    load_route,
    route_log,
    save_route,
    start_task,
)


def _env() -> dict[str, str]:
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{repo}{os.pathsep}{repo / 'src'}"
    env.pop("TERRA_MAP", None)
    return env


def _run(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "terra.cli", *argv],
        cwd=root,
        capture_output=True,
        text=True,
        env=_env(),
    )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    set_active_map_id(None)
    root = tmp_path / "proj"
    root.mkdir()
    ensure_map_store(root)
    init_brief(root, title="dx", mission="m")
    init_route(root)
    return root


# --- #4: a failure must not read as a success -----------------------------


def test_error_envelope_screams_on_stderr(project: Path) -> None:
    """`| tail` on a failure showed `"code": "route_complete"` — reads as OK.

    A lead marked three routes done this way. stdout must stay pure JSON;
    the loud marker goes to stderr.
    """
    r = _run(project, "route", "complete", "nope_not_a_task", "--evidence", "x")

    assert r.returncode == 1
    assert "TERRA ERROR" in r.stderr, "failure must be unmissable on stderr"
    assert "route_complete" in r.stderr, "marker should name the operation"
    payload = json.loads(r.stdout)
    assert payload["status"] == "error", "stdout must stay parseable JSON"


def test_success_writes_nothing_to_the_error_channel(project: Path) -> None:
    add_task(project, "a", title="A", bucket="low")
    r = _run(project, "route", "status")
    assert r.returncode == 0
    assert "TERRA ERROR" not in r.stderr


# --- #9: reclaiming a stranded lead ---------------------------------------


def _age_heartbeat(root: Path, task_id: str, hours: float) -> None:
    from datetime import datetime, timedelta, timezone

    rec = load_route(root)
    stamp = (
        (datetime.now(timezone.utc) - timedelta(hours=hours))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    for t in rec["tasks"]:
        if t["id"] == task_id:
            t["last_heartbeat_at"] = stamp
    save_route(root, rec)


def test_reclaim_stranded_task_instead_of_waiting_on_none(project: Path) -> None:
    """The message used to be `task X waiting on None` — meaningless."""
    add_task(project, "a", title="A", bucket="low")
    start_task(project, "a", agent="dead-lead")
    _age_heartbeat(project, "a", HEARTBEAT_STALE_HOURS + 1)

    t = start_task(project, "a", agent="cg-01-sim-lead")
    assert t["owner_agent"] == "cg-01-sim-lead"
    assert t["reclaimed_from"] == "dead-lead"
    assert t["status"] == "in_progress"


def test_reclaim_works_when_owner_was_never_stamped(project: Path) -> None:
    """The real case: owner_agent None, so nothing to compare against."""
    add_task(project, "a", title="A", bucket="low")
    start_task(project, "a")  # no --agent
    t = start_task(project, "a", agent="cg-01-sim-lead")
    assert t["owner_agent"] == "cg-01-sim-lead"


def test_refuses_to_steal_a_LIVE_task(project: Path) -> None:
    """Two writers on one task corrupted the master model. Must refuse."""
    add_task(project, "a", title="A", bucket="low")
    start_task(project, "a", agent="alive-lead")
    heartbeat_task(project, "a", agent="alive-lead")

    with pytest.raises(ValueError, match="ALIVE"):
        start_task(project, "a", agent="other-lead")


def test_same_agent_restart_is_just_a_heartbeat(project: Path) -> None:
    add_task(project, "a", title="A", bucket="low")
    start_task(project, "a", agent="me")
    t = start_task(project, "a", agent="me")
    assert t["owner_agent"] == "me"
    assert "reclaimed_from" not in t


# --- #7: route log --task -------------------------------------------------


def test_route_log_filters_to_one_task(project: Path) -> None:
    add_task(project, "a", title="A", bucket="low")
    add_task(project, "b", title="B", bucket="low")
    complete_task(project, "a", evidence="did A", freehand="n/a")
    complete_task(project, "b", evidence="did B", freehand="n/a")

    everything = route_log(project)
    just_a = route_log(project, task_id="a")

    assert {e["task"] for e in just_a["events"]} == {"a"}
    assert len(just_a["events"]) < len(everything["events"])

    with pytest.raises(ValueError, match="task not found"):
        route_log(project, task_id="ghost")


def test_route_log_task_flag_wired_in_cli(project: Path) -> None:
    """An advertised flag that isn't wired is worse than none."""
    add_task(project, "a", title="A", bucket="low")
    add_task(project, "b", title="B", bucket="low")
    complete_task(project, "a", evidence="did A", freehand="n/a")
    complete_task(project, "b", evidence="did B", freehand="n/a")

    r = _run(project, "route", "log", "--task", "a")
    assert r.returncode == 0
    ids = {e["task"] for e in json.loads(r.stdout)["data"]["events"]}
    assert ids == {"a"}


# --- #8: unknown get ------------------------------------------------------


def test_unknown_get_is_an_alias_for_show(project: Path) -> None:
    """`known get` exists, so agents reach for `unknown get` and got nothing;
    `unknown status` looks like the reader but is a SETTER."""
    _run(project, "unknown", "create", "u", "--type", "number",
         "--quantity", "q", "--claim", "c?", "--evidence", "e")

    got = _run(project, "unknown", "get", "u", "--json")
    shown = _run(project, "unknown", "show", "u", "--json")

    assert got.returncode == 0, got.stderr[:300]
    assert shown.returncode == 0
    assert json.loads(got.stdout) == json.loads(shown.stdout)


# --- #3: env reads are disclosed in the run record ------------------------


def _write_env_reading_probe(root: Path, probe_id: str) -> None:
    pdir = root / ".terra" / "map" / "probes" / probe_id
    (pdir / "probe.py").write_text(
        "KIND = 'watch'\n"
        "DURATION_S = 0\n"
        "REQUIRED_EXPORTS = ['to', 'status', 'artifacts']\n"
        "import os\n"
        "from pathlib import Path\n"
        "def run(ctx=None):\n"
        "    ctx = ctx or {}\n"
        "    to = ctx.get('to') or {'kind': 'default'}\n"
        "    if ctx.get('dry_run'):\n"
        "        return {'to': to, 'status': 'ok', 'artifacts': []}\n"
        "    pin = os.environ.get('COMBAT_KG_OVERRIDE')\n"
        "    secret = os.environ.get('MY_API_TOKEN')\n"
        "    p = Path(__file__).parent / 'm.txt'\n"
        "    p.write_text(str(pin))\n"
        "    return {\n"
        "        'to': to,\n"
        "        'status': 'ok',\n"
        "        'artifacts': [{'path': str(p), 'role': 'out'}],\n"
        "        'measures': [{'quantity': 'mass', 'value': float(pin or 0)}],\n"
        "    }\n",
        encoding="utf-8",
    )


def test_run_record_discloses_env_overrides(project: Path, monkeypatch) -> None:
    """A hand-pinned run must be distinguishable from a bare one.

    Declared bindings only cover known:/assumption:. A probe reading
    os.environ consumed an input the ledger never mentioned, so a forced run
    could graduate a belief and look identical to an honest one.
    """
    init_probe(project, "p", purpose="p")
    _write_env_reading_probe(project, "p")

    monkeypatch.setenv("COMBAT_KG_OVERRIDE", "10437.6")
    monkeypatch.setenv("MY_API_TOKEN", "hunter2")
    stamp = run_probe(project, "p", to={"kind": "t", "id": "1"})

    env = stamp["env_reads"]
    assert "COMBAT_KG_OVERRIDE" in env["read"], "the override must be visible"
    assert env["read"]["COMBAT_KG_OVERRIDE"] == "10437.6"
    assert env["complete"] is False, "must not overclaim subprocess coverage"


def test_env_read_values_are_redacted_for_secrets(project: Path, monkeypatch) -> None:
    init_probe(project, "p", purpose="p")
    _write_env_reading_probe(project, "p")
    monkeypatch.setenv("COMBAT_KG_OVERRIDE", "1")
    monkeypatch.setenv("MY_API_TOKEN", "hunter2")

    env = run_probe(project, "p", to={"kind": "t", "id": "1"})["env_reads"]
    assert env["read"]["MY_API_TOKEN"] == "<redacted>"
    assert "hunter2" not in json.dumps(env)


def test_bare_run_records_no_override(project: Path, monkeypatch) -> None:
    """The discriminator only works if a clean run stays clean."""
    init_probe(project, "p", purpose="p")
    _write_env_reading_probe(project, "p")
    monkeypatch.delenv("COMBAT_KG_OVERRIDE", raising=False)
    monkeypatch.delenv("MY_API_TOKEN", raising=False)

    env = run_probe(project, "p", to={"kind": "t", "id": "1"})["env_reads"]
    assert env["read"].get("COMBAT_KG_OVERRIDE") is None
    assert env["count"] <= 2


def test_os_environ_is_restored_after_a_run(project: Path) -> None:
    """A recording proxy that leaks would corrupt every later command."""
    init_probe(project, "p", purpose="p")
    _write_env_reading_probe(project, "p")
    before = type(os.environ)
    run_probe(project, "p", to={"kind": "t", "id": "1"})
    assert type(os.environ) is before
    assert os.environ.get("PATH"), "real environment must still work"


# --- run-level read provenance (the orphaned-run screening enabler) -------


def _write_ssot_reading_probe(root: Path, probe_id: str, known_id: str) -> None:
    """A probe that reads SSOT from inside its own code — the common shape."""
    pdir = root / ".terra" / "map" / "probes" / probe_id
    (pdir / "probe.py").write_text(
        "KIND = 'watch'\n"
        "DURATION_S = 0\n"
        "REQUIRED_EXPORTS = ['to', 'status', 'artifacts']\n"
        "from pathlib import Path\n"
        f"KID = {known_id!r}\n"
        "def run(ctx=None):\n"
        "    ctx = ctx or {}\n"
        "    to = ctx.get('to') or {'kind': 'default'}\n"
        "    if ctx.get('dry_run'):\n"
        "        return {'to': to, 'status': 'ok', 'artifacts': []}\n"
        "    from terra.readings import read_known\n"
        "    import os\n"
        "    r = read_known(Path(os.getcwd()), KID)\n"
        "    v = r.get('value') or r.get('mean') or 0\n"
        "    p = Path(__file__).parent / 'm.txt'\n"
        "    p.write_text(str(v))\n"
        "    return {\n"
        "        'to': to,\n"
        "        'status': 'ok',\n"
        "        'artifacts': [{'path': str(p), 'role': 'out'}],\n"
        "        'measures': [{'quantity': 'derived', 'value': float(v) * 2}],\n"
        "    }\n",
        encoding="utf-8",
    )


def _make_known(root: Path, kid: str, quantity: str, value: float) -> None:
    from terra.knowns import graduate_unknown
    from terra.unknowns import create_unknown, link_run
    from test_formula_type import _write_measure_probe

    init_probe(root, f"src_{kid}", purpose="p")
    _write_measure_probe(root, f"src_{kid}", quantity=quantity, value=value)
    rid = run_probe(root, f"src_{kid}", to={"kind": "t", "id": "1"})["id"]
    create_unknown(
        root, kid, map_type="number", quantity=quantity,
        claim="c?", evidence_needed="e",
    )
    link_run(root, kid, rid)
    graduate_unknown(root, kid)


def test_run_records_which_knowns_it_was_computed_against(
    project: Path, monkeypatch
) -> None:
    """Screening 6,000 orphaned runs by DoR basis was only possible by
    date-bucketing, because the record never said what the run consumed."""
    monkeypatch.chdir(project)
    _make_known(project, "mtow_basis", "mtow", 11986.5)
    init_probe(project, "consumer_probe", purpose="p")
    _write_ssot_reading_probe(project, "consumer_probe", "mtow_basis")

    stamp = run_probe(project, "consumer_probe", to={"kind": "t", "id": "1"})

    reads = stamp["known_reads"]
    assert reads, "a probe that read SSOT must disclose it"
    row = next(r for r in reads if r["known_id"] == "mtow_basis")
    assert row["value"] == 11986.5, "the BASIS value, not just the id"
    assert row["as_of"], "must carry the belief's as-of stamp for screening"


def test_run_with_no_ssot_reads_records_none(project: Path, monkeypatch) -> None:
    """The discriminator only works if a non-consuming run stays empty."""
    monkeypatch.chdir(project)
    from test_formula_type import _write_measure_probe

    init_probe(project, "standalone", purpose="p")
    _write_measure_probe(project, "standalone", quantity="q", value=1)
    stamp = run_probe(project, "standalone", to={"kind": "t", "id": "1"})
    assert stamp["known_reads"] == []


def test_read_sink_does_not_leak_between_runs(project: Path, monkeypatch) -> None:
    monkeypatch.chdir(project)
    _make_known(project, "mtow_basis", "mtow", 11986.5)
    init_probe(project, "consumer_probe", purpose="p")
    _write_ssot_reading_probe(project, "consumer_probe", "mtow_basis")
    from test_formula_type import _write_measure_probe

    init_probe(project, "standalone", purpose="p")
    _write_measure_probe(project, "standalone", quantity="q", value=1)

    run_probe(project, "consumer_probe", to={"kind": "t", "id": "1"})
    after = run_probe(project, "standalone", to={"kind": "t", "id": "2"})
    assert after["known_reads"] == [], "sink must not carry over"
