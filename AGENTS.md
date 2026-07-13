# Terra — agent notes

Terra is **above Cartograph**: **brief** (SSOT design request) + **route**
(task DAG) + **map** (survey/evidence). Bricks stay Cartograph.

This product improves by **project scars**, not only careful up-front design
(unlike Cartograph widgets). Ship thin slices; encode gotchas when DX burns.

This repo is a bit different from a pure Cartograph product app. We put a lot
of work into **validation as the hard bar** (Cartograph widgets, rules,
checkin). That earned some freedom here: Terra can move product-fast when the
bar is still **tests + validate**, not ceremony for its own sake.

“Vibe coding” that is really *validate-and-ship* is fine. Silent freehand
with no bar is not.

## Default posture (earned freedom)

**Inside Terra product code** (`src/terra/`, map model, CLI, `.terra` layout):

- Prefer **ship a thin slice + pytest green** over a full widget plan for every
  small map feature.
- Hard bar: **`PYTHONPATH=src pytest`** (and blueprint/widget validate when
  touching `cg/`).
- Agent-first outputs: JSON / machine envelopes by default where we have them;
  human views (`--human`, HTML) are secondary. See `docs/agent-io.md`.
- Docs under `docs/` and `skills/terra-map/` when behavior is durable.

You do **not** need a full **cg-plan** for every probe tweak, status line, or
map-scope bugfix. That would thrash the validation culture we built.

## When Cartograph still owns the move

Use **cg-plan → search → install/improve/create/blueprint** when the work is
**not** Terra-specific product glue:

| Situation | Do this |
| --------- | ------- |
| Capability would be useful **outside** Terra (agent CLI, envelopes, parsers, generic status) | **cg-plan** + registry search first |
| Multi-widget **feature** others would install | **blueprint** (see `cg/bp_agent_tool_cli_python`) |
| Durable project convention for agents/checkin | **cg-rules** (Cartograph), not only AGENTS.md prose |
| New atom that smells reusable | Search `cg/` + registry **before** inventing in `src/terra/` |

Under-extraction is still the failure mode for **library** work. Over-planning
Terra-only map product is the other failure mode. Pick by *would another
project re-derive this?*

## Cartograph in this tree

Installed under `cg/` (leaves + blueprints). Today:

- Leaves: agent-response, agent-cli  
- Blueprint: **`bp-agent-tool-cli-python`** — sealed agent CLI + envelope  

Terra’s `terra.agent_io` should **re-export the blueprint**, not invent a
parallel schema. Prefer improving the blueprint over freehand envelopes.

Parent Cartograph monorepo still has its own AGENTS.md; this file **wins for
work under `Terra/`**.

## Validation is the vibe

| Soft | Hard |
| ---- | ---- |
| “Looks good in chat” | pytest green |
| Prose-only CLI for agents | Structured status / agent-response envelope |
| One green probe run | Typed knowns ladder, link-run, void bad evidence |
| Guess domain from training data | Probe + stamped run |

If you are “vibing,” close the loop with **tests or validate** in the same
session. That is the freedom we earned: move fast *and* leave a bar.

## Map product laws (short)

1. **Global vs session maps** — experiments don’t muddy global beliefs.  
2. **Probes/lib global**; unknowns/knowns/plans/runs scoped to active map.  
3. **Plans above types** — multi/sequence evidence is `terra plan`, not a peer of number/boolean.  
4. **Adjust** — void/unlink before the next agent trusts poison.  
5. **Agent status** — `terra map status` is JSON-first (`attention` + `next_actions`).

## Git / scope

- Local git under this folder; **no GitHub push** unless the user asks.  
- Keep Terra product logic here; reusable atoms that outgrow Terra → extract via
  Cartograph (plan + create/checkin), don’t forever expand `src/terra/` with
  generic libraries.

## Skills (user-side)

Two portable skills (foreign-project cwd). Keep them aligned when the product changes:

| Skill | When |
| ----- | ---- |
| **terra-map** | fog, beliefs (unknown/known/formula/plan), scopes, status, void/promote |
| **terra-probe** | building/fixing `probe.py`, validate I/O, suites, measures, link-probe |
| **terra-dev** | **this repo** — CLI DX, pytest, skill sync, gotchas (not foreign survey) |

Handoff: probe stamps a run → **terra-map** link-run / known. Need an instrument → **terra-probe**.  
Maintaining Terra → **terra-dev** (always-check list + known footguns).

Sources: `skills/terra-{map,probe,dev}/` (also under `~/.grok/skills/`).
