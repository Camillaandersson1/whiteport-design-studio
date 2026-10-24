---
name: theme
source: wds
type: script
description: The look of everything WDS renders (trigger map, persona pages, folder presentations) and of markdown in VS Code. A neutral default, overridden by the client's brand tokens. The module is theme/theme.py; the default is theme/neutral.css.
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
| `--wds-heading-weight` | Weight of headings (600 by default; 300 for a light brand like Whiteport) |

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

## Markdown in VS Code in the brand's look

**Warning (2026-10-24):** the Markdown Editor extension (zaaack) rewrites the whole file in its own format on every save: tables are padded, blank lines added, and **frontmatter is removed**. It damaged two WDS step files and two client files. Do not use it to edit files in a repo; VS Code's preview is the safe default (`"*.md": "vscode.markdown.preview.editor"`). The styling below applies only while it is in use.

With the Markdown Editor extension (zaaack) as the editor for `.md`, markdown is edited like a document. This writes the brand's look into the repo's `.vscode/settings.json` (`markdown-editor.customCss`), keeping every other setting:

```bash
python agents/wds/tools/theme/theme.py vscode <repo>                     # the brand found in the repo, or neutral
python agents/wds/tools/theme/theme.py vscode <repo> --theme <tokens.css>  # a brand that lives in another repo
```

Only fonts loaded from the web reach the editor; a brand whose fonts are local files needs an `@import` from a font service in `tokens.css` for the editor. Run it again when the tokens change. Whether `.vscode/` is committed is the repo's choice; many keep it out of git.

## Use in a script

```python
sys.path.insert(0, "<agents/wds/tools>/theme")
from theme import Theme
th = Theme(folder)          # or Theme(folder, "<path to a css>")
th.get("--wds-ink")         # a resolved value, for SVG
th.style(page_css)          # a <style> block for an HTML page, fonts first
th.describe()               # which theme was used
```
