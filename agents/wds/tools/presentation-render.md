---
name: presentation-render
source: wds
type: script
description: Turns a folder's presentation.md into presentation.html, a deck you browse with the arrow keys, in the client's brand or the neutral WDS look. The script is presentation-render/present.py.
used_by: [folder-presentation]
---

# Tool: presentation-render

```
<folder>/presentation.md  →  present.py  →  <folder>/presentation.html
```

## Configuration

| What | Where |
|---|---|
| Python packages | `python -m pip install markdown pyyaml` (once per computer) |
| The look | The shared [theme](theme.md): the brand's `tokens.css`, or the neutral default |

## Actions

### Render one folder

```bash
python agents/wds/tools/presentation-render/present.py projects/<project>/A-Product-Brief
```

### Render every presentation in a project

```bash
python agents/wds/tools/presentation-render/present.py --all projects/<project>
```

`--theme <path to css>` uses a specific theme instead of the brand's.

## presentation.md

```markdown
---
title: Product Brief
project: Welqora seed round
updated: 2026-10-13
status: "**Draft.** The brief is written from the material; the workshops confirm it."
lang: en
---

# The seed round in one sentence

Welqora raises €4M for 10 % to fund the year that proves the platform.

---

## Who it is for

- **Anders the Angel**, …

---

## Where we are

| Done | Next |
|---|---|
| … | … |
```

- The first slide is the cover: its heading is large, and `status` is shown under it.
- A line with only `---` starts a new slide. Use `***` for a rule inside a slide.
- Markdown: headings, paragraphs, lists, tables, quotes, links and images. Images and links are relative to the folder, so `![](00-trigger-map.svg)` works.
- `lang` sets the page language (default `en`).

The deck works on a phone (scroll) and prints one slide per page.
