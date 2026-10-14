---
name: excalidraw-export
source: wds
type: script
description: Renders .excalidraw wireframes to PNG (or JPG) without opening an editor, one file or a whole folder, and can point the spec's image link at the result. The script is excalidraw-export/excalidraw-to-image.py.
used_by: [ux-design]
---

# Tool: excalidraw-export

The UX design loop needs a PNG of every wireframe: for the approval gate, and because GitHub renders the PNG inline in the spec while the `.excalidraw` file stays the editable source. The agent exports it itself; the user never has to export by hand.

## Configuration

| What | Where |
|---|---|
| Python package | `python -m pip install pillow` (once per computer) |
| Fonts | Found automatically on Windows, macOS and Linux. Excalidraw's hand-drawn font is rendered as a clean sans. |

## Actions

### Export one wireframe

```bash
python agents/wds/tools/excalidraw-export/excalidraw-to-image.py <page>-wireframe.excalidraw
```

Writes `<page>-wireframe.png` next to the source. A second argument sets another output path.

### Export and update the spec

```bash
python agents/wds/tools/excalidraw-export/excalidraw-to-image.py <page>-wireframe.excalidraw --update-spec <page>.md
```

Points the matching `![…](…)` image link in the spec at the new PNG.

### Export a whole folder

```bash
python agents/wds/tools/excalidraw-export/excalidraw-to-image.py --batch <folder>
```

Every `.excalidraw` under the folder, recursively.

| Option | Default | |
|---|---|---|
| `--format png\|jpg` | `png` | JPG for colourful, photo-heavy drawings |
| `--scale N` | `1.0` | `2` for a sharper image |
| `--padding N` | `40` | Pixels around the content |

## Limits

- Renders rectangles, ellipses, text and lines. Arrows, free drawing and embedded images are skipped. That is enough for WDS wireframes; for anything else, export from the Excalidraw editor.
- Rounded corners and the hand-drawn look are approximated; the PNG is clean and flat.
- Remove development annotations from the drawing before exporting ([docs/tools/excalidraw.md](../../../docs/tools/excalidraw.md), Workflow D).
