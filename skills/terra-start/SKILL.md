---
name: terra-start
description: >
  REQUIRED when initiating a new Terra project or when .terra/brief/route are
  missing: terra init, brief init/set (incl. budget_points), route init, first
  tasks with buckets. Fire on "start a terra project", "init the brief",
  "scaffold terra", empty product folder that needs campaign infrastructure.
  Does NOT own lead loop or lock-plan details (terra-route), beliefs
  (terra-survey), or product bars — after init hand off. Does NOT develop Terra
  itself (terra-dev).
---

# terra-start — initiate a Terra project

Stand up **brief + route + map store**. Then hand off.

`terra` on PATH required.

## Steps

```bash
cd /path/to/project

terra init

terra brief init --title "…" --mission "…"

terra brief set \
  --need "…" \
  --deliverable "…" \
  --non-goal "…" \
  --budget-points 100 \          # total effort (strongly recommended)
  --budget-notes "single phase / …" \
  --enabler "id:Title:path"      # optional

terra brief phase <id> --title "…"   # optional

terra route init

# Optional: reserve provisions for areas you will detail later
# terra route sector-add cad --title "CAD" --points 89

# Skeleton tasks MUST use --bucket when budget_points is set (low=3 medium=8 high=21)
terra route add brief_lock --title "Read brief; lock understanding" \
  --skill any --bucket low --accept "brief understood"

# more skeleton: --bucket …, --sector <id>, --skill …, --dep, --enabler
# Unsectored points ≤ free_pool; per-sector ≤ reserved

terra route budget --human       # plan / sectors / free_pool
terra route lock-plan            # then explode sectors with --sector only
# (details: terra-route — unlock needs --confirm)

# optional: terra map create trades --purpose "…" --use

terra brief show
terra route next
terra map status
```

## Budget at intake (brief)

| | |
| - | - |
| **Who owns total** | **terra-brief** — `budget_points` / `budget_notes` |
| **Who owns task weights** | **terra-route** — `--bucket` → 3/8/21 |
| **low / medium / high** | implement / validate / explore |
| **After skeleton** | `terra route lock-plan` so set-effort only moves **actual** |

## Done when

1. `terra brief show` works (budget set if using effort caps)  
2. `terra route next` shows a pickable task  
3. `terra route budget` shows plan ≤ budget  
4. Prefer **plan locked** before execution  
5. `terra map status` works  

| Next | Skill |
| ---- | ----- |
| Lead loop / set-effort / unlock | **terra-route** |
| Needs / enablers / raise budget | **terra-brief** |
| Unknowns / knowns / void | **terra-survey** |
| Global vs session | **terra-scopes** |
| probe.py | **terra-probe** |
| Index if unsure | **terra-map** |
