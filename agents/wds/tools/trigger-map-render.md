---
name: trigger-map-render
source: wds
type: script
description: Renders the whole Trigger Map from one data file, trigger-map.yaml, into the markdown documents, the map as SVG and HTML, and one persona page per persona. Same template every time; the look comes from the visual identity, with a neutral WDS theme as default. The script is trigger-map-render/render.py.
used_by: [trigger-map]
---

# Tool: trigger-map-render

The Trigger Map has a fixed form, so it is rendered rather than written. Saga keeps the content in one data file; the script turns it into every artefact, identical in structure every time.

```
B-Trigger-Map/trigger-map.yaml  →  render.py  →  01-business-goals.md
                                                 NN-persona-<name>.md + .html
                                                 00-trigger-map.md + .svg + .html
                                                 feature-impact.md (when there are features)
```

The generated files start with a comment saying so. Change the yaml and render again; an edit in a generated file is lost at the next render.

## Configuration

| What | Where |
|---|---|
| Python package | `python -m pip install pyyaml` (once per computer) |
| Default look | `trigger-map-render/themes/neutral.css`: quiet, one ink and one accent |
| The client's look | `visual-identity/tokens.css`, the nearest one above the folder (the project, then each level up to the repo root). It overrides the `--wds-*` roles, and may `@import` the client's fonts. |

### The theme roles

A client's `tokens.css` maps its own tokens to these roles. A role it leaves out keeps the neutral value.

| Role | Used for |
|---|---|
| `--wds-paper`, `--wds-surface` | Background |
| `--wds-ink`, `--wds-ink-2`, `--wds-ink-3` | Text, supporting text, labels. The product block on the map is ink with paper text, so contrast holds in every theme. |
| `--wds-line` | Hairlines, borders, connectors |
| `--wds-accent`, `--wds-accent-ink` | Accent graphics, accent as text and links |
| `--wds-positive`, `--wds-negative` | Forces toward and away from |
| `--wds-font-display`, `--wds-font-body`, `--wds-font-mono` | Headings, body, labels and scores |
| `--wds-radius` | Corner radius |

## Actions

### Render

```bash
python agents/wds/tools/trigger-map-render/render.py projects/<project>/B-Trigger-Map
```

It prints which theme it used and every file it wrote, and flags persona files that no longer belong to a persona in the yaml. `--theme <path to css>` uses a specific theme instead of the visual identity.

### Bring in an existing Trigger Map

For a map written by hand in the WDS templates (goals, persona files, the map with its Mermaid diagram):

```bash
python agents/wds/tools/trigger-map-render/render.py import projects/<project>/B-Trigger-Map
```

It writes `trigger-map.yaml` from the documents. Read it through before rendering, since the render replaces the documents with the template's version.

## The data file

```yaml
project: Seed Round
status: draft                  # draft | confirmed
status_note: "**draft from the material, workshops pending.** …"   # optional, replaces the default status line
date: '2026-10-13'
vision: The seed round brings in investors who …
product: {name: Welqora seed round, line: "€4M for 10 %, funding the proof year"}
goals:
- id: G1
  name: Close the round with the right investors
  why: The round is closed with investors who bring more than money.
  objectives:
  - {objective: A lead investor commits first, target: "One lead, `[needed: date]`", short: a lead commits first}
personas:                      # in priority order; the files are numbered 02, 03 … in this order
- name: Anders the Angel       # alliterative
  priority: primary            # primary | secondary | tertiary | gatekeeper
  priority_note: …             # optional
  one_line: a high-net-worth investor in Johan Lundberg's network
  goals: [G1, G2]
  status_note: …               # optional
  who: …
  psychology: …
  internal_state: …
  usage: {discovery: …, arrival: …, behaviour: …, decision: …}
  scenes: ["…"]                # optional: short scenes for the persona page
  forces:
  - {dir: "+", name: In before the others, what: …, why: …, when: …, f: 4, i: 4, fit: 5}
  - {dir: "-", name: Figures he can't check, what: …, why: …, when: …, f: 5, i: 5, fit: 5}
  goal_links: {G1: most of the €4M is likely to come from tickets like his.}
  sources: our conversations, 01-product-brief.md
key_read: The strongest forces are negative …
points: ["**Petra comes first.** …"]
features:                      # optional, workshop 5
- name: Audited data room
  serves: {anders.n1: 3, lars.n1: 2}   # force ids: <first name>.<p|n><number in its direction>
  implication: …
map: {forces_per_direction: 1} # forces per persona on the poster
scores_note: Scores are Saga's hypotheses.   # optional, shown with the scoring format
```

Text fields take inline markdown: `**bold**`, `*italic*`, `` `code` `` and links. A force's total is Frequency + Intensity + Fit, computed by the script.

## Errors

| What happens | Do |
|---|---|
| `Ingen trigger-map.yaml` | Write the data file, or bring in an existing map with `import`. |
| `ModuleNotFoundError: yaml` | `python -m pip install pyyaml` |
| The poster uses the neutral theme in a client repo | The repo has no `visual-identity/tokens.css` yet. Write it from the visual identity's tokens, mapping them to the roles above. |
