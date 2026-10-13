---
name: folder-presentation
description: Keeps a short HTML presentation in each WDS folder of a project that shows the essence of the folder as it stands now. Use when a folder's content changes, at every wrap for the folders the session touched, or when someone wants to understand a folder without reading all of it.
used_by: [idun, saga, freya, mimir]
version: 1.0
tools: [wds/presentation-render, wds/git]
---

# Folder presentation

Every WDS folder in a project (`A-Product-Brief/`, `B-Trigger-Map/`, `C-UX-Scenarios/`, `D-Design-System/`, `E-Development/`) holds a presentation of its own essence: a few slides that let the client, a new colleague or the next agent understand the folder and where it stands without reading every document. The documents stay the source; the presentation is the way in.

It is written as `presentation.md` in the folder and rendered to `presentation.html` with [presentation-render](../../tools/presentation-render.md), in the client's brand or the neutral WDS look.

## What a good one holds

- **The essence, not a summary of each file.** What the folder has concluded, in the words the client would use: the one sentence that carries it, then what follows from it.
- **Where it stands now.** What is agreed, what is still a draft or a hypothesis, what is open and who decides. The `status` in the front matter says it in one line.
- **What it means for the next step.** What Freya, Mimir or the client does with it.
- **Links into the documents** for whoever wants the detail.
- **Short.** Usually five to ten slides, one idea per slide, a heading that says the point. Tables and images where they say it faster than prose; the trigger map's `00-trigger-map.svg` belongs on a slide in `B-Trigger-Map/`.
- **Only what the folder says.** Nothing invented, nothing from another folder presented as this one's. A claim that is not yet verified is marked as such, as in the documents.
- **The documents' language** (`document_output_language` in `AGENTS.md`).

## When

- **At wrap,** for every WDS folder the session changed: update `presentation.md` so it reflects the folder as it stands after the session, render it, and commit it with the rest (wrap step 3).
- When a folder gets its first real content, create the presentation then.
- A folder with nothing in it yet has no presentation.

## Done

`presentation.md` and `presentation.html` reflect the folder's current state, and the `updated` date is today.
