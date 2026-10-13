---
name: theme
source: wds
type: script
description: The look of everything WDS renders (trigger map, persona pages, folder presentations). A neutral default, overridden by the client's brand tokens. The module is theme/theme.py; the default is theme/neutral.css.
used_by: [trigger-map, folder-presentation]
---

# Tool: theme

Rendered artefacts take their look from the client's brand, so a trigger map or a presentation looks like the client's own material. Until the brand has tokens, they use a neutral, tidy WDS default.

## Where the brand's tokens are

`tokens.css`, the nearest one above the folder being rendered, up to the repo root. At each level the scripts look for, in order:

1. `brand/design-system/tokens.css`
2. `brand/visual-identity/tokens.css`
3. `visual-identity/tokens.css` (repos set up before `brand/`)

`tokens.css` is the machine form of the brand's design tokens; the document that explains them (`design-tokens.md`) sits beside it. A token changes in both together, and only at the brand's level, never in a project.

## The roles

`tokens.css` maps the brand's own tokens to the roles the scripts use. A role it leaves out keeps the neutral value.

| Role | Used for |
|---|---|
| `--wds-paper`, `--wds-surface` | Background |
| `--wds-ink`, `--wds-ink-2`, `--wds-ink-3` | Text, supporting text, labels |
| `--wds-line` | Hairlines, borders, connectors |
| `--wds-accent`, `--wds-accent-ink` | Accent graphics; accent as text and links |
| `--wds-positive`, `--wds-negative` | Forces toward and away from |
| `--wds-font-display`, `--wds-font-body`, `--wds-font-mono` | Headings, body, labels and figures |
| `--wds-radius` | Corner radius |

Dark blocks (such as the product on the trigger map) use ink with paper text, so contrast holds whatever the accent is.

## A brand's tokens.css

```css
/* <Client>: the design tokens as CSS. What they mean and why: design-tokens.md. */
@import url("https://fonts.googleapis.com/css2?family=…&display=swap");

:root {
  --paper: #FEFEFD;
  --ink: #16181B;
  --gilt: #B8955A;
  --serif: "Baskervville", Georgia, serif;

  /* WDS roles */
  --wds-paper: var(--paper);
  --wds-ink: var(--ink);
  --wds-accent: var(--gilt);
  --wds-font-display: var(--serif);
}
```

Write it from the brand's `design-tokens.md` when the first artefact is rendered for the client, and keep the two in step.

## Use in a script

```python
sys.path.insert(0, "<agents/wds/tools>/theme")
from theme import Theme
th = Theme(folder)          # or Theme(folder, "<path to a css>")
th.get("--wds-ink")         # a resolved value, for SVG
th.style(page_css)          # a <style> block for an HTML page, fonts first
th.describe()               # which theme was used
```
