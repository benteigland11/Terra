"""Terra CLI — map layer: probes + unknowns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .paths import (
    ensure_map_store,
    ensure_project_root,
    ensure_probes_store,
    probe_dir,
    probes_root,
    require_project_root,
    unknown_path,
)
from .probe_init import init_probe
from .probe_run import (
    DEFAULT_RUN_TIMEOUT_S,
    list_runs,
    load_run,
    parse_to_arg,
    run_probe,
)
from .probe_validate import (
    validate_all_probes,
    validate_probe_dir,
    validate_probe_script,
)
from .run_validate import validate_all_runs, validate_run_id
from .knowns import (
    create_known,
    describe_known,
    link_run_known,
    list_knowns,
    load_known,
    promote_known,
    set_known_status,
    validate_known_file,
)
from .number_type import CONFIDENCE_SET, KNOWN_STATUSES
from .suites import (
    create_suite,
    list_suites,
    load_suite,
    parse_probe_list,
    run_suite,
    validate_all_suites,
    validate_suite,
)
from .unknown_contract import UNKNOWN_STATUSES
from .unknowns import (
    create_unknown,
    describe_unknown,
    link_probe,
    link_run,
    list_unknowns,
    load_unknown,
    set_status,
    unlink_run,
    validate_all_unknowns,
    validate_unknown_file,
)


def _print_io_steps(exercise: dict | None, *, indent: str = "  ") -> None:
    """Always print INPUT/OUTPUT (and EXECUTE) status — never silent on failure."""
    if not exercise or "steps" not in exercise:
        return
    steps = exercise["steps"]
    for name in ("input", "execute", "output"):
        step = steps.get(name) or {}
        ok = step.get("ok")
        if ok is True:
            label = "ok"
        elif ok is False:
            label = "FAIL"
        else:
            label = "—"
        print(f"{indent}{name.upper():8} {label}")
        for b in step.get("blocks") or []:
            print(f"{indent}  error: {b}")


def _print_probe_result(result: dict, *, json_out: bool) -> int:
    if json_out:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    level = result.get("level", 1)
    if "probes" in result:
        print(f"validation level {level} (input to → output to/status/artifacts)")
        for b in result.get("blocks", []):
            print(f"block: {b}")
        for p in result.get("probes", []):
            status = "ok" if p["ok"] else "FAIL"
            print(f"[{status}] {p.get('id')}")
            _print_io_steps(p.get("exercise"), indent="  ")
            for b in p.get("blocks", []):
                # avoid duplicating step errors already printed under INPUT/OUTPUT
                if "/input:" in b or "/output:" in b or "/execute:" in b:
                    continue
                print(f"  block: {b}")
            for w in p.get("warnings", []):
                print(f"  warn:  {w}")
        print("PASS" if result.get("ok") else "FAIL")
        return 0 if result.get("ok") else 1

    status = "ok" if result.get("ok") else "FAIL"
    print(f"[{status}] {result.get('id')}  (level {level})")
    if result.get("path"):
        print(f"  path:  {result['path']}")
    _print_io_steps(result.get("exercise"), indent="  ")
    for b in result.get("blocks", []):
        if "/input:" in b or "/output:" in b or "/execute:" in b:
            continue
        print(f"  block: {b}")
    for w in result.get("warnings", []):
        print(f"  warn:  {w}")
    ex = result.get("exercise")
    if ex and result.get("ok"):
        print(
            f"  exercise: status={ex.get('status')!r} "
            f"artifacts={ex.get('artifact_count')}"
        )
    print("PASS" if result.get("ok") else "FAIL")
    return 0 if result.get("ok") else 1


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve() if args.path else Path.cwd().resolve()
    ensure_map_store(root)
    print(f"initialized {root / '.terra' / 'map'}")
    print(f"  probes:   {root / '.terra' / 'map' / 'probes'}")
    print(f"  unknowns: {root / '.terra' / 'map' / 'unknowns'}")
    print(f"  runs:     {root / '.terra' / 'map' / 'runs'}")
    print(f"  lib:      {root / '.terra' / 'map' / 'lib'}")
    return 0


def cmd_probe_create(args: argparse.Namespace) -> int:
    """Scaffold a new probe package (create is the base command; init is an alias).

    Auto-creates the map store in cwd when missing.
    """
    try:
        root, created_store = ensure_project_root()
        pdir = init_probe(
            root,
            args.id,
            purpose=args.purpose,
            kind=args.kind,
            duration_s=args.duration,
            force=args.force,
        )
    except (ValueError, FileExistsError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created_store:
        print(f"initialized {root / '.terra' / 'map'}")
    print(f"created probe {args.id}  kind={args.kind}")
    print(f"  {pdir}")
    print("  next: edit probe.py, then `terra probe validate " + args.id + "`")
    return 0


def cmd_unknown_create(args: argparse.Namespace) -> int:
    try:
        root, created_store = ensure_project_root()
        path = create_unknown(
            root,
            args.id,
            claim=args.claim,
            evidence_needed=args.evidence or "",
            blocks_build=not args.no_blocks_build,
            probe_id=args.probe,
            notes=args.notes or "",
            force=args.force,
            map_type=getattr(args, "type", None),
            quantity=getattr(args, "quantity", None),
            unit=getattr(args, "unit", "") or "",
        )
    except (ValueError, FileExistsError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created_store:
        print(f"initialized {root / '.terra' / 'map'}")
    # create --probe starts in probing (same as link-probe)
    status = "probing" if args.probe else "open"
    print(f"created unknown {args.id}  status={status}")
    print(f"  {path}")
    if args.probe:
        print(f"  linked probe: {args.probe}")
    else:
        print(
            "  next: terra probe create <id> --purpose \"…\"  "
            "OR  terra unknown link-probe …"
        )
    return 0


def cmd_unknown_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_unknowns(root)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no unknowns — if stuck, create one: terra unknown create …)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        rec = r.get("record") or {}
        status = rec.get("status", "?")
        # blocks_build only meaningful while still active (open/probing/blocked)
        active = status in ("open", "probing", "blocked")
        block = (
            " blocks_build"
            if active and rec.get("blocks_build")
            else ""
        )
        claim = rec.get("claim") or ""
        print(f"[{flag}] {r['id']}  {status}{block}  {claim}")
        for b in r.get("blocks") or []:
            print(f"  block: {b}")
    return 0


def cmd_unknown_show(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        desc = describe_unknown(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(desc, indent=2, sort_keys=True, default=str))
        return 0
    rec = desc["record"]
    status = rec.get("status", "?")
    active = status in ("open", "probing", "blocked")
    block = "  blocks_build" if active and rec.get("blocks_build") else ""
    print(f"unknown {rec.get('id')}  status={status}{block}")
    print(f"claim: {rec.get('claim')}")
    print(f"evidence_needed: {rec.get('evidence_needed')}")
    pids = rec.get("probe_ids") or []
    if rec.get("probe_id") and rec.get("probe_id") not in pids:
        pids = [rec["probe_id"], *pids]
    print(f"probes: {', '.join(pids) if pids else '(none)'}")
    if rec.get("type") in ("number", "boolean"):
        st = rec.get("stats") or {}
        if rec.get("type") == "boolean":
            print(
                f"type: boolean  quantity={rec.get('quantity')}  "
                f"n={st.get('n')}  rate={st.get('rate')}  "
                f"k_true={st.get('k_true')}  k_false={st.get('k_false')}  "
                f"confidence_derived={rec.get('confidence_derived')}"
            )
        else:
            print(
                f"type: number  quantity={rec.get('quantity')}  "
                f"n={st.get('n')}  mean={st.get('mean')}  std={st.get('std')}  "
                f"confidence_derived={rec.get('confidence_derived')}"
            )
    if rec.get("resolved_by"):
        print(f"resolved_by: {rec.get('resolved_by')}")
    runs = desc.get("linked_runs") or []
    if not runs:
        print("runs: (none — terra unknown link-run <id> <run_id>)")
    else:
        print("runs:")
        for r in runs:
            flag = "ok" if r.get("exists") else "MISSING"
            prim = " primary" if r.get("primary") else ""
            print(
                f"  [{flag}] {r.get('id')}{prim}  "
                f"probe={r.get('probe_id')}  status={r.get('status')}  "
                f"{r.get('captured_at') or ''}"
            )
    return 0


def cmd_known_create(args: argparse.Namespace) -> int:
    try:
        root, created = ensure_project_root()
        path = create_known(
            root,
            args.id,
            claim=args.claim,
            quantity=args.quantity,
            map_type=getattr(args, "type", None) or "number",
            unit=args.unit or "",
            confidence=args.confidence,
            status=args.status,
            run_id=args.from_run,
            notes=args.notes or "",
            force=args.force,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    rec = load_known(root, args.id)
    st = rec.get("stats") or {}
    print(
        f"created known {args.id}  type={rec.get('type')}  "
        f"status={rec.get('status')}"
    )
    print(f"  confidence={rec.get('confidence')}  derived={rec.get('confidence_derived')}")
    if rec.get("type") == "boolean":
        print(
            f"  n={st.get('n')}  rate={st.get('rate')}  "
            f"k_true={st.get('k_true')}  k_false={st.get('k_false')}"
        )
    else:
        print(f"  n={st.get('n')}  mean={st.get('mean')}  std={st.get('std')}")
    print(f"  {path}")
    print("  next: terra known link-run …  then  terra known promote …")
    return 0


def cmd_known_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_knowns(root)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no knowns)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        rec = r.get("record") or {}
        st = rec.get("stats") or {}
        if rec.get("type") == "boolean":
            stat_s = f"n={st.get('n')}  rate={st.get('rate')}"
        else:
            stat_s = f"n={st.get('n')}  mean={st.get('mean')}"
        print(
            f"[{flag}] {r['id']}  {rec.get('type')}  {rec.get('status')}  "
            f"conf={rec.get('confidence')}/{rec.get('confidence_derived')}  "
            f"{stat_s}  {rec.get('claim', '')[:50]}"
        )
    return 0


def cmd_known_show(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        desc = describe_known(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rec = desc["record"]
    if args.json:
        print(json.dumps(rec, indent=2, sort_keys=True, default=str))
        return 0
    st = rec.get("stats") or {}
    print(f"known {rec.get('id')}  type={rec.get('type')}  status={rec.get('status')}")
    print(f"claim: {rec.get('claim')}")
    print(f"quantity: {rec.get('quantity')}  unit={rec.get('unit') or '—'}")
    print(
        f"confidence: claimed={rec.get('confidence')}  "
        f"derived={rec.get('confidence_derived')}"
    )
    if rec.get("type") == "boolean":
        print(
            f"stats: n={st.get('n')}  rate={st.get('rate')}  "
            f"k_true={st.get('k_true')}  k_false={st.get('k_false')}"
        )
    else:
        print(
            f"stats: n={st.get('n')}  mean={st.get('mean')}  std={st.get('std')}  "
            f"min={st.get('min')}  max={st.get('max')}"
        )
    print(f"run_ids: {rec.get('run_ids') or []}")
    return 0


def cmd_known_link_run(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = link_run_known(
            root, args.id, args.run_id, primary=bool(args.primary)
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    st = rec.get("stats") or {}
    if rec.get("type") == "boolean":
        print(
            f"known {rec['id']}  n={st.get('n')}  rate={st.get('rate')}  "
            f"k_true={st.get('k_true')}  conf={rec.get('confidence')}/"
            f"{rec.get('confidence_derived')}"
        )
    else:
        print(
            f"known {rec['id']}  n={st.get('n')}  mean={st.get('mean')}  "
            f"std={st.get('std')}  conf={rec.get('confidence')}/"
            f"{rec.get('confidence_derived')}"
        )
    return 0


def cmd_known_promote(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = promote_known(
            root,
            args.id,
            args.confidence,
            status=args.status,
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"known {rec['id']}  confidence={rec.get('confidence')}  "
        f"status={rec.get('status')}  derived={rec.get('confidence_derived')}"
    )
    return 0


def cmd_known_status(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = set_known_status(root, args.id, args.status, notes=args.notes)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"known {rec['id']}  status={rec['status']}")
    return 0


def cmd_known_validate(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.id:
        result = validate_known_file(root, args.id)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["ok"] else 1
        status = "ok" if result["ok"] else "FAIL"
        print(f"[{status}] {result.get('id')}")
        for b in result.get("blocks") or []:
            print(f"  block: {b}")
        print("PASS" if result["ok"] else "FAIL")
        return 0 if result["ok"] else 1
    rows = list_knowns(root)
    ok = all(r["ok"] for r in rows) if rows else True
    for r in rows:
        status = "ok" if r["ok"] else "FAIL"
        print(f"[{status}] {r['id']}")
        for b in r.get("blocks") or []:
            print(f"  block: {b}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_unknown_status(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = set_status(
            root,
            args.id,
            args.status,
            resolved_by=args.resolved_by,
            notes=args.notes,
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"unknown {rec['id']}  status={rec['status']}")
    return 0


def cmd_unknown_link_probe(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = link_probe(root, args.id, args.probe_id)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    pids = rec.get("probe_ids") or []
    print(
        f"unknown {rec['id']}  primary={rec.get('probe_id')}  "
        f"probe_ids={pids}  status={rec['status']}"
    )
    return 0


def cmd_unknown_link_run(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = link_run(
            root, args.id, args.run_id, primary=bool(args.primary)
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"unknown {rec['id']}  run_ids={rec.get('run_ids')}  "
        f"primary_run={rec.get('primary_run_id')}  status={rec['status']}"
    )
    return 0


def cmd_unknown_unlink_run(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = unlink_run(root, args.id, args.run_id)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"unknown {rec['id']}  run_ids={rec.get('run_ids')}  "
        f"primary_run={rec.get('primary_run_id')}"
    )
    return 0


def cmd_suite_create(args: argparse.Namespace) -> int:
    try:
        root, created = ensure_project_root()
        probes = parse_probe_list(args.probes)
        default_to = None
        if args.to_file:
            default_to = json.loads(Path(args.to_file).read_text(encoding="utf-8"))
        elif args.to is not None:
            default_to = parse_to_arg(args.to)
        path = create_suite(
            root,
            args.id,
            probes=probes,
            default_to=default_to,
            purpose=args.purpose or "",
            force=args.force,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    print(f"created suite {args.id}")
    print(f"  probes: {', '.join(parse_probe_list(args.probes))}")
    print(f"  {path}")
    print(f"  next: terra suite run {args.id} --to '{{…}}'")
    return 0


def cmd_suite_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_suites(root)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no suites)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        rec = r.get("record") or {}
        probes = rec.get("probes") or []
        print(f"[{flag}] {r['id']}  ({len(probes)}) {', '.join(probes)}")
    return 0


def cmd_suite_show(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = load_suite(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(rec, indent=2, sort_keys=True, default=str))
    return 0


def cmd_suite_run(args: argparse.Namespace) -> int:
    try:
        root, created = ensure_project_root()
        to = None
        if args.to_file:
            to = json.loads(Path(args.to_file).read_text(encoding="utf-8"))
        elif args.to is not None:
            to = parse_to_arg(args.to)
        timeout = args.timeout if args.timeout is not None else DEFAULT_RUN_TIMEOUT_S
        summary = run_suite(
            root,
            args.id,
            to=to,
            timeout_s=float(timeout),
            dry_run=bool(args.dry_run),
            stop_on_error=not bool(args.continue_on_error),
            strict_to=bool(getattr(args, "strict_to", False)),
            strict_status=bool(getattr(args, "strict_status", False)),
        )
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
        return 0 if summary.get("ok") else 1
    status = "ok" if summary.get("ok") else "FAIL"
    print(f"[{status}] suite {summary.get('suite_id')}")
    print(f"  to: {json.dumps(summary.get('to'), default=str)}")
    for r in summary.get("results") or []:
        if r.get("ok"):
            print(
                f"  [ok] {r.get('probe_id')}  run={r.get('run_id')}  "
                f"status={r.get('status')}"
            )
            for w in r.get("warnings") or []:
                print(f"    warn: {w}")
        else:
            print(f"  [FAIL] {r.get('probe_id')}  {r.get('error')}")
    print(f"  run_ids: {summary.get('run_ids')}")
    print("PASS" if summary.get("ok") else "FAIL")
    return 0 if summary.get("ok") else 1


def cmd_suite_validate(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.id:
        result = validate_suite(root, args.id)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["ok"] else 1
        status = "ok" if result["ok"] else "FAIL"
        print(f"[{status}] suite {result.get('id')}")
        for b in result.get("blocks") or []:
            print(f"  block: {b}")
        for p in result.get("probes") or []:
            ps = "ok" if p.get("ok") else "FAIL"
            print(f"  probe [{ps}] {p.get('id')}")
        print("PASS" if result["ok"] else "FAIL")
        return 0 if result["ok"] else 1

    result = validate_all_suites(root)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["ok"] else 1
    for s in result.get("suites") or []:
        status = "ok" if s["ok"] else "FAIL"
        print(f"[{status}] {s.get('id')}")
        for b in s.get("blocks") or []:
            print(f"  block: {b}")
    print(f"count={result.get('count', 0)}")
    print("PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


def cmd_probe_run(args: argparse.Namespace) -> int:
    """Execute a probe and stamp a run under .terra/map/runs/."""
    try:
        root = require_project_root()
        if getattr(args, "to_file", None):
            to_path = Path(args.to_file)
            to = json.loads(to_path.read_text(encoding="utf-8"))
        else:
            to = parse_to_arg(args.to)
        timeout = args.timeout if args.timeout is not None else DEFAULT_RUN_TIMEOUT_S
        stamp = run_probe(
            root,
            args.id,
            to=to,
            timeout_s=float(timeout),
            dry_run=bool(args.dry_run),
            strict_to=bool(getattr(args, "strict_to", False)),
            strict_status=bool(getattr(args, "strict_status", False)),
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        out = {k: v for k, v in stamp.items() if not str(k).startswith("_")}
        out["path"] = stamp.get("_path")
        out["run_dir"] = stamp.get("_run_dir")
        print(json.dumps(out, indent=2, default=str))
        return 0

    print(f"run {stamp['id']}")
    print(f"  probe:   {stamp.get('probe_id')}")
    print(f"  status:  {stamp.get('status')}")
    print(f"  path:    {stamp.get('_path')}")
    arts = stamp.get("artifacts") or []
    print(f"  artifacts: {len(arts)}")
    for w in stamp.get("warnings") or []:
        print(f"  warn:  {w}")
    time = stamp.get("time") or {}
    if time.get("duration_s") is not None:
        print(f"  duration_s: {time.get('duration_s')}")
    return 0


def cmd_run_validate(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.id:
        result = validate_run_id(root, args.id)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["ok"] else 1
        status = "ok" if result["ok"] else "FAIL"
        print(f"[{status}] {result.get('id')}")
        for b in result.get("blocks") or []:
            print(f"  block: {b}")
        for w in result.get("warnings") or []:
            print(f"  warn:  {w}")
        print("PASS" if result["ok"] else "FAIL")
        return 0 if result["ok"] else 1

    result = validate_all_runs(root)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["ok"] else 1
    for r in result.get("runs") or []:
        status = "ok" if r["ok"] else "FAIL"
        rec = r.get("record") or {}
        print(
            f"[{status}] {r.get('id')}  probe={rec.get('probe_id')}  "
            f"status={rec.get('status')}"
        )
        for b in r.get("blocks") or []:
            print(f"  block: {b}")
        for w in r.get("warnings") or []:
            print(f"  warn:  {w}")
    print(f"count={result.get('count', 0)}")
    print("PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


def cmd_run_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_runs(
        root,
        probe_id=getattr(args, "probe", None),
        status=getattr(args, "status", None),
    )
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no runs — terra probe run <id>)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        rec = r.get("record") or {}
        print(
            f"[{flag}] {r['id']}  probe={rec.get('probe_id')}  "
            f"status={rec.get('status')}"
        )
    return 0


def cmd_run_show(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = load_run(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(rec, indent=2, sort_keys=True, default=str))
    return 0


def cmd_unknown_validate(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.id:
        result = validate_unknown_file(unknown_path(root, args.id))
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            status = "ok" if result["ok"] else "FAIL"
            print(f"[{status}] {result['id']}")
            for b in result.get("blocks") or []:
                print(f"  block: {b}")
            print("PASS" if result["ok"] else "FAIL")
        return 0 if result["ok"] else 1

    result = validate_all_unknowns(root)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["ok"] else 1
    for u in result.get("unknowns") or []:
        status = "ok" if u["ok"] else "FAIL"
        rec = u.get("record") or {}
        print(f"[{status}] {u['id']}  {rec.get('status', '?')}")
        for b in u.get("blocks") or []:
            print(f"  block: {b}")
    print(
        f"active={result.get('active_count', 0)}  "
        f"blocking={result.get('blocking_count', 0)}"
    )
    print("PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


def cmd_probe_validate(args: argparse.Namespace) -> int:
    """Validate one probe package, all packages, or a bare .py script."""
    target = args.target

    # Bare script path
    if target and (target.endswith(".py") or Path(target).is_file()):
        path = Path(target)
        if path.is_file():
            result = validate_probe_script(
                path,
                purpose=args.purpose,
                probe_id=args.id,
            )
            return _print_probe_result(result, json_out=args.json)

    try:
        root = require_project_root()
    except FileNotFoundError as e:
        # Allow bare script without project; otherwise error
        if target and Path(target).is_file():
            result = validate_probe_script(
                Path(target), purpose=args.purpose, probe_id=args.id
            )
            return _print_probe_result(result, json_out=args.json)
        print(f"error: {e}", file=sys.stderr)
        return 1

    ensure_probes_store(root)

    if not target or target in (".", "all", "--all"):
        result = validate_all_probes(probes_root(root))
        return _print_probe_result(result, json_out=args.json)

    # Package id or path to package dir
    cand = Path(target)
    if cand.is_dir() and (cand / "probe.json").is_file():
        result = validate_probe_dir(cand)
    else:
        pdir = probe_dir(root, target)
        if not pdir.is_dir():
            print(
                f"error: unknown probe {target!r} (no {pdir})",
                file=sys.stderr,
            )
            return 1
        result = validate_probe_dir(pdir)
    return _print_probe_result(result, json_out=args.json)


def cmd_probe_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    proot = probes_root(root)
    if not proot.is_dir():
        print("(no probes directory — run terra init)")
        return 0
    rows = []
    for child in sorted(p for p in proot.iterdir() if p.is_dir()):
        if child.name.startswith("."):
            continue
        if not (child / "probe.json").is_file() and not (child / "probe.py").is_file():
            continue
        r = validate_probe_dir(child)
        rows.append(r)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no probes)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        meta = r.get("meta") or {}
        purpose = meta.get("purpose") or ""
        kind = meta.get("kind") or "?"
        extra = ""
        if kind == "watch":
            dur = meta.get("duration_s", 0)
            mode = "snapshot" if float(dur or 0) <= 0 else f"{dur}s"
            extra = f"  watch/{mode}"
        elif kind == "run":
            extra = "  run"
        print(f"[{flag}] {r.get('id')}  {kind}{extra}  {purpose}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="terra",
        description=(
            "Terra — map layer above Cartograph. "
            "Probes (instruments) + unknowns (named gaps)."
        ),
    )
    p.add_argument("--version", action="version", version=f"terra {__version__}")
    sub = p.add_subparsers(dest="group", required=True)

    p_init = sub.add_parser(
        "init", help="Create .terra/map (probes + unknowns) in this project"
    )
    p_init.add_argument(
        "path", nargs="?", default=None, help="Project directory (default: cwd)"
    )
    p_init.set_defaults(func=cmd_init)

    p_probe = sub.add_parser("probe", help="Map probes (instruments)")
    probe_sub = p_probe.add_subparsers(dest="probe_cmd", required=True)

    def _add_probe_scaffold_parser(name: str, help_text: str) -> None:
        sp = probe_sub.add_parser(name, help=help_text)
        sp.add_argument("id", help="Probe slug (e.g. env_fingerprint)")
        sp.add_argument(
            "--purpose",
            required=True,
            help="One sentence: what mystery this probe reduces",
        )
        sp.add_argument(
            "--kind",
            choices=("run", "watch"),
            default="watch",
            help="run = drive/simulate; watch = observe (duration_s=0 → snapshot)",
        )
        sp.add_argument(
            "--duration",
            type=float,
            default=None,
            dest="duration",
            help="For kind=watch only: seconds (0=snapshot, default 0; >0=stream window)",
        )
        sp.add_argument(
            "--force",
            action="store_true",
            help="Overwrite probe.json / probe.py if present",
        )
        sp.set_defaults(func=cmd_probe_create)

    _add_probe_scaffold_parser(
        "create",
        "Scaffold a new Python probe package (base create)",
    )
    _add_probe_scaffold_parser(
        "init",
        "Alias for create — scaffold a new Python probe package",
    )

    p_val = probe_sub.add_parser(
        "validate",
        help="Pseudo-validate a probe package, all probes, or a bare .py script",
    )
    p_val.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Probe id, package dir, path to .py, or omit for all",
    )
    p_val.add_argument(
        "--purpose",
        default=None,
        help="Purpose hint when validating a bare script",
    )
    p_val.add_argument(
        "--id",
        default=None,
        help="Probe id hint when validating a bare script",
    )
    p_val.add_argument("--json", action="store_true")
    p_val.set_defaults(func=cmd_probe_validate)

    p_list = probe_sub.add_parser("list", help="List probes and validation status")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_probe_list)

    p_run = probe_sub.add_parser(
        "run",
        help="Execute probe and stamp a run (time/from/to/status/artifacts)",
    )
    p_run.add_argument("id", help="Probe id")
    p_run.add_argument(
        "--to",
        default=None,
        help='Target: JSON, key=value pairs, or literal (default {"kind":"default"})',
    )
    p_run.add_argument(
        "--to-file",
        default=None,
        help="Path to JSON file for `to`",
    )
    p_run.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=f"Seconds (default {DEFAULT_RUN_TIMEOUT_S:g})",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass dry_run=True (probe should avoid live side effects)",
    )
    p_run.add_argument(
        "--strict-to",
        action="store_true",
        help="CI: fail if recommended to envelope warns (e.g. missing kind)",
    )
    p_run.add_argument(
        "--strict-status",
        action="store_true",
        help="CI: fail if status is not in recommended vocab",
    )
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=cmd_probe_run)

    p_runs = sub.add_parser("run", help="Stamped map readings")
    runs_sub = p_runs.add_subparsers(dest="run_cmd", required=True)
    p_rl = runs_sub.add_parser("list", help="List stamped runs")
    p_rl.add_argument("--probe", default=None, help="Filter by probe id")
    p_rl.add_argument(
        "--status",
        default=None,
        help=(
            "Filter by status string (recommended: ok|degraded|unavailable|"
            "empty|error — freeform values still match exactly)"
        ),
    )
    p_rl.add_argument("--json", action="store_true")
    p_rl.set_defaults(func=cmd_run_list)

    p_rv = runs_sub.add_parser("validate", help="Validate stamped run(s)")
    p_rv.add_argument("id", nargs="?", default=None, help="Run id or omit for all")
    p_rv.add_argument("--json", action="store_true")
    p_rv.set_defaults(func=cmd_run_validate)

    p_rs = runs_sub.add_parser("show", help="Show one run meta.json")
    p_rs.add_argument("id", help="Run id")
    p_rs.set_defaults(func=cmd_run_show)

    # --- unknowns ---
    p_unk = sub.add_parser(
        "unknown",
        help="Named gaps in understanding (stuck → open an unknown)",
    )
    unk_sub = p_unk.add_subparsers(dest="unknown_cmd", required=True)

    p_uc = unk_sub.add_parser("create", help="Open a new unknown (auto-inits store)")
    p_uc.add_argument("id", help="Slug id (e.g. mob_query_api)")
    p_uc.add_argument(
        "--claim",
        required=True,
        help="What we do not know (one clear sentence)",
    )
    p_uc.add_argument(
        "--evidence",
        default="",
        help="What reading would resolve this (required content for open status)",
    )
    p_uc.add_argument(
        "--type",
        default=None,
        choices=["number", "boolean"],
        dest="type",
        help="Map type (number: mean±std; boolean: rate from true/false trials)",
    )
    p_uc.add_argument(
        "--quantity",
        default=None,
        help="For typed nodes: stable measure name (e.g. hostile_count, rcon_up)",
    )
    p_uc.add_argument("--unit", default="", help="Optional unit for number type")
    p_uc.add_argument(
        "--no-blocks-build",
        action="store_true",
        help="Do not mark as blocking product build (default: blocks_build=true)",
    )
    p_uc.add_argument("--probe", default=None, help="Optional linked probe id")
    p_uc.add_argument("--notes", default="", help="Freeform notes")
    p_uc.add_argument("--force", action="store_true")
    p_uc.set_defaults(func=cmd_unknown_create)

    p_ul = unk_sub.add_parser("list", help="List unknowns")
    p_ul.add_argument("--json", action="store_true")
    p_ul.set_defaults(func=cmd_unknown_list)

    p_us = unk_sub.add_parser(
        "show", help="Show unknown + linked probes/runs (use --json for raw)"
    )
    p_us.add_argument("id")
    p_us.add_argument("--json", action="store_true", help="Machine-readable describe")
    p_us.set_defaults(func=cmd_unknown_show)

    p_ust = unk_sub.add_parser("status", help="Set status (open|probing|blocked|resolved|wont_care)")
    p_ust.add_argument("id")
    p_ust.add_argument("status", choices=sorted(UNKNOWN_STATUSES))
    p_ust.add_argument(
        "--resolved-by",
        default=None,
        help="How it was closed (required trail when status=resolved)",
    )
    p_ust.add_argument("--notes", default=None)
    p_ust.set_defaults(func=cmd_unknown_status)

    p_ulp = unk_sub.add_parser(
        "link-probe",
        help="Link a probe id (multi ok via probe_ids); sets probing if was open",
    )
    p_ulp.add_argument("id", help="Unknown id")
    p_ulp.add_argument("probe_id", help="Probe id")
    p_ulp.set_defaults(func=cmd_unknown_link_probe)

    p_ulr = unk_sub.add_parser(
        "link-run",
        help="Link a stamped run as structured evidence; sets probing if was open",
    )
    p_ulr.add_argument("id", help="Unknown id")
    p_ulr.add_argument("run_id", help="Run id under .terra/map/runs/")
    p_ulr.add_argument(
        "--primary",
        action="store_true",
        help="Set as primary_run_id (default: first link becomes primary)",
    )
    p_ulr.set_defaults(func=cmd_unknown_link_run)

    p_uur = unk_sub.add_parser("unlink-run", help="Remove a run id from an unknown")
    p_uur.add_argument("id", help="Unknown id")
    p_uur.add_argument("run_id", help="Run id to detach")
    p_uur.set_defaults(func=cmd_unknown_unlink_run)

    p_uv = unk_sub.add_parser("validate", help="Validate unknown record(s)")
    p_uv.add_argument("id", nargs="?", default=None)
    p_uv.add_argument("--json", action="store_true")
    p_uv.set_defaults(func=cmd_unknown_validate)

    # --- suites (composition recipes) ---
    p_suite = sub.add_parser(
        "suite",
        help="Ordered probe recipes (shared to; no domain plugins)",
    )
    suite_sub = p_suite.add_subparsers(dest="suite_cmd", required=True)

    p_sc = suite_sub.add_parser("create", help="Create a suite of ordered probes")
    p_sc.add_argument("id", help="Suite slug")
    p_sc.add_argument(
        "--probes",
        required=True,
        help="Comma-separated probe ids in order, e.g. a,b,c",
    )
    p_sc.add_argument(
        "--purpose",
        default="",
        help="Optional one-line purpose",
    )
    p_sc.add_argument(
        "--to",
        default=None,
        help="Optional default to (JSON / key=val) baked into the suite",
    )
    p_sc.add_argument("--to-file", default=None, help="Default to from JSON file")
    p_sc.add_argument("--force", action="store_true")
    p_sc.set_defaults(func=cmd_suite_create)

    p_sl = suite_sub.add_parser("list", help="List suites")
    p_sl.add_argument("--json", action="store_true")
    p_sl.set_defaults(func=cmd_suite_list)

    p_ss = suite_sub.add_parser("show", help="Show suite JSON")
    p_ss.add_argument("id")
    p_ss.set_defaults(func=cmd_suite_show)

    p_sr = suite_sub.add_parser(
        "run",
        help="Run each probe in order with shared --to (or suite default_to)",
    )
    p_sr.add_argument("id", help="Suite id")
    p_sr.add_argument(
        "--to",
        default=None,
        help="Shared target (overrides suite default_to)",
    )
    p_sr.add_argument("--to-file", default=None)
    p_sr.add_argument("--timeout", type=float, default=None)
    p_sr.add_argument("--dry-run", action="store_true")
    p_sr.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Do not stop suite when one probe fails",
    )
    p_sr.add_argument(
        "--strict-to",
        action="store_true",
        help="CI: fail leaf runs on to-schema warnings",
    )
    p_sr.add_argument(
        "--strict-status",
        action="store_true",
        help="CI: fail leaf runs on status-vocab warnings",
    )
    p_sr.add_argument("--json", action="store_true")
    p_sr.set_defaults(func=cmd_suite_run)

    p_sv = suite_sub.add_parser(
        "validate",
        help="Validate suite meta + level-1 each probe (no live survey)",
    )
    p_sv.add_argument("id", nargs="?", default=None, help="Suite id or omit for all")
    p_sv.add_argument("--json", action="store_true")
    p_sv.set_defaults(func=cmd_suite_validate)

    # --- knowns (typed anchors; first type: number) ---
    p_kn = sub.add_parser(
        "known",
        help="Typed anchors (number: mean±std from samples; n=1 cannot be high)",
    )
    kn_sub = p_kn.add_subparsers(dest="known_cmd", required=True)

    p_kc = kn_sub.add_parser("create", help="Create a typed known (number|boolean)")
    p_kc.add_argument("id", help="Slug id")
    p_kc.add_argument("--claim", required=True, help="Falsifiable claim")
    p_kc.add_argument(
        "--type",
        default="number",
        choices=["number", "boolean"],
        dest="type",
        help="number (mean±std) or boolean (success rate)",
    )
    p_kc.add_argument(
        "--quantity",
        required=True,
        help="Stable measure name probes put in measures[]",
    )
    p_kc.add_argument("--unit", default="", help="Optional unit")
    p_kc.add_argument(
        "--confidence",
        default="low",
        choices=sorted(CONFIDENCE_SET),
        help="Claimed confidence (capped by sample ladder; default low)",
    )
    p_kc.add_argument(
        "--status",
        default="provisional",
        choices=sorted(KNOWN_STATUSES),
    )
    p_kc.add_argument("--from-run", default=None, dest="from_run", help="Seed with a run id")
    p_kc.add_argument("--notes", default="")
    p_kc.add_argument("--force", action="store_true")
    p_kc.set_defaults(func=cmd_known_create)

    p_kl = kn_sub.add_parser("list", help="List knowns")
    p_kl.add_argument("--json", action="store_true")
    p_kl.set_defaults(func=cmd_known_list)

    p_ks = kn_sub.add_parser("show", help="Show known + stats")
    p_ks.add_argument("id")
    p_ks.add_argument("--json", action="store_true")
    p_ks.set_defaults(func=cmd_known_show)

    p_klr = kn_sub.add_parser("link-run", help="Add a sample run; recompute n/mean/std")
    p_klr.add_argument("id")
    p_klr.add_argument("run_id")
    p_klr.add_argument("--primary", action="store_true")
    p_klr.set_defaults(func=cmd_known_link_run)

    p_kp = kn_sub.add_parser(
        "promote",
        help="Raise confidence only if sample ladder allows (blocks n=1 high)",
    )
    p_kp.add_argument("id")
    p_kp.add_argument(
        "confidence",
        choices=sorted(CONFIDENCE_SET),
        help="Target confidence",
    )
    p_kp.add_argument(
        "--status",
        default=None,
        choices=sorted(KNOWN_STATUSES),
        help="Optional status (default: active when med/high from provisional)",
    )
    p_kp.set_defaults(func=cmd_known_promote)

    p_kst = kn_sub.add_parser("status", help="Set known status")
    p_kst.add_argument("id")
    p_kst.add_argument("status", choices=sorted(KNOWN_STATUSES))
    p_kst.add_argument("--notes", default=None)
    p_kst.set_defaults(func=cmd_known_status)

    p_kv = kn_sub.add_parser("validate", help="Validate known(s); recompute stats")
    p_kv.add_argument("id", nargs="?", default=None)
    p_kv.add_argument("--json", action="store_true")
    p_kv.set_defaults(func=cmd_known_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
