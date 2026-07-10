# Map layer — Data (requirement 3)

Cartograph taught: **validation is the key**, not markdown guidance.
The map layer starts with the easiest hard surface: **collected data**.

Data is a **reading of the world** — not a plan, not an opinion, not chat
scrollback. Unknowns and anchors come later; they will *point at* data.
Without durable, validated captures, the rest of the map is fiction.

## Core rule

A capture is only “real data” if it passes validation. Soft notes (“I ran
something earlier”) are not data. Unstamped folders under `.terra/map/data/`
are not trusted by the loop.

## What a capture is

One directory:

```text
.terra/map/data/<id>/
  meta.json          # provenance + env + links + artifact index
  <artifact files>   # stdout, files copied in, probe output, …
```

`meta.json` is the stamp surface. Artifacts are the evidence.

## Why this is first

| Requirement | Needs data? |
| ----------- | ----------- |
| Unknowns | “What would resolve this?” → expected data shape |
| Anchors | High confidence only with linked data; refutation needs data |
| **Data** | Self-contained: capture + validate without the other two |

So we build **capture + validate** before the belief graph.

## Hard bar (validate)

A capture **passes** only if all of:

1. `meta.json` exists and parses as JSON object  
2. `schema_version` is supported (currently `1`)  
3. `id` is non-empty and equals the directory name  
4. `captured_at` is a valid ISO-8601 timestamp  
5. `source.type` is one of `command | file | probe | manual`  
6. Source payload matches type (e.g. `command` requires `source.command`)  
7. `env.fingerprint` is an object with **at least one** entry  
8. `artifacts` is a non-empty list  
9. Every artifact `path` exists under the capture dir, is a file, and is non-empty  
   (unless `allow_empty: true` on that artifact)  
10. If `sha256` is set, it matches the file contents  
11. `links.supports`, `links.refutes`, `links.unknowns`, `links.anchors` are lists  
    (may be empty until unknowns/anchors exist)

Failures are **blocks** — the capture is not usable as map evidence.

## Capture contract

Recording data must always:

- Write artifacts **first**, then `meta.json` that indexes them  
- Record **when** (`captured_at`)  
- Record **where/what world** (`env.fingerprint`)  
- Record **how** (`source`)  
- Compute content hashes for listed artifacts  

Optional at capture time: title, notes, link ids (for later map objects).

## Non-goals (v0)

- Unknown / anchor CRUD  
- Automatic interpretation of outputs  
- Cloud sync  
- Replacing Cartograph widgets (durable probes may *become* widgets later)

## CLI (v0)

```text
terra data capture --title "…" -- <command> [args…]
terra data capture --file PATH --title "…"
terra data list
terra data show <id>
terra data validate [<id>]
```

Project root: directory containing `.terra/`, or cwd if creating via capture
with `--init`.

## Success metric

You can point at a capture id and say: **this is evidence**, not a story —
and a cold agent can re-read `meta.json` + artifacts without the original chat.
