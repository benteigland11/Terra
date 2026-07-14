"""Terra CLI — map layer: probes + unknowns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .paths import (
    GLOBAL_MAP_ID,
    create_session_map,
    ensure_map_store,
    ensure_project_root,
    ensure_probes_store,
    get_active_map_id,
    list_maps,
    map_root,
    probe_dir,
    probes_root,
    require_project_root,
    set_active_map_id,
    unknown_path,
    write_active_map,
)
from .probe_init import init_probe
from .probe_run import (
    DEFAULT_RUN_TIMEOUT_S,
    delete_run,
    list_runs,
    load_run,
    parse_to_arg,
    run_probe,
    unvoid_run,
    void_run,
)
from .probe_validate import (
    validate_all_probes,
    validate_probe_dir,
    validate_probe_script,
)
from .run_validate import validate_all_runs, validate_run_id
from .knowns import (
    create_known,
    delete_known,
    describe_known,
    link_run_known,
    list_knowns,
    load_known,
    promote_known,
    set_known,
    set_known_status,
    unlink_run_known,
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
    delete_unknown,
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
    print(f"initialized {root / '.terra' / 'map'}  (global map)")
    print(f"  probes+lib: global shared")
    print(f"  active map: {get_active_map_id(root)}")
    print(f"  belief path: {map_root(root)}")
    print("  tip: terra map create <exp> --use  # experiment-scoped knowns/runs")
    return 0


def cmd_map_create(args: argparse.Namespace) -> int:
    try:
        root, created = ensure_project_root()
        path = create_session_map(
            root,
            args.id,
            purpose=args.purpose or "",
            use=bool(args.use),
            force=bool(args.force),
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    print(f"created map {args.id}  (session)")
    print(f"  {path}")
    print("  probes/lib stay global; unknowns/knowns/runs/suites are scoped here")
    if args.use:
        print(f"  active map → {args.id}")
    else:
        print(f"  use: terra map use {args.id}   or  --map {args.id}")
    return 0


def cmd_map_list(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_maps(root)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    for r in rows:
        star = "*" if r.get("active") else " "
        print(
            f"{star} [{r.get('kind')}] {r.get('id')}  "
            f"{r.get('purpose') or ''}"
        )
    print(f"active: {get_active_map_id(root)}")
    return 0


def cmd_map_use(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        write_active_map(root, args.id)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"active map → {get_active_map_id(root)}")
    print(f"  belief path: {map_root(root)}")
    return 0


def cmd_map_show(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    mid = get_active_map_id(root)
    info = {
        "active": mid,
        "belief_path": str(map_root(root)),
        "probes_path": str(probes_root(root)),
        "maps": list_maps(root),
    }
    if args.json:
        print(json.dumps(info, indent=2, default=str))
        return 0
    print(f"active map: {mid}")
    print(f"  beliefs (unknowns/knowns/runs/suites): {map_root(root)}")
    print(f"  probes+lib (always global): {probes_root(root)}")
    print("  board: terra map status   (or --html)")
    return 0


def cmd_brief_init(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import brief_summary, init_brief, load_brief

    try:
        root, _ = ensure_project_root()
        init_brief(
            root,
            title=args.title,
            mission=args.mission or "",
            force=bool(args.force),
        )
        rec = load_brief(root)
    except (ValueError, FileExistsError, OSError) as e:
        return emit(error(str(e), code="brief_init"))
    return emit(success(brief_summary(rec), meta={"surface": "terra.brief.init"}))


def cmd_brief_show(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import brief_summary, load_brief

    try:
        root = require_project_root()
        rec = load_brief(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_show"))
    if args.human:
        print(f"brief v{rec.get('version')}  status={rec.get('status')}")
        print(f"title: {rec.get('title')}")
        print(f"mission: {rec.get('mission') or '—'}")
        bp = rec.get("budget_points")
        bn = rec.get("budget_notes") or ""
        print(f"budget_points: {bp if bp is not None else '—'}  (task buckets: low=3 medium=8 high=21)")
        if bn:
            print(f"budget_notes: {bn}")
        print(f"needs: {rec.get('needs') or []}")
        print(f"non_goals: {rec.get('non_goals') or []}")
        print(f"deliverables: {rec.get('deliverables') or []}")
        ens = rec.get("enablers") or []
        if ens:
            print("enablers (internal tooling — not customer pack):")
            for e in ens:
                print(
                    f"  • [{e.get('status')}] {e.get('id')}  {e.get('title')}  "
                    f"path={e.get('path') or '—'}"
                )
        else:
            print("enablers: []")
        print(f"phases: {[p.get('id') for p in (rec.get('phases') or [])]}")
        print(f"change_control: {rec.get('change_control')}")
        return 0
    data = rec if args.full else brief_summary(rec)
    return emit(success(data, meta={"surface": "terra.brief.show"}))


def cmd_brief_set(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import brief_summary, set_brief_fields

    try:
        root = require_project_root()
        rec = set_brief_fields(
            root,
            title=args.title,
            mission=args.mission,
            status=args.status,
            budget_points=getattr(args, "budget_points", None),
            clear_budget_points=bool(getattr(args, "clear_budget_points", False)),
            budget_notes=getattr(args, "budget_notes", None),
            needs=args.needs,
            non_goals=args.non_goals,
            deliverables=args.deliverables,
            enablers=getattr(args, "enablers", None),
            replace_lists=bool(args.replace_lists),
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_set"))
    return emit(success(brief_summary(rec), meta={"surface": "terra.brief.set"}))


def cmd_brief_phase(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import add_phase, brief_summary

    try:
        root = require_project_root()
        rec = add_phase(root, args.id, title=args.title or "")
    except (FileNotFoundError, ValueError, FileExistsError, OSError) as e:
        return emit(error(str(e), code="brief_phase"))
    return emit(success(brief_summary(rec), meta={"surface": "terra.brief.phase"}))


def cmd_brief_propose(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import propose_change

    try:
        root = require_project_root()
        prop = propose_change(
            root,
            summary=args.summary,
            need=args.need,
            non_goal=args.non_goal,
            deliverable=args.deliverable,
            enabler=getattr(args, "enabler", None),
            mission=args.mission,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_propose"))
    return emit(success(prop, meta={"surface": "terra.brief.propose"}))


def cmd_brief_accept(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import accept_proposal, brief_summary

    try:
        root = require_project_root()
        rec = accept_proposal(root, args.id)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_accept"))
    return emit(success(brief_summary(rec), meta={"surface": "terra.brief.accept"}))


def cmd_brief_reject(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import brief_summary, reject_proposal

    try:
        root = require_project_root()
        rec = reject_proposal(root, args.id)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_reject"))
    return emit(success(brief_summary(rec), meta={"surface": "terra.brief.reject"}))


def cmd_brief_enabler(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .brief import brief_summary, set_enabler_status

    try:
        root = require_project_root()
        rec = set_enabler_status(
            root,
            args.id,
            args.status,
            path=args.path,
            graduates_to=args.graduates_to,
            notes=args.notes,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="brief_enabler"))
    ens = [e for e in (rec.get("enablers") or []) if e.get("id") == args.id]
    return emit(
        success(
            {"enabler": ens[0] if ens else None, "brief": brief_summary(rec)},
            meta={"surface": "terra.brief.enabler"},
        )
    )


def cmd_route_init(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import init_route, route_status

    try:
        root, _ = ensure_project_root()
        init_route(root, force=bool(args.force))
        st = route_status(root)
    except (ValueError, FileExistsError, OSError) as e:
        return emit(error(str(e), code="route_init"))
    return emit(success(st, meta={"surface": "terra.route.init"}))


def cmd_route_status(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import route_status

    try:
        root = require_project_root()
        st = route_status(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_status"))
    if args.human:
        c = st.get("counts") or {}
        print(f"route  tasks={c.get('tasks')}  pickable={c.get('pickable')}  "
              f"in_progress={c.get('in_progress')}  blocked={c.get('blocked')}  "
              f"done={c.get('done')}")
        b = st.get("budget") or {}
        _print_budget_human(b)
        print("next:")
        for t in st.get("next") or []:
            pts = t.get("points")
            bkt = t.get("bucket")
            weight = f"  {bkt}/{pts}pt" if bkt or pts else ""
            print(f"  • {t.get('id')}  [{t.get('status')}]  skill={t.get('skill')}{weight}  "
                  f"{t.get('title')}")
        return 0
    return emit(success(st, meta={"surface": "terra.route.status"}))


def _print_budget_human(b: dict) -> None:
    if (
        b.get("budget_points") is None
        and not b.get("points_actual")
        and not b.get("points_plan")
        and not b.get("points_planned")
        and not b.get("sectors")
    ):
        return
    flags = []
    if b.get("plan_locked"):
        flags.append("PLAN LOCKED")
    if b.get("over_budget"):
        flags.append("OVER BUDGET")
    if b.get("over_plan"):
        flags.append("OVER PLAN")
    flag_s = ("  " + " ".join(flags)) if flags else ""
    plan = b.get("points_plan")
    actual = b.get("points_actual", b.get("points_planned"))
    print(
        f"budget  total={b.get('budget_points') if b.get('budget_points') is not None else '—'}  "
        f"plan={plan}  actual={actual}  done={b.get('points_done')}  "
        f"free_pool={b.get('free_pool') if b.get('free_pool') is not None else '—'}  "
        f"sector_reserved={b.get('sector_reserved_total')}  "
        f"var={b.get('variance_actual_minus_plan')}  "
        f"(low=3 medium=8 high=21){flag_s}"
    )
    if b.get("plan_locked_at"):
        print(f"  plan_locked_at={b.get('plan_locked_at')}")
    for s in b.get("sectors") or []:
        over = " OVER_RESERVE" if s.get("over_reserve") else ""
        print(
            f"  sector {s.get('id')}: reserved={s.get('reserved_points')}  "
            f"plan={s.get('points_plan')}  actual={s.get('points_actual')}  "
            f"remain_plan={s.get('remaining_reserve_plan')}{over}  "
            f"— {s.get('title')}"
        )
    if b.get("tasks_without_points"):
        print(f"  tasks_without_points={b.get('tasks_without_points')}")


def cmd_route_budget(args: argparse.Namespace) -> int:
    """Agent-friendly budget-only view (same numbers as route status)."""
    from .agent_io import emit, error, success
    from .route import route_status

    try:
        root = require_project_root()
        st = route_status(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_budget"))
    b = st.get("budget") or {}
    # include compact task weights for allocation visibility
    tasks = []
    for t in st.get("tasks") or []:
        if t.get("status") == "cancelled":
            continue
        tasks.append(
            {
                "id": t.get("id"),
                "status": t.get("status"),
                "sector_id": t.get("sector_id"),
                "bucket": t.get("bucket"),
                "points": t.get("points"),
                "plan_bucket": t.get("plan_bucket"),
                "plan_points": t.get("plan_points"),
                "title": t.get("title"),
            }
        )
    data = {**b, "tasks": tasks}
    if args.human:
        _print_budget_human(b)
        for t in tasks:
            sec = f" sector={t.get('sector_id')}" if t.get("sector_id") else ""
            w = (
                f"plan={t.get('plan_bucket')}/{t.get('plan_points')}pt "
                f"actual={t.get('bucket')}/{t.get('points')}pt"
                if t.get("points") is not None or t.get("plan_points") is not None
                else "unset"
            )
            print(
                f"  • {t.get('id')}  [{t.get('status')}]{sec}  {w}  {t.get('title')}"
            )
        return 0
    return emit(success(data, meta={"surface": "terra.route.budget"}))


def cmd_route_set_effort(args: argparse.Namespace) -> int:
    """Re-bucket a task; may exceed budget when plan is locked."""
    from .agent_io import emit, error, success
    from .route import route_status, set_task_effort

    try:
        root = require_project_root()
        t = set_task_effort(
            root,
            args.id,
            bucket=getattr(args, "bucket", None),
            points=getattr(args, "points", None),
        )
        st = route_status(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_set_effort"))
    payload = {"task": t, "budget": st.get("budget")}
    if args.human:
        print(
            f"set {t.get('id')} → actual={t.get('bucket')}/{t.get('points')}pt "
            f"plan={t.get('plan_bucket')}/{t.get('plan_points')}pt "
            f"(plan_locked={st.get('plan_locked')})"
        )
        _print_budget_human(st.get("budget") or {})
        return 0
    return emit(success(payload, meta={"surface": "terra.route.set_effort"}))


def cmd_route_sector_add(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import add_sector, route_status

    try:
        root = require_project_root()
        sec = add_sector(
            root,
            args.id,
            title=args.title,
            reserved_points=int(args.points),
            notes=args.notes or "",
        )
        st = route_status(root)
    except (FileNotFoundError, ValueError, FileExistsError, OSError) as e:
        return emit(error(str(e), code="route_sector_add"))
    if args.human:
        print(
            f"sector {sec.get('id')} reserved={sec.get('reserved_points')}  "
            f"{sec.get('title')}"
        )
        _print_budget_human(st.get("budget") or {})
        return 0
    return emit(
        success({"sector": sec, "budget": st.get("budget")}, meta={"surface": "terra.route.sector_add"})
    )


def cmd_route_sector_set(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import route_status, set_sector_reserve

    try:
        root = require_project_root()
        sec = set_sector_reserve(
            root,
            args.id,
            reserved_points=args.points,
            title=args.title,
            notes=args.notes,
        )
        st = route_status(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_sector_set"))
    if args.human:
        print(
            f"sector {sec.get('id')} reserved={sec.get('reserved_points')}  "
            f"{sec.get('title')}"
        )
        _print_budget_human(st.get("budget") or {})
        return 0
    return emit(
        success({"sector": sec, "budget": st.get("budget")}, meta={"surface": "terra.route.sector_set"})
    )


def cmd_route_lock_plan(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import lock_plan

    try:
        root = require_project_root()
        out = lock_plan(root)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_lock_plan"))
    if args.human:
        print(out.get("message"))
        _print_budget_human(out.get("budget") or {})
        return 0
    return emit(success(out, meta={"surface": "terra.route.lock_plan"}))


def cmd_route_unlock_plan(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import unlock_plan

    try:
        root = require_project_root()
        out = unlock_plan(root, confirm=bool(args.confirm))
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_unlock_plan"))
    if args.human:
        print(out.get("message"))
        _print_budget_human(out.get("budget") or {})
        return 0
    return emit(success(out, meta={"surface": "terra.route.unlock_plan"}))


def cmd_route_next(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import next_tasks

    try:
        root = require_project_root()
        tasks = next_tasks(root, limit=int(args.limit or 5))
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_next"))
    if args.human:
        if not tasks:
            print("(no pickable tasks)")
            return 0
        for t in tasks:
            pts = t.get("points")
            bkt = t.get("bucket")
            weight = f"  {bkt}/{pts}pt" if bkt or pts else ""
            print(
                f"{t.get('id')}  [{t.get('status')}]  skill={t.get('skill')}{weight}  "
                f"{t.get('title')}"
            )
        return 0
    return emit(
        success(
            {"command": "route.next", "tasks": tasks},
            meta={"surface": "terra.route.next"},
        )
    )


def cmd_route_add(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import add_task

    try:
        root = require_project_root()
        t = add_task(
            root,
            args.id,
            title=args.title,
            phase=args.phase or "",
            deps=args.deps or [],
            skill=args.skill or "any",
            role=getattr(args, "role", None) or "any",
            enabler_id=getattr(args, "enabler_id", None),
            acceptance=args.acceptance or [],
            map_id=args.task_map,
            bucket=getattr(args, "bucket", None),
            points=getattr(args, "points", None),
            sector_id=getattr(args, "sector_id", None),
        )
    except (FileNotFoundError, ValueError, FileExistsError, OSError) as e:
        return emit(error(str(e), code="route_add"))
    return emit(success(t, meta={"surface": "terra.route.add"}))


def cmd_route_start(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import start_task

    try:
        root = require_project_root()
        t = start_task(root, args.id)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_start"))
    return emit(success(t, meta={"surface": "terra.route.start"}))


def cmd_route_complete(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import complete_task

    try:
        root = require_project_root()
        t = complete_task(root, args.id, evidence=args.evidence)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_complete"))
    return emit(success(t, meta={"surface": "terra.route.complete"}))


def cmd_route_block(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import block_task

    try:
        root = require_project_root()
        t = block_task(root, args.id, reason=args.reason)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_block"))
    return emit(success(t, meta={"surface": "terra.route.block"}))


def cmd_route_unblock(args: argparse.Namespace) -> int:
    from .agent_io import emit, error, success
    from .route import unblock_task

    try:
        root = require_project_root()
        t = unblock_task(root, args.id)
    except (FileNotFoundError, ValueError, OSError) as e:
        return emit(error(str(e), code="route_unblock"))
    return emit(success(t, meta={"surface": "terra.route.unblock"}))


def cmd_map_status(args: argparse.Namespace) -> int:
    """Map board — agent-first (JSON default, like cartograph status).

    Human pretty-print: --human. Browser: --html / --open.
    """
    from .agent_io import emit, error
    from .map_status import (
        agent_status_response,
        collect_status_board,
        format_status_text,
        write_status_html,
    )

    try:
        root = require_project_root()
        board = collect_status_board(
            root,
            all_maps=bool(args.all),
            map_id=getattr(args, "map_scope", None),
        )
    except FileNotFoundError as e:
        return emit(error(str(e), code="no_project"))

    want_html = bool(args.html) or bool(args.open)
    if want_html:
        out_path = Path(args.output) if args.output else None
        path = write_status_html(root, board, path=out_path)
        # Still agent-envelope for path so agents can open it if needed
        if not getattr(args, "human", False):
            return emit(
                agent_status_response(
                    {
                        **board,
                        "html_path": str(path),
                    }
                )
            )
        print(f"wrote {path}")
        if args.open:
            import webbrowser

            webbrowser.open(path.resolve().as_uri())
            print("opened in browser")
        return 0

    if getattr(args, "human", False):
        print(format_status_text(board), end="")
        return 0

    # Default: machine-first JSON (Cartograph status precedent)
    return emit(agent_status_response(board))


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
            expression=getattr(args, "expression", None),
            vars=getattr(args, "vars", None),
        )
    except (ValueError, FileExistsError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created_store:
        print(f"initialized {root / '.terra' / 'map'}")
    # create --probe starts in probing (same as link-probe)
    status = "probing" if args.probe else "open"
    print(f"created unknown {args.id}  status={status}")
    if getattr(args, "type", None) == "formula":
        print(f"  type=formula  expr={getattr(args, 'expression', '')!r}")
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
    if rec.get("type") in ("number", "boolean", "formula"):
        st = rec.get("stats") or {}
        if rec.get("type") == "formula":
            print(
                f"type: formula  expr={rec.get('expression')!r}  "
                f"holds={st.get('holds')}  holds_rate={st.get('holds_rate')}  "
                f"n={st.get('n')}  conf_derived={rec.get('confidence_derived')}"
            )
            print(f"vars: {rec.get('vars')}")
        elif rec.get("type") == "boolean":
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


def _print_known_summary(prefix: str, rec: dict, path: Path | None = None) -> None:
    st = rec.get("stats") or {}
    print(
        f"{prefix} known {rec.get('id')}  type={rec.get('type')}  "
        f"status={rec.get('status')}"
    )
    print(
        f"  confidence={rec.get('confidence')}  "
        f"derived={rec.get('confidence_derived')}"
    )
    if rec.get("type") == "formula":
        print(f"  expression: {rec.get('expression')}")
        print(f"  vars: {rec.get('vars')}")
        print(
            f"  holds={st.get('holds')}  holds_rate={st.get('holds_rate')}  "
            f"n={st.get('n')}"
        )
    elif rec.get("type") == "boolean":
        print(
            f"  n={st.get('n')}  rate={st.get('rate')}  "
            f"k_true={st.get('k_true')}  k_false={st.get('k_false')}"
        )
    else:
        print(f"  n={st.get('n')}  mean={st.get('mean')}  std={st.get('std')}")
    if path is not None:
        print(f"  {path}")


_KNOWN_BIRTH_MSG = (
    "`terra known create` is retired — knowns are born by graduating an "
    "evidence-bearing unknown.\n"
    "  terra unknown create <slug> --type number|boolean|formula "
    "--quantity <q> --claim \"…?\" --evidence \"…\"\n"
    "  terra unknown link-probe <slug> <probe_id>\n"
    "  terra probe run <probe_id> --to '…' --json\n"
    "  terra unknown link-run <slug> <run_id>\n"
    "  terra unknown graduate <slug> [--as <known_slug>]"
)


def cmd_known_create(args: argparse.Namespace) -> int:
    print(f"error: {_KNOWN_BIRTH_MSG}", file=sys.stderr)
    return 2


def cmd_known_set(args: argparse.Namespace) -> int:
    """Upsert known — agent muscle-memory verb. Never silent no-op."""
    # Merge --note alias into notes
    notes = args.notes
    if getattr(args, "note", None) is not None:
        notes = args.note if notes is None else notes

    value = getattr(args, "value", None)
    try:
        root, created = ensure_project_root()
        mtype = getattr(args, "type", None)
        rec, action = set_known(
            root,
            args.id,
            claim=args.claim,
            notes=notes,
            map_type=mtype,
            quantity=args.quantity,
            unit=args.unit,
            confidence=args.confidence,
            status=args.status,
            run_id=args.from_run,
            expression=getattr(args, "expression", None),
            vars=getattr(args, "vars", None),
            value=value,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    from .paths import known_path as _known_path

    _print_known_summary(action, rec, _known_path(root, args.id))
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
        if rec.get("type") == "formula":
            stat_s = f"holds={st.get('holds')}  rate={st.get('holds_rate')}  n={st.get('n')}"
        elif rec.get("type") == "boolean":
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
    print(
        f"confidence: claimed={rec.get('confidence')}  "
        f"derived={rec.get('confidence_derived')}"
    )
    if rec.get("type") == "formula":
        print(f"expression: {rec.get('expression')}")
        print(f"vars: {rec.get('vars')}")
        print(
            f"stats: holds={st.get('holds')}  holds_rate={st.get('holds_rate')}  "
            f"n={st.get('n')}  k_hold={st.get('k_hold')}  k_fail={st.get('k_fail')}  "
            f"bindings={st.get('bindings')}"
        )
        if st.get("error"):
            print(f"error: {st.get('error')}")
    else:
        print(f"quantity: {rec.get('quantity')}  unit={rec.get('unit') or '—'}")
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
    if rec.get("type") == "formula":
        print(
            f"known {rec['id']}  holds={st.get('holds')}  "
            f"holds_rate={st.get('holds_rate')}  n={st.get('n')}  "
            f"conf={rec.get('confidence')}/{rec.get('confidence_derived')}"
        )
    elif rec.get("type") == "boolean":
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


def cmd_unknown_graduate(args: argparse.Namespace) -> int:
    """Graduate an evidence-bearing unknown into a known (only birth path)."""
    from .knowns import graduate_unknown

    try:
        root = require_project_root()
        rec = graduate_unknown(
            root,
            args.id,
            known_id=getattr(args, "as_id", None),
            notes=args.notes,
            force=args.force,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps(rec, indent=2, default=str))
        return 0
    from .paths import known_path as _known_path

    _print_known_summary("graduated", rec, _known_path(root, rec["id"]))
    print(
        f"  unknown {args.id} resolved (resolved_by=known:{rec['id']})\n"
        f"  next: terra known link-run {rec['id']} <run_id>  "
        f"then  terra known promote {rec['id']} med"
    )
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
    st = rec.get("stats") or {}
    print(
        f"unknown {rec['id']}  run_ids={rec.get('run_ids')}  "
        f"primary_run={rec.get('primary_run_id')}"
    )
    if rec.get("type") in ("number", "boolean"):
        print(
            f"  recomputed n={st.get('n')}  "
            f"derived={rec.get('confidence_derived')}"
        )
    return 0


def cmd_unknown_delete(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        path = delete_unknown(root, args.id)
    except (FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"deleted unknown {args.id}  ({path})")
    return 0


def cmd_known_unlink_run(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = unlink_run_known(root, args.id, args.run_id)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    st = rec.get("stats") or {}
    print(
        f"known {rec['id']}  run_ids={rec.get('run_ids')}  "
        f"conf={rec.get('confidence')}/{rec.get('confidence_derived')}"
    )
    if rec.get("type") == "boolean":
        print(f"  n={st.get('n')}  rate={st.get('rate')}")
    else:
        print(f"  n={st.get('n')}  mean={st.get('mean')}  std={st.get('std')}")
    return 0


def cmd_plan_create(args: argparse.Namespace) -> int:
    from .plans import create_plan, load_plan
    from .evidence_plan import format_plan_summary

    try:
        root, created = ensure_project_root()
        path = create_plan(
            root,
            args.id,
            claim=args.claim,
            mode=args.mode or "all",
            legs=args.legs or [],
            status=args.status,
            notes=args.notes or "",
            force=args.force,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if created:
        print(f"initialized {root / '.terra' / 'map'}")
    rec = load_plan(root, args.id)
    print(f"created plan {args.id}  (above types; legs use number|boolean)")
    print(f"  status={rec.get('status')}  conf={rec.get('confidence')}")
    for line in format_plan_summary(rec):
        print(f"  {line}")
    print(f"  {path}")
    print("  next: terra plan link-run <id> <run> --leg <leg_id>")
    return 0


def cmd_plan_list(args: argparse.Namespace) -> int:
    from .plans import list_plans

    try:
        root = require_project_root()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rows = list_plans(root)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0
    if not rows:
        print("(no plans — terra plan create …)")
        return 0
    for r in rows:
        flag = "ok" if r["ok"] else "BAD"
        rec = r.get("record") or {}
        pl = rec.get("plan") or {}
        print(
            f"[{flag}] {r['id']}  mode={pl.get('mode')}  "
            f"{pl.get('satisfied_count', 0)}/{pl.get('leg_count', 0)}  "
            f"conf={rec.get('confidence')}/{rec.get('confidence_derived')}  "
            f"{(rec.get('claim') or '')[:50]}"
        )
    return 0


def cmd_plan_show(args: argparse.Namespace) -> int:
    from .plans import describe_plan
    from .evidence_plan import format_plan_summary

    try:
        root = require_project_root()
        desc = describe_plan(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    rec = desc["record"]
    if args.json:
        print(json.dumps(rec, indent=2, sort_keys=True, default=str))
        return 0
    print(f"plan {rec.get('id')}  status={rec.get('status')}")
    print(f"claim: {rec.get('claim')}")
    print(
        f"confidence: claimed={rec.get('confidence')}  "
        f"derived={rec.get('confidence_derived')}"
    )
    for line in format_plan_summary(rec):
        print(line)
    return 0


def cmd_plan_link_run(args: argparse.Namespace) -> int:
    from .plans import link_run_plan
    from .evidence_plan import format_plan_summary

    try:
        root = require_project_root()
        rec = link_run_plan(
            root,
            args.id,
            args.run_id,
            leg_id=args.leg,
            primary=bool(args.primary),
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"plan {rec['id']}  linked run → leg {args.leg}")
    for line in format_plan_summary(rec):
        print(f"  {line}")
    return 0


def cmd_plan_unlink_run(args: argparse.Namespace) -> int:
    from .plans import unlink_run_plan
    from .evidence_plan import format_plan_summary

    try:
        root = require_project_root()
        rec = unlink_run_plan(
            root, args.id, args.run_id, leg_id=getattr(args, "leg", None)
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"plan {rec['id']}  unlinked {args.run_id}")
    for line in format_plan_summary(rec):
        print(f"  {line}")
    return 0


def cmd_plan_promote(args: argparse.Namespace) -> int:
    from .plans import promote_plan

    try:
        root = require_project_root()
        rec = promote_plan(
            root, args.id, args.confidence, status=args.status
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"plan {rec['id']}  confidence={rec.get('confidence')}  "
        f"status={rec.get('status')}  derived={rec.get('confidence_derived')}"
    )
    return 0


def cmd_plan_delete(args: argparse.Namespace) -> int:
    from .plans import delete_plan

    try:
        root = require_project_root()
        path = delete_plan(root, args.id)
    except (FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"deleted plan {args.id}  ({path})")
    return 0


def cmd_known_delete(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        path = delete_known(root, args.id)
    except (FileNotFoundError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"deleted known {args.id}  ({path})")
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
        void = " VOID" if rec.get("voided") else ""
        print(
            f"[{flag}] {r['id']}{void}  probe={rec.get('probe_id')}  "
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


def cmd_run_void(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        result = void_run(
            root,
            args.id,
            reason=args.reason or "",
            cascade=not bool(args.no_cascade),
        )
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    rec = result["run"]
    print(f"voided run {rec.get('id')}  reason={rec.get('void_reason')!r}")
    u = result.get("unlinked") or {}
    if result.get("cascade"):
        print(
            f"  unlinked knowns={u.get('knowns') or []}  "
            f"unknowns={u.get('unknowns') or []}  "
            f"plans={u.get('plans') or []}"
        )
    else:
        print(
            f"  recomputed (still linked) knowns={u.get('knowns') or []}  "
            f"unknowns={u.get('unknowns') or []}  "
            f"plans={u.get('plans') or []}"
        )
    print("  next agent will not use this sample in stats")
    return 0


def cmd_run_unvoid(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        rec = unvoid_run(root, args.id)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"unvoided run {rec.get('id')}  (re-link if it should count again)")
    return 0


def cmd_run_delete(args: argparse.Namespace) -> int:
    try:
        root = require_project_root()
        result = delete_run(
            root, args.id, cascade=not bool(args.no_cascade)
        )
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    print(f"deleted run {result.get('deleted')}  ({result.get('path')})")
    u = result.get("unlinked") or {}
    print(
        f"  unlinked knowns={u.get('knowns') or []}  "
        f"unknowns={u.get('unknowns') or []}"
    )
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
            "Terra — above Cartograph: brief (SSOT) + route (tasks) + map (survey). "
            "Typed knowns/unknowns; probes; experiment sessions."
        ),
    )
    p.add_argument("--version", action="version", version=f"terra {__version__}")
    p.add_argument(
        "--map",
        default=None,
        dest="map_id",
        help=(
            "Map scope for this command: 'global' (default) or session id. "
            "Overrides .terra/active_map and TERRA_MAP. "
            "Probes/lib always global; beliefs/runs use this map."
        ),
    )
    sub = p.add_subparsers(dest="group", required=True)

    p_map = sub.add_parser(
        "map",
        help="Map scopes: global durable map vs experiment sessions",
    )
    map_sub = p_map.add_subparsers(dest="map_cmd", required=True)

    p_mc = map_sub.add_parser(
        "create",
        help="Create experiment-scoped map (isolated knowns/unknowns/runs)",
    )
    p_mc.add_argument("id", help="Session map slug")
    p_mc.add_argument("--purpose", default="", help="What this experiment is for")
    p_mc.add_argument(
        "--use",
        action="store_true",
        help="Set as active map after create",
    )
    p_mc.add_argument("--force", action="store_true")
    p_mc.set_defaults(func=cmd_map_create)

    p_ml = map_sub.add_parser("list", help="List global + session maps")
    p_ml.add_argument("--json", action="store_true")
    p_ml.set_defaults(func=cmd_map_list)

    p_mu = map_sub.add_parser("use", help="Set default active map (writes .terra/active_map)")
    p_mu.add_argument("id", help="'global' or session slug")
    p_mu.set_defaults(func=cmd_map_use)

    p_ms = map_sub.add_parser("show", help="Show active map paths")
    p_ms.add_argument("--json", action="store_true")
    p_ms.set_defaults(func=cmd_map_show)

    p_mst = map_sub.add_parser(
        "status",
        help="Map board (JSON by default — agent-first; use --human for text)",
    )
    p_mst.add_argument(
        "--all",
        action="store_true",
        help="Include every session map + global",
    )
    p_mst.add_argument(
        "--id",
        dest="map_scope",
        default=None,
        help="Board for this map id only (default: active)",
    )
    p_mst.add_argument(
        "--human",
        action="store_true",
        help="Pretty-print for humans (secondary view)",
    )
    p_mst.add_argument(
        "--json",
        action="store_true",
        help="Alias for default agent JSON (always on unless --human/--html)",
    )
    p_mst.add_argument(
        "--html",
        action="store_true",
        help="Write HTML board (human view); JSON path still emitted unless --human",
    )
    p_mst.add_argument(
        "-o",
        "--output",
        default=None,
        help="HTML output path (with --html)",
    )
    p_mst.add_argument(
        "--open",
        action="store_true",
        help="Open HTML in browser (implies --html)",
    )
    p_mst.set_defaults(func=cmd_map_status)

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

    p_rvoid = runs_sub.add_parser(
        "void",
        help="Mark run bad (excluded from stats); cascade-unlinks by default",
    )
    p_rvoid.add_argument("id", help="Run id")
    p_rvoid.add_argument(
        "--reason",
        default="",
        help="Why this run must not feed the map",
    )
    p_rvoid.add_argument(
        "--no-cascade",
        action="store_true",
        help="Keep run_ids on knowns/unknowns (still skipped in stats)",
    )
    p_rvoid.add_argument("--json", action="store_true")
    p_rvoid.set_defaults(func=cmd_run_void)

    p_runvoid = runs_sub.add_parser(
        "unvoid",
        help="Clear voided flag (does not re-link; link-run again if needed)",
    )
    p_runvoid.add_argument("id", help="Run id")
    p_runvoid.set_defaults(func=cmd_run_unvoid)

    p_rdel = runs_sub.add_parser(
        "delete",
        help="Hard-delete run dir (prefer void). Cascade-unlinks by default",
    )
    p_rdel.add_argument("id", help="Run id")
    p_rdel.add_argument(
        "--no-cascade",
        action="store_true",
        help="Do not unlink from knowns/unknowns first",
    )
    p_rdel.add_argument("--json", action="store_true")
    p_rdel.set_defaults(func=cmd_run_delete)

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
        choices=["number", "boolean", "formula"],
        dest="type",
        help="number | boolean | formula (observation as checkable expr+vars)",
    )
    p_uc.add_argument(
        "--quantity",
        default=None,
        help="For number/boolean: stable measure name (e.g. hostile_count)",
    )
    p_uc.add_argument(
        "--expression",
        default=None,
        help="For formula: e.g. 'mean(h) <= 10 and n(h) >= 3'",
    )
    p_uc.add_argument(
        "--var",
        action="append",
        dest="vars",
        default=None,
        metavar="NAME=QTY[:kind]",
        help="For formula: bind var (repeatable), e.g. --var h=hostile_count",
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

    p_ugr = unk_sub.add_parser(
        "graduate",
        help="Graduate typed unknown with linked runs into a known "
        "(the only way knowns are born)",
    )
    p_ugr.add_argument("id", help="Unknown id")
    p_ugr.add_argument(
        "--as",
        dest="as_id",
        default=None,
        help="Known slug (default: same as unknown id)",
    )
    p_ugr.add_argument("--notes", default=None)
    p_ugr.add_argument(
        "--force", action="store_true", help="Overwrite existing known"
    )
    p_ugr.add_argument("--json", action="store_true")
    p_ugr.set_defaults(func=cmd_unknown_graduate)

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

    p_uur = unk_sub.add_parser(
        "unlink-run",
        help="Remove a run id from an unknown; recompute typed stats",
    )
    p_uur.add_argument("id", help="Unknown id")
    p_uur.add_argument("run_id", help="Run id to detach")
    p_uur.set_defaults(func=cmd_unknown_unlink_run)

    p_udel = unk_sub.add_parser(
        "delete", help="Delete unknown record from active map"
    )
    p_udel.add_argument("id", help="Unknown id")
    p_udel.set_defaults(func=cmd_unknown_delete)

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

    # Retired birth path — kept so agents get guidance, not argparse noise.
    # Accepts (and ignores) legacy flags; always errors → unknown graduate.
    p_kc = kn_sub.add_parser(
        "create",
        help="Retired — knowns are born via `terra unknown graduate`",
    )
    p_kc.add_argument("id", nargs="?", default=None)
    p_kc.add_argument("legacy_args", nargs=argparse.REMAINDER)
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

    p_kur = kn_sub.add_parser(
        "unlink-run",
        help="Remove a sample run; recompute stats / demote confidence if needed",
    )
    p_kur.add_argument("id")
    p_kur.add_argument("run_id")
    p_kur.set_defaults(func=cmd_known_unlink_run)

    # --- plans (above types: multi/sequence evidence dossiers) ---
    p_plan = sub.add_parser(
        "plan",
        help="Evidence plans above types (multi all | sequential prove A then B)",
    )
    plan_sub = p_plan.add_subparsers(dest="plan_cmd", required=True)

    p_pc = plan_sub.add_parser("create", help="Create multi or sequence evidence plan")
    p_pc.add_argument("id", help="Slug id")
    p_pc.add_argument("--claim", required=True, help="What the dossier asserts")
    p_pc.add_argument(
        "--mode",
        choices=["all", "sequence"],
        default="all",
        help="all = multi any-order; sequence = prove A then B",
    )
    p_pc.add_argument(
        "--leg",
        action="append",
        dest="legs",
        required=True,
        metavar="SPEC",
        help=(
            "Repeatable leg: id:type:quantity[:n=N][:conf=low|med|high]  "
            "e.g. --leg rcon:boolean:rcon_up --leg hostiles:number:hostile_count:n=3"
        ),
    )
    p_pc.add_argument(
        "--status",
        default="provisional",
        choices=sorted(KNOWN_STATUSES),
    )
    p_pc.add_argument("--notes", default="")
    p_pc.add_argument("--force", action="store_true")
    p_pc.set_defaults(func=cmd_plan_create)

    p_pl = plan_sub.add_parser("list", help="List plans on active map")
    p_pl.add_argument("--json", action="store_true")
    p_pl.set_defaults(func=cmd_plan_list)

    p_ps = plan_sub.add_parser("show", help="Show plan progress + legs")
    p_ps.add_argument("id")
    p_ps.add_argument("--json", action="store_true")
    p_ps.set_defaults(func=cmd_plan_show)

    p_plr = plan_sub.add_parser(
        "link-run", help="Attach a run to one leg (sequence enforces order)"
    )
    p_plr.add_argument("id")
    p_plr.add_argument("run_id")
    p_plr.add_argument("--leg", required=True, help="Leg id to fill")
    p_plr.add_argument("--primary", action="store_true")
    p_plr.set_defaults(func=cmd_plan_link_run)

    p_pur = plan_sub.add_parser("unlink-run", help="Detach a run from plan leg(s)")
    p_pur.add_argument("id")
    p_pur.add_argument("run_id")
    p_pur.add_argument("--leg", default=None, help="Only this leg")
    p_pur.set_defaults(func=cmd_plan_unlink_run)

    p_pp = plan_sub.add_parser(
        "promote",
        help="Raise confidence only when all legs satisfied",
    )
    p_pp.add_argument("id")
    p_pp.add_argument("confidence", choices=sorted(CONFIDENCE_SET))
    p_pp.add_argument(
        "--status",
        default=None,
        choices=sorted(KNOWN_STATUSES),
    )
    p_pp.set_defaults(func=cmd_plan_promote)

    p_pd = plan_sub.add_parser("delete", help="Delete plan from active map")
    p_pd.add_argument("id")
    p_pd.set_defaults(func=cmd_plan_delete)

    p_kdel = kn_sub.add_parser(
        "delete", help="Delete known record from active map"
    )
    p_kdel.add_argument("id")
    p_kdel.set_defaults(func=cmd_known_delete)

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

    # --- brief (SSOT design request) ---
    p_br = sub.add_parser(
        "brief",
        help="SSOT design request (needs, deliverables, change control)",
    )
    br_sub = p_br.add_subparsers(dest="brief_cmd", required=True)

    p_bi = br_sub.add_parser("init", help="Create project brief")
    p_bi.add_argument("--title", required=True)
    p_bi.add_argument("--mission", default="")
    p_bi.add_argument("--force", action="store_true")
    p_bi.set_defaults(func=cmd_brief_init)

    p_bs = br_sub.add_parser("show", help="Show brief (JSON default)")
    p_bs.add_argument("--human", action="store_true")
    p_bs.add_argument("--full", action="store_true", help="Include proposals")
    p_bs.set_defaults(func=cmd_brief_show)

    p_bset = br_sub.add_parser("set", help="Update brief fields (bumps version)")
    p_bset.add_argument("--title", default=None)
    p_bset.add_argument("--mission", default=None)
    p_bset.add_argument(
        "--status",
        default=None,
        choices=["draft", "active", "frozen", "archived"],
    )
    p_bset.add_argument("--need", action="append", dest="needs", default=None)
    p_bset.add_argument(
        "--non-goal", action="append", dest="non_goals", default=None
    )
    p_bset.add_argument(
        "--deliverable", action="append", dest="deliverables", default=None
    )
    p_bset.add_argument(
        "--enabler",
        action="append",
        dest="enablers",
        default=None,
        metavar="ID:TITLE[:PATH]",
        help="Internal tooling/harness (not a customer deliverable)",
    )
    p_bset.add_argument(
        "--replace-lists",
        action="store_true",
        help="Replace needs/non_goals/deliverables/enablers instead of append",
    )
    p_bset.add_argument(
        "--budget-points",
        type=int,
        default=None,
        dest="budget_points",
        help="Total project effort budget (task points: low=3 medium=8 high=21)",
    )
    p_bset.add_argument(
        "--clear-budget-points",
        action="store_true",
        dest="clear_budget_points",
        help="Clear budget_points (set to null)",
    )
    p_bset.add_argument(
        "--budget-notes",
        default=None,
        dest="budget_notes",
        help="Human note for budget (horizon, team size, …)",
    )
    p_bset.set_defaults(func=cmd_brief_set)

    p_bph = br_sub.add_parser("phase", help="Add a phase name to the brief")
    p_bph.add_argument("id", help="Phase slug")
    p_bph.add_argument("--title", default="")
    p_bph.set_defaults(func=cmd_brief_phase)

    p_bp = br_sub.add_parser("propose", help="Queue a change (does not apply)")
    p_bp.add_argument("--summary", required=True)
    p_bp.add_argument("--need", default=None)
    p_bp.add_argument("--non-goal", default=None, dest="non_goal")
    p_bp.add_argument("--deliverable", default=None)
    p_bp.add_argument(
        "--enabler",
        default=None,
        metavar="ID:TITLE[:PATH]",
        help="Propose adding an enabler (tooling/harness)",
    )
    p_bp.add_argument("--mission", default=None)
    p_bp.set_defaults(func=cmd_brief_propose)

    p_ba = br_sub.add_parser("accept", help="Accept a proposal (bumps version)")
    p_ba.add_argument("id", help="Proposal id")
    p_ba.set_defaults(func=cmd_brief_accept)

    p_brj = br_sub.add_parser("reject", help="Reject a proposal")
    p_brj.add_argument("id", help="Proposal id")
    p_brj.set_defaults(func=cmd_brief_reject)

    p_ben = br_sub.add_parser(
        "enabler",
        help="Update enabler status (needed|building|ready|graduated|abandoned)",
    )
    p_ben.add_argument("id", help="Enabler id")
    p_ben.add_argument(
        "status",
        choices=["needed", "building", "ready", "graduated", "abandoned"],
    )
    p_ben.add_argument("--path", default=None, help="Path to tooling in repo")
    p_ben.add_argument(
        "--graduates-to",
        default=None,
        dest="graduates_to",
        help="Cartograph widget/blueprint id if extracted",
    )
    p_ben.add_argument("--notes", default=None)
    p_ben.set_defaults(func=cmd_brief_enabler)

    # --- route (task DAG) ---
    p_rt = sub.add_parser(
        "route",
        help="Task DAG for the main agent (walks the brief)",
    )
    rt_sub = p_rt.add_subparsers(dest="route_cmd", required=True)

    p_ri = rt_sub.add_parser("init", help="Create empty route")
    p_ri.add_argument("--force", action="store_true")
    p_ri.set_defaults(func=cmd_route_init)

    p_rst = rt_sub.add_parser("status", help="Counts + next + blocked (JSON)")
    p_rst.add_argument("--human", action="store_true")
    p_rst.set_defaults(func=cmd_route_status)

    p_rbgt = rt_sub.add_parser(
        "budget",
        help="Budget rollup only (total/planned/done/unallocated + task weights)",
    )
    p_rbgt.add_argument("--human", action="store_true")
    p_rbgt.set_defaults(func=cmd_route_budget)

    p_rse = rt_sub.add_parser(
        "set-effort",
        help="Re-bucket a task (low|medium|high). May exceed budget_points.",
    )
    p_rse.add_argument("id", help="Task slug")
    p_rse.add_argument(
        "--bucket",
        default=None,
        choices=["low", "medium", "high"],
        help="low=3 implement, medium=8 validate, high=21 explore",
    )
    p_rse.add_argument(
        "--points",
        type=int,
        default=None,
        help="3, 8, or 21 (sets bucket if --bucket omitted)",
    )
    p_rse.add_argument("--human", action="store_true")
    p_rse.set_defaults(func=cmd_route_set_effort)

    p_rsa = rt_sub.add_parser(
        "sector-add",
        help="Reserve a point provision (sector) to explode into tasks later",
    )
    p_rsa.add_argument("id", help="Sector slug")
    p_rsa.add_argument("--title", required=True)
    p_rsa.add_argument(
        "--points",
        type=int,
        required=True,
        help="Reserved points from project budget (any int >= 0)",
    )
    p_rsa.add_argument("--notes", default="")
    p_rsa.add_argument("--human", action="store_true")
    p_rsa.set_defaults(func=cmd_route_sector_add)

    p_rss = rt_sub.add_parser(
        "sector-set",
        help="Update sector reserve/title (plan must be unlocked to change points)",
    )
    p_rss.add_argument("id", help="Sector slug")
    p_rss.add_argument("--points", type=int, default=None, help="New reserved_points")
    p_rss.add_argument("--title", default=None)
    p_rss.add_argument("--notes", default=None)
    p_rss.add_argument("--human", action="store_true")
    p_rss.set_defaults(func=cmd_route_sector_set)

    p_rlp = rt_sub.add_parser(
        "lock-plan",
        help="Lock plan_* baseline (set-effort only changes working effort)",
    )
    p_rlp.add_argument("--human", action="store_true")
    p_rlp.set_defaults(func=cmd_route_lock_plan)

    p_rul = rt_sub.add_parser(
        "unlock-plan",
        help="Unlock plan baseline (requires --confirm after warning)",
    )
    p_rul.add_argument(
        "--confirm",
        action="store_true",
        help="Required to actually unlock (without it, prints warning and fails)",
    )
    p_rul.add_argument("--human", action="store_true")
    p_rul.set_defaults(func=cmd_route_unlock_plan)

    p_rn = rt_sub.add_parser("next", help="Next pickable / in-progress tasks")
    p_rn.add_argument("--limit", type=int, default=5)
    p_rn.add_argument("--human", action="store_true")
    p_rn.set_defaults(func=cmd_route_next)

    p_ra = rt_sub.add_parser("add", help="Add a task")
    p_ra.add_argument("id", help="Task slug")
    p_ra.add_argument("--title", required=True)
    p_ra.add_argument("--phase", default="")
    p_ra.add_argument(
        "--dep",
        action="append",
        dest="deps",
        default=None,
        help="Dependency task id (repeatable)",
    )
    p_ra.add_argument(
        "--skill",
        default="any",
        choices=sorted(
            {
                "terra-map",
                "terra-probe",
                "cg-plan",
                "cg-create",
                "cg-blueprint",
                "deliverable",
                "tooling",
                "any",
            }
        ),
        help="tooling=build enablers/harnesses; deliverable=customer pack",
    )
    p_ra.add_argument(
        "--role",
        default="any",
        choices=sorted(
            {"survey", "enabler", "deliverable", "orchestration", "any"}
        ),
        help="enabler = internal means of production; deliverable = brief output",
    )
    p_ra.add_argument(
        "--enabler",
        dest="enabler_id",
        default=None,
        help="Link task to brief.enablers[].id",
    )
    p_ra.add_argument(
        "--bucket",
        default=None,
        choices=["low", "medium", "high"],
        help="Effort bucket: low=3 (implement), medium=8 (validate), high=21 (explore)",
    )
    p_ra.add_argument(
        "--points",
        type=int,
        default=None,
        help="Task points (must be 3, 8, or 21; sets bucket if --bucket omitted)",
    )
    p_ra.add_argument(
        "--sector",
        dest="sector_id",
        default=None,
        help="Draw from a sector provision (required to add tasks when plan is locked)",
    )
    p_ra.add_argument(
        "--accept",
        action="append",
        dest="acceptance",
        default=None,
        help="Acceptance criterion (repeatable)",
    )
    p_ra.add_argument("--map", dest="task_map", default=None)
    p_ra.set_defaults(func=cmd_route_add)

    p_rstt = rt_sub.add_parser("start", help="Mark task in_progress")
    p_rstt.add_argument("id")
    p_rstt.set_defaults(func=cmd_route_start)

    p_rc = rt_sub.add_parser("complete", help="Mark task done")
    p_rc.add_argument("id")
    p_rc.add_argument("--evidence", default=None)
    p_rc.set_defaults(func=cmd_route_complete)

    p_rb = rt_sub.add_parser("block", help="Block a task")
    p_rb.add_argument("id")
    p_rb.add_argument("--reason", required=True)
    p_rb.set_defaults(func=cmd_route_block)

    p_rub = rt_sub.add_parser("unblock", help="Unblock a task")
    p_rub.add_argument("id")
    p_rub.set_defaults(func=cmd_route_unblock)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    # Apply --map before any path resolution in the command
    if getattr(args, "map_id", None):
        try:
            set_active_map_id(args.map_id)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
